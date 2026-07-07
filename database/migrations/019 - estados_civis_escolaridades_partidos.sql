BEGIN;

-- Catalogo global de estados civis.
CREATE TABLE IF NOT EXISTS cadastro.estado_civil (
    id      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo  VARCHAR(30) NOT NULL,
    nome    VARCHAR(60) NOT NULL,
    ordem   SMALLINT NOT NULL,
    CONSTRAINT uq_estado_civil_codigo UNIQUE (codigo),
    CONSTRAINT uq_estado_civil_nome UNIQUE (nome)
);

COMMENT ON TABLE cadastro.estado_civil IS
    'Catalogo padronizado de estados civis utilizado no cadastro de pessoas.';

INSERT INTO cadastro.estado_civil (codigo, nome, ordem) VALUES
    ('solteiro', 'Solteiro(a)', 1),
    ('casado', 'Casado(a)', 2),
    ('uniao_estavel', 'União estável', 3),
    ('separado_judicialmente', 'Separado(a) judicialmente', 4),
    ('divorciado', 'Divorciado(a)', 5),
    ('viuvo', 'Viúvo(a)', 6)
ON CONFLICT (codigo) DO UPDATE
SET nome = EXCLUDED.nome,
    ordem = EXCLUDED.ordem;

-- Converte os valores textuais existentes antes de alterar o tipo da coluna.
DO $$
DECLARE
    tipo_atual TEXT;
BEGIN
    SELECT c.data_type
      INTO tipo_atual
      FROM information_schema.columns c
     WHERE c.table_schema = 'cadastro'
       AND c.table_name = 'pessoa'
       AND c.column_name = 'estado_civil';

    IF tipo_atual IN ('character varying', 'character', 'text') THEN
        UPDATE cadastro.pessoa p
           SET estado_civil = ec.id::TEXT
          FROM cadastro.estado_civil ec
         WHERE p.estado_civil IS NOT NULL
           AND ec.codigo = CASE lower(trim(p.estado_civil))
               WHEN 'solteiro' THEN 'solteiro'
               WHEN 'solteira' THEN 'solteiro'
               WHEN 'solteiro(a)' THEN 'solteiro'
               WHEN 'casado' THEN 'casado'
               WHEN 'casada' THEN 'casado'
               WHEN 'casado(a)' THEN 'casado'
               WHEN 'união estável' THEN 'uniao_estavel'
               WHEN 'uniao estavel' THEN 'uniao_estavel'
               WHEN 'convivente' THEN 'uniao_estavel'
               WHEN 'separado' THEN 'separado_judicialmente'
               WHEN 'separada' THEN 'separado_judicialmente'
               WHEN 'separado(a)' THEN 'separado_judicialmente'
               WHEN 'separado judicialmente' THEN 'separado_judicialmente'
               WHEN 'separada judicialmente' THEN 'separado_judicialmente'
               WHEN 'divorciado' THEN 'divorciado'
               WHEN 'divorciada' THEN 'divorciado'
               WHEN 'divorciado(a)' THEN 'divorciado'
               WHEN 'viúvo' THEN 'viuvo'
               WHEN 'viúva' THEN 'viuvo'
               WHEN 'viuvo' THEN 'viuvo'
               WHEN 'viuva' THEN 'viuvo'
               WHEN 'viúvo(a)' THEN 'viuvo'
               ELSE NULL
           END;

        -- Valores legados sem correspondencia conhecida nao devem impedir a migration.
        UPDATE cadastro.pessoa
           SET estado_civil = NULL
         WHERE estado_civil IS NOT NULL
           AND estado_civil !~ '^[0-9]+$';

        ALTER TABLE cadastro.pessoa
            ALTER COLUMN estado_civil TYPE INTEGER
            USING NULLIF(estado_civil, '')::INTEGER;

        UPDATE cadastro.pessoa p
           SET estado_civil = NULL
         WHERE p.estado_civil IS NOT NULL
           AND NOT EXISTS (
               SELECT 1
                 FROM cadastro.estado_civil ec
                WHERE ec.id = p.estado_civil
           );
    ELSIF tipo_atual <> 'integer' THEN
        RAISE EXCEPTION
            'Tipo inesperado para cadastro.pessoa.estado_civil: %', tipo_atual;
    END IF;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'fk_pessoa_estado_civil'
           AND conrelid = 'cadastro.pessoa'::regclass
    ) THEN
        ALTER TABLE cadastro.pessoa
            ADD CONSTRAINT fk_pessoa_estado_civil
            FOREIGN KEY (estado_civil)
            REFERENCES cadastro.estado_civil(id)
            ON DELETE SET NULL;
    END IF;
