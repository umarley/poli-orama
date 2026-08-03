-- Inclui Barrolândia/TO, ausente na carga inicial de municípios.
-- Fontes:
--   IBGE Cidades@: https://www.ibge.gov.br/cidades-e-estados/to/barrolandia.html
--   IBGE, mapa municipal: localização da sede (-9.83, -48.72)
--   IBGE, API de Malhas Geográficas v3 (qualidade mínima): limite municipal
--   TSE, Perfil do Eleitorado 2026: código eleitoral 96997
--   Prefeitura de Barrolândia: data de criação em 11 de janeiro de 1988

BEGIN;

INSERT INTO global.municipio (
    codigo_ibge,
    codigo_uf_ibge,
    codigo_tse,
    nome,
    latitude,
    longitude,
    geom,
    limite_geom,
    capital,
    data_aniversario
) VALUES (
    1703107,
    17,
    96997,
    'Barrolândia',
    -9.8340400,
    -48.7252000,
    ST_SetSRID(ST_MakePoint(-48.7252000, -9.8340400), 4326)::geography,
    ST_Multi(
        ST_CollectionExtract(
            ST_MakeValid(
                ST_SetSRID(
                    ST_GeomFromGeoJSON(
                        $geojson${"type":"Polygon","coordinates":[[[-48.8239,-10.0566],[-48.7723,-10.0145],[-48.7447,-9.9708],[-48.7306,-9.9071],[-48.6972,-9.8918],[-48.6539,-9.9028],[-48.6251,-9.865],[-48.6302,-9.8314],[-48.6577,-9.7849],[-48.6525,-9.7559],[-48.7051,-9.7708],[-48.7553,-9.7536],[-48.8299,-9.7458],[-48.8606,-9.73],[-48.8611,-9.757],[-48.8875,-9.7705],[-48.9297,-9.7451],[-48.9723,-9.8404],[-48.9677,-9.8529],[-48.9319,-9.8281],[-48.8947,-9.8357],[-48.8506,-9.8993],[-48.8818,-10.0009],[-48.9006,-10.0271],[-48.8893,-10.0631],[-48.881,-10.0264],[-48.8239,-10.0566]]]}$geojson$
                    ),
                    4326
                )
            ),
            3
        )
    )::geography,
    FALSE,
    '11/01'
)
ON CONFLICT (codigo_ibge) DO UPDATE
SET codigo_uf_ibge = EXCLUDED.codigo_uf_ibge,
    codigo_tse = EXCLUDED.codigo_tse,
    nome = EXCLUDED.nome,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    geom = EXCLUDED.geom,
    limite_geom = EXCLUDED.limite_geom,
    capital = EXCLUDED.capital,
    data_aniversario = EXCLUDED.data_aniversario;

COMMIT;
