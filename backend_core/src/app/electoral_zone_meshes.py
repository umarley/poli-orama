"""Consulta compartilhada das malhas eleitorais calculadas a partir dos locais."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def list_electoral_zone_meshes(
    session: AsyncSession,
    *,
    south: float,
    west: float,
    north: float,
    east: float,
    limit: int,
    ufs: list[str] | None = None,
    municipality_tse_codes: list[int] | None = None,
    zone_numbers: list[int] | None = None,
    polling_place_codes: list[int] | None = None,
    section_numbers: list[int] | None = None,
    scope_unrestricted: bool = True,
    scope_ufs: list[str] | None = None,
    scope_municipalities_ibge: list[int] | None = None,
    scope_zone_ids: list[int] | None = None,
    scope_section_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    clauses = [
        "lv.situacao='ativo'",
        "lv.zona_eleitoral_id IS NOT NULL",
        "lv.latitude IS NOT NULL",
        "lv.longitude IS NOT NULL",
        "lv.latitude BETWEEN :south AND :north",
        "lv.longitude BETWEEN :west AND :east",
    ]
    values: dict[str, Any] = {
        "south": south,
        "west": west,
        "north": north,
        "east": east,
        "limit": limit,
    }
    optional_filters = (
        (ufs, "e.uf = ANY(:ufs)", "ufs"),
        (
            municipality_tse_codes,
            "m.codigo_tse = ANY(:municipality_tse_codes)",
            "municipality_tse_codes",
        ),
        (zone_numbers, "ze.numero_zona = ANY(:zone_numbers)", "zone_numbers"),
        (
            polling_place_codes,
            "lv.codigo_local = ANY(:polling_place_codes)",
            "polling_place_codes",
        ),
    )
    for items, expression, name in optional_filters:
        if items:
            clauses.append(expression)
            values[name] = items
    if section_numbers:
        clauses.append(
            "EXISTS (SELECT 1 FROM global.secao_eleitoral sf "
            "WHERE sf.local_votacao_id=lv.id AND sf.numero_secao=ANY(:section_numbers))"
        )
        values["section_numbers"] = section_numbers
    if not scope_unrestricted:
        scope_parts: list[str] = []
        for items, expression, name in (
            (scope_ufs, "e.uf = ANY(:scope_ufs)", "scope_ufs"),
            (
                scope_municipalities_ibge,
                "m.codigo_ibge = ANY(:scope_municipalities_ibge)",
                "scope_municipalities_ibge",
            ),
            (scope_zone_ids, "ze.id = ANY(:scope_zone_ids)", "scope_zone_ids"),
        ):
            if items:
                scope_parts.append(expression)
                values[name] = items
        if scope_section_ids:
            scope_parts.append(
                "EXISTS (SELECT 1 FROM global.secao_eleitoral ss "
                "WHERE ss.local_votacao_id=lv.id AND ss.id=ANY(:scope_section_ids))"
            )
            values["scope_section_ids"] = scope_section_ids
        clauses.append(f"({' OR '.join(scope_parts)})" if scope_parts else "FALSE")

    where = " AND ".join(clauses)
    rows = (
        (
            await session.execute(
                text(
                    "WITH candidate_zones AS ("
                    " SELECT DISTINCT lv.zona_eleitoral_id"
                    " FROM global.local_votacao lv"
                    " JOIN global.zona_eleitoral ze ON ze.id=lv.zona_eleitoral_id"
                    " LEFT JOIN global.municipio m"
                    " ON m.codigo_ibge=ze.codigo_municipio_ibge"
                    " LEFT JOIN global.estado e ON e.codigo_ibge=ze.codigo_uf_ibge"
                    f" WHERE {where}"
                    "), zone_hulls AS ("
                    " SELECT ze.id,ze.numero_zona,m.nome AS municipio,"
                    " count(lv.id)::int AS quantidade_locais,"
                    " ST_ConvexHull(ST_Collect(ST_SetSRID(ST_MakePoint("
                    " lv.longitude::double precision,lv.latitude::double precision),4326)))"
                    " AS geometry"
                    " FROM candidate_zones cz"
                    " JOIN global.zona_eleitoral ze ON ze.id=cz.zona_eleitoral_id"
                    " LEFT JOIN global.municipio m"
                    " ON m.codigo_ibge=ze.codigo_municipio_ibge"
                    " JOIN global.local_votacao lv ON lv.zona_eleitoral_id=ze.id"
                    " AND lv.situacao='ativo' AND lv.latitude IS NOT NULL"
                    " AND lv.longitude IS NOT NULL"
                    " GROUP BY ze.id,ze.numero_zona,m.nome"
                    " HAVING count(DISTINCT (lv.longitude,lv.latitude)) >= 3"
                    ") SELECT id,numero_zona,municipio,quantidade_locais,"
                    " ST_AsGeoJSON(geometry,6)::json AS geometry"
                    " FROM zone_hulls WHERE GeometryType(geometry)='POLYGON'"
                    " AND ST_Intersects(geometry,ST_MakeEnvelope("
                    " :west,:south,:east,:north,4326))"
                    " ORDER BY numero_zona,id LIMIT :limit"
                ),
                values,
            )
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]