END;
$$;

COMMENT ON COLUMN cadastro.pessoa.estado_civil IS
    'Estado civil padronizado, referenciado por cadastro.estado_civil.';

-- Niveis de escolaridade, do menor para o maior grau de formacao.
INSERT INTO cadastro.escolaridade (nome, ordem) VALUES
    ('Analfabeto', 1),
    ('Alfabetizado (lê e escreve)', 2),
    ('Educação infantil', 3),
    ('Ensino fundamental incompleto', 4),
    ('Ensino fundamental completo', 5),
    ('Ensino médio incompleto', 6),
    ('Ensino médio completo', 7),
    ('Ensino técnico incompleto', 8),
    ('Ensino técnico completo', 9),
    ('Ensino superior incompleto', 10),
    ('Ensino superior completo', 11),
    ('Especialização', 12),
    ('Mestrado', 13),
    ('Doutorado', 14),
    ('Pós-doutorado', 15)
ON CONFLICT (nome) DO UPDATE
SET ordem = EXCLUDED.ordem;

-- Partidos com registro vigente no Tribunal Superior Eleitoral.
INSERT INTO cadastro.partido (sigla, nome, numero) VALUES
    ('MDB', 'Movimento Democrático Brasileiro', 15),
    ('PDT', 'Partido Democrático Trabalhista', 12),
    ('PT', 'Partido dos Trabalhadores', 13),
    ('PCdoB', 'Partido Comunista do Brasil', 65),
    ('PSB', 'Partido Socialista Brasileiro', 40),
    ('PSDB', 'Partido da Social Democracia Brasileira', 45),
    ('AGIR', 'Agir', 36),
    ('MOBILIZA', 'Mobilização Nacional', 33),
    ('CIDADANIA', 'Cidadania', 23),
    ('PV', 'Partido Verde', 43),
    ('AVANTE', 'Avante', 70),
    ('PP', 'Progressistas', 11),
    ('PSTU', 'Partido Socialista dos Trabalhadores Unificado', 16),
    ('PCB', 'Partido Comunista Brasileiro', 21),
    ('PRTB', 'Partido Renovador Trabalhista Brasileiro', 28),
    ('DC', 'Democracia Cristã', 27),
    ('PCO', 'Partido da Causa Operária', 29),
    ('PODE', 'Podemos', 20),
    ('REPUBLICANOS', 'Republicanos', 10),
    ('PSOL', 'Partido Socialismo e Liberdade', 50),
    ('PL', 'Partido Liberal', 22),
    ('PSD', 'Partido Social Democrático', 55),
    ('SOLIDARIEDADE', 'Solidariedade', 77),
    ('NOVO', 'Partido Novo', 30),
    ('REDE', 'Rede Sustentabilidade', 18),
    ('DEMOCRATA', 'Democrata', 35),
    ('UP', 'Unidade Popular', 80),
    ('UNIÃO', 'União Brasil', 44),
    ('PRD', 'Partido Renovação Democrática', 25),
    ('MISSÃO', 'Partido Missão', 14)
ON CONFLICT (sigla) DO UPDATE
SET nome = EXCLUDED.nome,
    numero = EXCLUDED.numero;

