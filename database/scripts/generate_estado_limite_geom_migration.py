"""Gera migration com limites oficiais das UFs (IBGE Malhas v3)."""

from __future__ import annotations

import gzip
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_PATH = (
    ROOT
    / "app_saas"
    / "database"
    / "migrations"
    / "043 - limites_geograficos_estados.sql"
)

# Codigos IBGE das UFs presentes em global.estado (migration 015).
STATE_CODES = [
    11, 12, 13, 14, 15, 16, 17,
    21, 22, 23, 24, 25, 26, 27, 28, 29,
    31, 32, 33, 35,
    41, 42, 43,
    50, 51, 52, 53,
]

IBGE_MESH_URL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/estados/{codigo_ibge}"
    "?formato=application/vnd.geo+json&qualidade=minima"
)


def fetch_state_geometry(codigo_ibge: int) -> dict:
    request = urllib.request.Request(
        IBGE_MESH_URL.format(codigo_ibge=codigo_ibge),
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "User-Agent": "saas-campanha-eleitoral-migration-generator/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        raw = response.read()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        payload = json.loads(raw.decode("utf-8"))

    features = payload.get("features") or []
    if not features:
        raise ValueError(f"Malha IBGE vazia para UF {codigo_ibge}.")
    return features[0]["geometry"]


def geometry_to_update(codigo_ibge: int, geometry: dict) -> str:
    geojson = json.dumps(geometry, ensure_ascii=False, separators=(",", ":"))
    return "\n".join(
        [
            f"UPDATE global.estado",
            "SET limite_geom = ST_Multi(",
            "        ST_CollectionExtract(",
            "            ST_MakeValid(",
            f"                ST_SetSRID(ST_GeomFromGeoJSON($geojson${geojson}$geojson$), 4326)",
            "            ),",
            "            3",
            "        )",
            "    )::geography",
            f"WHERE codigo_ibge = {codigo_ibge};",
        ]
    )


def main() -> None:
    updates: list[str] = []
    for codigo_ibge in STATE_CODES:
        geometry = fetch_state_geometry(codigo_ibge)
        updates.append(geometry_to_update(codigo_ibge, geometry))
        print(f"Fetched UF {codigo_ibge} ({geometry['type']})")

    content = "\n".join(
        [
            "-- Limites oficiais das unidades federativas (IBGE).",
            "-- Fonte: API de Malhas Geograficas v3 (qualidade minima), SRID 4326.",
            f"-- Total de estados atualizados: {len(updates)}",
            "",
            "BEGIN;",
            "",
            "ALTER TABLE global.estado",
            "    ADD COLUMN IF NOT EXISTS limite_geom geography(MultiPolygon, 4326);",
            "",
            "COMMENT ON COLUMN global.estado.limite_geom IS",
            "    'Limite oficial da unidade federativa conforme malha IBGE (WGS84).';",
            "",
            *updates,
            "",
            "DO $$",
            "DECLARE",
            "    estados_sem_limite INTEGER;",
            "BEGIN",
            "    SELECT count(*)",
            "    INTO estados_sem_limite",
            "    FROM global.estado",
            "    WHERE limite_geom IS NULL;",
            "",
            "    IF estados_sem_limite > 0 THEN",
            "        RAISE EXCEPTION",
            "            'Existem % estado(s) sem limite_geom apos a carga IBGE.', estados_sem_limite;",
            "    END IF;",
            "END",
            "$$;",
            "",
            "CREATE INDEX IF NOT EXISTS ix_estado_limite_geom",
            "    ON global.estado",
            "    USING GIST (limite_geom);",
            "",
            "COMMIT;",
            "",
        ]
    )

    OUT_PATH.write_text(content, encoding="utf-8")
    print(f"Generated {OUT_PATH} with {len(updates)} updates")


if __name__ == "__main__":
    main()
