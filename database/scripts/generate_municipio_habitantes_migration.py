"""Gera migration 042 com updates de habitantes (estimativa IBGE 2024)."""

from __future__ import annotations

import gzip
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_PATH = (
    ROOT
    / "app_saas"
    / "database"
    / "migrations"
    / "042 - municipio_habitantes_ibge.sql"
)

IBGE_URL = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/6579/"
    "periodos/2024/variaveis/9324?localidades=N6[all]"
)


def fetch_population_by_municipality() -> dict[int, int]:
    request = urllib.request.Request(
        IBGE_URL,
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

    series_items = payload[0]["resultados"][0]["series"]
    population: dict[int, int] = {}
    for item in series_items:
        codigo_ibge = int(item["localidade"]["id"])
        value = item["serie"].get("2024")
        raw_value = str(value).strip().replace(".", "").replace(",", "")
        if not raw_value.isdigit():
            continue
        habitantes = int(raw_value)
        population[codigo_ibge] = habitantes
    return population


def main() -> None:
    population = fetch_population_by_municipality()
    updates = [
        f"UPDATE global.municipio SET habitantes = {habitantes} WHERE codigo_ibge = {codigo_ibge};"
        for codigo_ibge, habitantes in sorted(population.items())
    ]

    content = "\n".join(
        [
            "-- Populacao estimada dos municipios brasileiros (IBGE, estimativa 2024).",
            "-- Fonte: SIDRA agregado 6579, variavel 9324 (Populacao residente estimada).",
            f"-- Total de municipios atualizados: {len(updates)}",
            "",
            "BEGIN;",
            "",
            "ALTER TABLE global.municipio",
            "    ADD COLUMN IF NOT EXISTS habitantes INTEGER;",
            "",
            "COMMENT ON COLUMN global.municipio.habitantes IS",
            "    'Populacao residente estimada do municipio conforme IBGE (habitantes).';",
            "",
            "ALTER TABLE global.municipio",
            "    ADD CONSTRAINT ck_municipio_habitantes_nao_negativo",
            "    CHECK (habitantes IS NULL OR habitantes >= 0);",
            "",
            *updates,
            "",
            "COMMIT;",
            "",
        ]
    )

    OUT_PATH.write_text(content, encoding="utf-8")
    print(f"Generated {OUT_PATH} with {len(updates)} updates")


if __name__ == "__main__":
    main()