-- Catalogo global de profissoes mais utilizadas em cadastros de pessoas.
WITH profissoes(nome) AS (
    VALUES
        ('Administrador(a)'),
        ('Advogado(a)'),
        ('Agricultor(a)'),
        ('Agrônomo(a)'),
        ('Analista de dados'),
        ('Analista de sistemas'),
        ('Arquiteto(a)'),
        ('Artesão(ã)'),
        ('Assistente administrativo(a)'),
        ('Assistente social'),
        ('Atendente'),
        ('Ator/Atriz'),
        ('Autônomo(a)'),
        ('Auxiliar administrativo(a)'),
        ('Auxiliar de serviços gerais'),
        ('Bancário(a)'),
        ('Barbeiro(a)'),
        ('Biólogo(a)'),
        ('Bombeiro(a)'),
        ('Cabeleireiro(a)'),
        ('Caminhoneiro(a)'),
        ('Carpinteiro(a)'),
        ('Comerciante'),
        ('Comissário(a) de bordo'),
        ('Comunicador(a)'),
        ('Contador(a)'),
        ('Corretor(a) de imóveis'),
        ('Cozinheiro(a)'),
        ('Cuidador(a)'),
        ('Dentista'),
        ('Designer'),
        ('Doméstico(a)'),
        ('Economista'),
        ('Eletricista'),
        ('Empresário(a)'),
        ('Enfermeiro(a)'),
        ('Engenheiro(a)'),
        ('Esteticista'),
        ('Farmacêutico(a)'),
        ('Feirante'),
        ('Fisioterapeuta'),
        ('Fotógrafo(a)'),
        ('Funcionário(a) público(a)'),
        ('Garçom/Garçonete'),
        ('Geógrafo(a)'),
        ('Jornalista'),
        ('Manicure/Pedicure'),
        ('Mecânico(a)'),
        ('Médico(a)'),
        ('Militar'),
        ('Motorista'),
        ('Nutricionista'),
        ('Operador(a) de máquinas'),
        ('Pedreiro(a)'),
        ('Pescador(a)'),
        ('Policial'),
        ('Professor(a)'),
        ('Profissional de educação física'),
        ('Profissional de marketing'),
        ('Programador(a)'),
        ('Psicólogo(a)'),
        ('Publicitário(a)'),
        ('Recepcionista'),
        ('Representante comercial'),
        ('Secretário(a)'),
        ('Segurança/Vigilante'),
        ('Técnico(a) de enfermagem'),
        ('Técnico(a) em informática'),
        ('Terapeuta ocupacional'),
        ('Trabalhador(a) da construção civil'),
        ('Trabalhador(a) rural'),
        ('Turismólogo(a)'),
        ('Vendedor(a)'),
        ('Veterinário(a)'),
        ('Aposentado(a)'),
        ('Desempregado(a)'),
        ('Do lar'),
        ('Estudante'),
        ('Outra')
)
INSERT INTO cadastro.profissao (tenant_id, nome)
SELECT NULL, p.nome
  FROM profissoes p
 WHERE NOT EXISTS (
     SELECT 1
       FROM cadastro.profissao existente
      WHERE existente.tenant_id IS NULL
        AND existente.nome = p.nome
 );

-- Religioes e opcoes de declaracao. A coleta deve observar a base legal da LGPD.
INSERT INTO cadastro.religiao (nome) VALUES
    ('Agnóstico'),
    ('Ateu'),
    ('Adventista'),
    ('Anglicana/Episcopal'),
    ('Assembleia de Deus'),
    ('Batista'),
    ('Budista'),
    ('Candomblé'),
    ('Católica Apostólica Brasileira'),
    ('Católica Apostólica Romana'),
    ('Congregação Cristã no Brasil'),
    ('Espírita'),
    ('Evangélica - outras denominações'),
    ('Hinduísta'),
    ('Igreja de Jesus Cristo dos Santos dos Últimos Dias'),
    ('Judaica'),
    ('Luterana'),
    ('Metodista'),
    ('Muçulmana/Islâmica'),
    ('Ortodoxa'),
    ('Pentecostal - outras denominações'),
    ('Presbiteriana'),
    ('Religiões de matriz africana - outras'),
    ('Religiões e espiritualidades indígenas'),
    ('Testemunhas de Jeová'),
    ('Tradições esotéricas'),
    ('Umbanda'),
    ('Sem religião'),
    ('Prefere não informar'),
    ('Outra')
ON CONFLICT (nome) DO NOTHING;

GRANT SELECT, INSERT, UPDATE, DELETE
    ON cadastro.estado_civil
    TO app_inteligencia;
GRANT USAGE, SELECT
    ON SEQUENCE cadastro.estado_civil_id_seq
    TO app_inteligencia;

COMMIT;
