-- Acelera a camada de locais de votacao, consultada pelos limites visiveis do mapa.
BEGIN;

CREATE INDEX IF NOT EXISTS ix_local_votacao_ativo_latitude_longitude
    ON global.local_votacao (latitude, longitude)
    WHERE situacao = 'ativo'
      AND latitude IS NOT NULL
      AND longitude IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_local_votacao_zona_ativa_georreferenciada
    ON global.local_votacao (zona_eleitoral_id, latitude, longitude)
    WHERE situacao = 'ativo'
      AND zona_eleitoral_id IS NOT NULL
      AND latitude IS NOT NULL
      AND longitude IS NOT NULL;

COMMIT;
