# Dicionário de Dados - Plataforma SaaS de Inteligência Política

Este documento descreve a estrutura de banco de dados da plataforma, detalhando schemas, tabelas, colunas, restrições e comentários.

## 1. Visão Geral e Estratégia

A arquitetura de dados foi projetada em **PostgreSQL** e adota os seguintes padrões:
* **Multitenancy (SaaS):** Isolamento de dados entre políticos/candidatos assinantes utilizando **Row-Level Security (RLS)** nativo do banco de dados. Todas as tabelas sensíveis possuem a coluna `tenant_id`.
* **Auditoria e LGPD:** Colunas padronizadas (`criado_em`, `atualizado_em`, `criado_por`, `atualizado_por`, `excluido_em`) e schema de auditoria para trilhas e logs de exportação.
* **Chaves e IDs:** Chaves primárias (`id`) numéricas usando `BIGINT GENERATED ALWAYS AS IDENTITY` e identificadores públicos em `UUID` (`uuid_publico`) para exposição segura em APIs.
* **Georreferenciamento:** Uso da extensão **PostGIS** para tratar localizações geográficas e áreas.

## 2. Schemas

### 2.1. Schema `public`

**Descrição:** Schema padrão utilizado para a gestão do SaaS, contendo o cadastro dos políticos/candidatos assinantes (tenants) e planos de assinatura.

#### Tabela: `public.plano_assinatura`

**Descrição:** Planos comerciais do SaaS, limites, recursos habilitados e regras de cobranca.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `uuid_publico` | `uuid` |  |  | Não | gen_random_uuid() | Identificador público para APIs |
| `nome` | `varchar(120)` |  |  | Não |  |  |
| `descricao` | `text` |  |  | Sim |  |  |
| `preco_mensal` | `numeric(12,2)` |  |  | Não | 0 | Restrição: CHECK ((preco_mensal >= (0)::numeric)) |
| `moeda` | `character(3)` |  |  | Não | 'BRL'::bpchar |  |
| `limite_usuarios` | `integer` |  |  | Sim |  | Restrição: CHECK (((limite_usuarios IS NULL) OR (limite_usuarios > 0))) |
| `limite_pessoas` | `integer` |  |  | Sim |  | Restrição: CHECK (((limite_pessoas IS NULL) OR (limite_pessoas > 0))) |
| `limite_armazenamento_mb` | `integer` |  |  | Sim |  | Restrição: CHECK (((limite_armazenamento_mb IS NULL) OR (limite_armazenamento_mb > 0))) |
| `recursos` | `jsonb` |  |  | Não | '{}'::jsonb |  |
| `ativo` | `boolean` |  |  | Não | true |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |



#### Tabela: `public.tenant`

**Descrição:** Político ou candidato assinante da plataforma. Unidade principal de isolamento dos dados.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `uuid_publico` | `uuid` |  |  | Não | gen_random_uuid() | Identificador público para APIs |
| `nome` | `varchar(180)` |  |  | Não |  |  |
| `slug` | `varchar(80)` |  |  | Não |  |  |
| `documento` | `varchar(20)` |  |  | Sim |  |  |
| `tem_mandato` | `boolean` |  |  | Não | false |  |
| `plano_assinatura_id` | `bigint` |  | plano_assinatura(id) | Sim |  |  |
| `data_inicio_contrato` | `date` |  |  | Sim |  |  |
| `data_fim_contrato` | `date` |  |  | Sim |  |  |
| `status` | `varchar(20)` |  |  | Não | 'ativo'::character varying | Restrição: CHECK (((status)::text = ANY ((ARRAY['ativo'::character varying, 'suspenso'::character varying, 'cancelado'::character varying, 'trial'::character varying, 'inadimplente'::character varying])::text[]))) |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |
| `excluido_em` | `timestamptz` |  |  | Sim |  |  |

#### Tabela: `public.tenant_configuracao`

**Descrição:** Configuracoes especificas de cada tenant: nome publico, preferencias, integracoes e parametros operacionais.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `nome_publico` | `varchar(180)` |  |  | Sim |  |  |
| `cor_primaria` | `varchar(9)` |  |  | Sim |  |  |
| `logo_url` | `text` |  |  | Sim |  |  |
| `fuso_horario` | `varchar(60)` |  |  | Não | 'America/Sao_Paulo'::character varying |  |
| `percentual_alerta_meta` | `numeric(5,2)` |  |  | Não | 70.00 | Restrição: CHECK (((percentual_alerta_meta >= (0)::numeric) AND (percentual_alerta_meta <= (100)::numeric))) |
| `integracoes` | `jsonb` |  |  | Não | '{}'::jsonb |  |
| `preferencias` | `jsonb` |  |  | Não | '{}'::jsonb |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |

### 2.2. Schema `global`

**Descrição:** Dados compartilhados entre todos os tenants: UF, municipios, bairros, zonas, secoes, locais de votacao, datas comemorativas e bases TSE/IBGE.

#### Tabela: `global.bairro`

**Descrição:** Bairros por municipio. Pode ter origem oficial ou cadastro manual da campanha.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `integer` | Sim |  | Não | Auto-increment | Chave primária |
| `municipio_id` | `integer` |  | municipio(id) | Não |  |  |
| `nome` | `varchar(150)` |  |  | Não |  |  |
| `origem` | `varchar(20)` |  |  | Não | 'oficial'::character varying | Restrição: CHECK (((origem)::text = ANY ((ARRAY['oficial'::character varying, 'manual'::character varying, 'importado'::character varying])::text[]))) |

#### Tabela: `global.categoria_data_comemorativa`

**Descrição:** Classifica datas comemorativas: aniversario municipal, religiosa, civica, cultural ou comunitaria.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `nome` | `varchar(80)` |  |  | Não |  |  |
| `descricao` | `varchar(255)` |  |  | Sim |  |  |

#### Tabela: `global.data_comemorativa`

**Descrição:** Datas civicas, religiosas, municipais, culturais e setoriais para relacionamento politico e alertas.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `integer` | Sim |  | Não | Auto-increment | Chave primária |
| `categoria_id` | `smallint` |  | categoria_data_comemorativa(id) | Sim |  |  |
| `nome` | `varchar(180)` |  |  | Não |  |  |
| `descricao` | `text` |  |  | Sim |  |  |
| `dia` | `smallint` |  |  | Sim |  | Restrição: CHECK (((dia >= 1) AND (dia <= 31))) |
| `mes` | `smallint` |  |  | Sim |  | Restrição: CHECK (((mes >= 1) AND (mes <= 12))) |
| `data_movel` | `boolean` |  |  | Não | false |  |
| `ambito` | `varchar(20)` |  |  | Não | 'nacional'::character varying | Restrição: CHECK (((ambito)::text = ANY ((ARRAY['nacional'::character varying, 'estadual'::character varying, 'municipal'::character varying, 'regional'::character varying, 'setorial'::character varying])::text[]))) |
| `estado_id` | `smallint` |  | estado(id) | Sim |  |  |
| `municipio_id` | `integer` |  | municipio(id) | Sim |  |  |
| `ativo` | `boolean` |  |  | Não | true |  |

#### Tabela: `global.estado`

**Descrição:** Unidades federativas brasileiras (UF) com codigo IBGE.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `codigo_ibge` | `smallint` |  |  | Não |  |  |
| `uf` | `character(2)` |  |  | Não |  |  |
| `nome` | `varchar(60)` |  |  | Não |  |  |
| `regiao` | `varchar(20)` |  |  | Sim |  |  |

#### Tabela: `global.local_votacao`

**Descrição:** Local oficial de votacao com endereco, georreferencia e situacao cadastral.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `integer` | Sim |  | Não | Auto-increment | Chave primária |
| `municipio_id` | `integer` |  | municipio(id) | Não |  |  |
| `zona_eleitoral_id` | `integer` |  | zona_eleitoral(id) | Sim |  |  |
| `bairro_id` | `integer` |  | bairro(id) | Sim |  |  |
| `codigo_local` | `integer` |  |  | Sim |  |  |
| `nome` | `varchar(180)` |  |  | Não |  |  |
| `logradouro` | `varchar(180)` |  |  | Sim |  |  |
| `numero` | `varchar(20)` |  |  | Sim |  |  |
| `complemento` | `varchar(120)` |  |  | Sim |  |  |
| `cep` | `varchar(9)` |  |  | Sim |  |  |
| `latitude` | `numeric(10,7)` |  |  | Sim |  |  |
| `longitude` | `numeric(10,7)` |  |  | Sim |  |  |
| `geom` | `geography(Point,4326)` |  |  | Sim |  |  |
| `situacao` | `varchar(20)` |  |  | Não | 'ativo'::character varying | Restrição: CHECK (((situacao)::text = ANY ((ARRAY['ativo'::character varying, 'inativo'::character varying, 'desativado'::character varying])::text[]))) |

#### Tabela: `global.municipio`

**Descrição:** Cadastro oficial de municipios, integrado com codigo IBGE e codigo TSE.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `integer` | Sim |  | Não | Auto-increment | Chave primária |
| `estado_id` | `smallint` |  | estado(id) | Não |  |  |
| `codigo_ibge` | `integer` |  |  | Não |  |  |
| `codigo_tse` | `integer` |  |  | Sim |  |  |
| `nome` | `varchar(120)` |  |  | Não |  |  |
| `latitude` | `numeric(10,7)` |  |  | Sim |  |  |
| `longitude` | `numeric(10,7)` |  |  | Sim |  |  |
| `geom` | `geography(Point,4326)` |  |  | Sim |  |  |
| `data_aniversario` | `date` |  |  | Sim |  |  |

#### Tabela: `global.secao_eleitoral`

**Descrição:** Secao eleitoral oficial, vinculada a zona eleitoral e local de votacao.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `zona_eleitoral_id` | `integer` |  | zona_eleitoral(id) | Não |  |  |
| `local_votacao_id` | `integer` |  | local_votacao(id) | Sim |  |  |
| `numero_secao` | `smallint` |  |  | Não |  |  |
| `agregada_em` | `smallint` |  |  | Sim |  |  |

#### Tabela: `global.zona_eleitoral`

**Descrição:** Zona eleitoral oficial do TSE, vinculada a UF e municipio.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `integer` | Sim |  | Não | Auto-increment | Chave primária |
| `estado_id` | `smallint` |  | estado(id) | Não |  |  |
| `municipio_id` | `integer` |  | municipio(id) | Sim |  |  |
| `numero_zona` | `smallint` |  |  | Não |  |  |
| `descricao` | `varchar(150)` |  |  | Sim |  |  |

### 2.3. Schema `auth`

**Descrição:** Autenticacao, autorizacao e seguranca: usuarios, perfis, permissoes, sessoes e politicas de acesso territorial.

#### Tabela: `auth.perfil_acesso`

**Descrição:** Papel de acesso: gestor, coordenador territorial, lider, telefonista, atendimento, RH, administrativo.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Sim |  | Isolamento de dados (Multitenant) |
| `nome` | `varchar(80)` |  |  | Não |  |  |
| `codigo` | `varchar(50)` |  |  | Não |  |  |
| `descricao` | `varchar(255)` |  |  | Sim |  |  |
| `nivel` | `smallint` |  |  | Não | 5 |  |
| `sistema` | `boolean` |  |  | Não | false |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `auth.perfil_permissao`

**Descrição:** Associacao entre perfis de acesso e permissoes.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `perfil_acesso_id` | `bigint` | Sim | perfil_acesso(id) | Não |  |  |
| `permissao_id` | `bigint` | Sim | permissao(id) | Não |  |  |
| `concedida_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `auth.permissao`

**Descrição:** Permissao granular sobre modulos, acoes, tipos de dados e exportacoes.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `codigo` | `varchar(100)` |  |  | Não |  |  |
| `modulo` | `varchar(60)` |  |  | Não |  |  |
| `acao` | `varchar(30)` |  |  | Não |  | Restrição: CHECK (((acao)::text = ANY ((ARRAY['visualizar'::character varying, 'criar'::character varying, 'editar'::character varying, 'excluir'::character varying, 'exportar'::character varying, 'aprovar'::character varying, 'administrar'::character varying])::text[]))) |
| `descricao` | `varchar(255)` |  |  | Sim |  |  |

#### Tabela: `auth.politica_acesso_territorial`

**Descrição:** Define quais territorios/regioes/cidades/bairros/zonas/secoes um usuario pode visualizar ou administrar.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `usuario_id` | `bigint` |  | usuario(id) | Não |  |  |
| `tipo_escopo` | `varchar(30)` |  |  | Não |  | Restrição: CHECK (((tipo_escopo)::text = ANY ((ARRAY['estado'::character varying, 'municipio'::character varying, 'bairro'::character varying, 'zona_eleitoral'::character varying, 'secao_eleitoral'::character varying, 'territorio'::character varying, 'global'::character varying])::text[]))) |
| `estado_id` | `smallint` |  | estado(id) | Sim |  |  |
| `municipio_id` | `integer` |  | municipio(id) | Sim |  |  |
| `bairro_id` | `integer` |  | bairro(id) | Sim |  |  |
| `zona_eleitoral_id` | `integer` |  | zona_eleitoral(id) | Sim |  |  |
| `secao_eleitoral_id` | `bigint` |  | secao_eleitoral(id) | Sim |  |  |
| `territorio_id` | `bigint` |  | territorio(id) | Sim |  |  |
| `pode_administrar` | `boolean` |  |  | Não | false |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `auth.sessao_usuario`

**Descrição:** Sessoes ativas, tokens, dispositivos, IPs e datas de expiracao.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `usuario_id` | `bigint` |  | usuario(id) | Não |  |  |
| `token_hash` | `text` |  |  | Não |  |  |
| `refresh_token_hash` | `text` |  |  | Sim |  |  |
| `dispositivo` | `varchar(180)` |  |  | Sim |  |  |
| `user_agent` | `text` |  |  | Sim |  |  |
| `ip_origem` | `inet` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `expira_em` | `timestamptz` |  |  | Não |  |  |
| `revogada_em` | `timestamptz` |  |  | Sim |  |  |

#### Tabela: `auth.usuario`

**Descrição:** Conta de acesso ao sistema, vinculada a um tenant e opcionalmente a uma pessoa cadastrada.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `uuid_publico` | `uuid` |  |  | Não | gen_random_uuid() | Identificador público para APIs |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `pessoa_id` | `bigint` |  | pessoa(id) | Sim |  |  |
| `nome` | `varchar(180)` |  |  | Não |  |  |
| `email` | `citext` |  |  | Não |  |  |
| `hash_senha` | `text` |  |  | Não |  |  |
| `telefone` | `varchar(20)` |  |  | Sim |  |  |
| `mfa_habilitado` | `boolean` |  |  | Não | false |  |
| `mfa_segredo` | `text` |  |  | Sim |  |  |
| `status` | `varchar(20)` |  |  | Não | 'ativo'::character varying | Restrição: CHECK (((status)::text = ANY ((ARRAY['ativo'::character varying, 'inativo'::character varying, 'bloqueado'::character varying, 'pendente'::character varying])::text[]))) |
| `ultimo_login_em` | `timestamptz` |  |  | Sim |  |  |
| `tentativas_login` | `smallint` |  |  | Não | 0 |  |
| `senha_alterada_em` | `timestamptz` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |
| `excluido_em` | `timestamptz` |  |  | Sim |  |  |

#### Tabela: `auth.usuario_perfil`

**Descrição:** Associacao entre usuarios e perfis, permitindo mais de um papel por usuario.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `usuario_id` | `bigint` | Sim | usuario(id) | Não |  |  |
| `perfil_acesso_id` | `bigint` | Sim | perfil_acesso(id) | Não |  |  |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `atribuido_em` | `timestamptz` |  |  | Não | now() |  |

### 2.4. Schema `cadastro`

**Descrição:** Cadastro central: pessoas, documentos, contatos, enderecos, vinculos, liderancas, comunidades, tags e nucleos familiares.

#### Tabela: `cadastro.comunidade`

**Descrição:** Grupo social, religioso, profissional, territorial ou politico ao qual pessoas podem pertencer.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `nome` | `varchar(150)` |  |  | Não |  |  |
| `tipo` | `varchar(40)` |  |  | Sim |  | Restrição: CHECK (((tipo)::text = ANY ((ARRAY['religiosa'::character varying, 'profissional'::character varying, 'territorial'::character varying, 'politica'::character varying, 'social'::character varying, 'esportiva'::character varying, 'cultural'::character varying, 'outra'::character varying])::text[]))) |
| `descricao` | `text` |  |  | Sim |  |  |
| `lider_responsavel_id` | `bigint` |  | lideranca(id) | Sim |  |  |
| `municipio_id` | `integer` |  | municipio(id) | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `cadastro.eleitor`

**Descrição:** Extensao da pessoa com dados eleitorais: titulo, zona, secao e local de votacao.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `pessoa_id` | `bigint` |  | pessoa(id) | Não |  |  |
| `titulo_eleitor` | `varchar(20)` |  |  | Sim |  |  |
| `zona_eleitoral_id` | `integer` |  | zona_eleitoral(id) | Sim |  |  |
| `secao_eleitoral_id` | `bigint` |  | secao_eleitoral(id) | Sim |  |  |
| `local_votacao_id` | `integer` |  | local_votacao(id) | Sim |  |  |
| `municipio_voto_id` | `integer` |  | municipio(id) | Sim |  |  |
| `situacao_titulo` | `varchar(30)` |  |  | Sim | 'regular'::character varying | Restrição: CHECK (((situacao_titulo)::text = ANY ((ARRAY['regular'::character varying, 'suspenso'::character varying, 'cancelado'::character varying, 'desconhecido'::character varying])::text[]))) |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `cadastro.endereco`

**Descrição:** Endereco estruturado com logradouro, numero, complemento, bairro, cidade, CEP e georreferencia.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `municipio_id` | `integer` |  | municipio(id) | Sim |  |  |
| `bairro_id` | `integer` |  | bairro(id) | Sim |  |  |
| `bairro_texto` | `varchar(150)` |  |  | Sim |  |  |
| `logradouro` | `varchar(180)` |  |  | Sim |  |  |
| `numero` | `varchar(20)` |  |  | Sim |  |  |
| `complemento` | `varchar(120)` |  |  | Sim |  |  |
| `cep` | `varchar(9)` |  |  | Sim |  |  |
| `ponto_referencia` | `varchar(180)` |  |  | Sim |  |  |
| `latitude` | `numeric(10,7)` |  |  | Sim |  |  |
| `longitude` | `numeric(10,7)` |  |  | Sim |  |  |
| `geom` | `geography(Point,4326)` |  |  | Sim |  |  |
| `geocodificado` | `boolean` |  |  | Não | false |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `cadastro.escolaridade`

**Descrição:** Niveis de escolaridade padronizados.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `nome` | `varchar(80)` |  |  | Não |  |  |
| `ordem` | `smallint` |  |  | Sim |  |  |

#### Tabela: `cadastro.hierarquia_lideranca`

**Descrição:** Relacoes entre coordenador geral, coordenador territorial, lider, liderado e apoiador.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `lideranca_superior_id` | `bigint` |  | lideranca(id) | Não |  |  |
| `pessoa_subordinada_id` | `bigint` |  | pessoa(id) | Não |  |  |
| `papel_subordinado` | `varchar(30)` |  |  | Não | 'liderado'::character varying | Restrição: CHECK (((papel_subordinado)::text = ANY ((ARRAY['lider'::character varying, 'liderado'::character varying, 'apoiador'::character varying, 'eleitor'::character varying])::text[]))) |
| `data_inicio` | `date` |  |  | Não | CURRENT_DATE |  |
| `data_fim` | `date` |  |  | Sim |  |  |
| `ativo` | `boolean` |  |  | Não | true |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `cadastro.indicacao`

**Descrição:** Registra quem indicou quem, origem da indicacao, data e contexto.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `pessoa_indicada_id` | `bigint` |  | pessoa(id) | Não |  |  |
| `pessoa_indicante_id` | `bigint` |  | pessoa(id) | Sim |  |  |
| `origem` | `varchar(60)` |  |  | Sim |  |  |
| `contexto` | `varchar(255)` |  |  | Sim |  |  |
| `data_indicacao` | `date` |  |  | Não | CURRENT_DATE |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `cadastro.lideranca`

**Descrição:** Papel operacional de lideranca: tipo de lider, coordenador responsavel, equipe, meta associada.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `pessoa_id` | `bigint` |  | pessoa(id) | Não |  |  |
| `tipo_lideranca` | `varchar(40)` |  |  | Não | 'lider'::character varying | Restrição: CHECK (((tipo_lideranca)::text = ANY ((ARRAY['coordenador_geral'::character varying, 'coordenador_territorial'::character varying, 'lider'::character varying, 'sublider'::character varying])::text[]))) |
| `coordenador_id` | `bigint` |  | lideranca(id) | Sim |  |  |
| `apelido_campanha` | `varchar(120)` |  |  | Sim |  |  |
| `ativo` | `boolean` |  |  | Não | true |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `cadastro.nucleo_familiar`

**Descrição:** Grupo familiar usado para mobilizacao, metas e analise territorial.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `nome` | `varchar(150)` |  |  | Sim |  |  |
| `pessoa_referencia_id` | `bigint` |  | pessoa(id) | Sim |  |  |
| `endereco_id` | `bigint` |  | endereco(id) | Sim |  |  |
| `quantidade_membros` | `smallint` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `cadastro.partido`

**Descrição:** Partidos politicos para vinculos, historico ou relacionamento institucional.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `sigla` | `varchar(20)` |  |  | Não |  |  |
| `nome` | `varchar(120)` |  |  | Não |  |  |
| `numero` | `smallint` |  |  | Sim |  |  |

#### Tabela: `cadastro.pessoa`

**Descrição:** Entidade central: eleitor, apoiador, lider, coordenador, contato institucional ou integrante de equipe.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `uuid_publico` | `uuid` |  |  | Não | gen_random_uuid() | Identificador público para APIs |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `nome_completo` | `varchar(180)` |  |  | Não |  |  |
| `nome_social` | `varchar(180)` |  |  | Sim |  |  |
| `apelido` | `varchar(120)` |  |  | Sim |  |  |
| `sexo` | `character(1)` |  |  | Sim |  | Restrição: CHECK ((sexo = ANY (ARRAY['M'::bpchar, 'F'::bpchar, 'O'::bpchar, 'N'::bpchar]))) |
| `data_nascimento` | `date` |  |  | Sim |  |  |
| `estado_civil` | `varchar(30)` |  |  | Sim |  |  |
| `escolaridade_id` | `smallint` |  | escolaridade(id) | Sim |  |  |
| `profissao_id` | `integer` |  | profissao(id) | Sim |  |  |
| `religiao_id` | `smallint` |  | religiao(id) | Sim |  |  |
| `foto_arquivo_id` | `bigint` |  | arquivo(id) | Sim |  |  |
| `nivel_engajamento` | `smallint` |  |  | Sim |  | Restrição: CHECK (((nivel_engajamento >= 0) AND (nivel_engajamento <= 10))) |
| `score_confiabilidade` | `numeric(5,2)` |  |  | Sim |  | Restrição: CHECK (((score_confiabilidade >= (0)::numeric) AND (score_confiabilidade <= (100)::numeric))) |
| `completude_cadastral` | `numeric(5,2)` |  |  | Sim |  | Restrição: CHECK (((completude_cadastral >= (0)::numeric) AND (completude_cadastral <= (100)::numeric))) |
| `fonte_dado_id` | `bigint` |  | fonte_dado(id) | Sim |  |  |
| `observacoes` | `text` |  |  | Sim |  |  |
| `ativo` | `boolean` |  |  | Não | true |  |
| `criado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `atualizado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |
| `excluido_em` | `timestamptz` |  |  | Sim |  |  |

#### Tabela: `cadastro.pessoa_complemento_politico`

**Descrição:** Informacoes politicas e de engajamento: vinculo, partido, cargo, funcao, temas de interesse e nivel de engajamento.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `pessoa_id` | `bigint` |  | pessoa(id) | Não |  |  |
| `vinculo_politico` | `varchar(120)` |  |  | Sim |  |  |
| `partido_id` | `smallint` |  | partido(id) | Sim |  |  |
| `cargo_funcao` | `varchar(120)` |  |  | Sim |  |  |
| `temas_interesse` | `jsonb` |  |  | Não | '[]'::jsonb |  |
| `nivel_engajamento` | `smallint` |  |  | Sim |  | Restrição: CHECK (((nivel_engajamento >= 0) AND (nivel_engajamento <= 10))) |
| `observacoes` | `text` |  |  | Sim |  |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `cadastro.pessoa_comunidade`

**Descrição:** Associacao entre pessoas e comunidades.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `pessoa_id` | `bigint` | Sim | pessoa(id) | Não |  |  |
| `comunidade_id` | `bigint` | Sim | comunidade(id) | Não |  |  |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `papel` | `varchar(40)` |  |  | Sim |  |  |
| `desde` | `date` |  |  | Sim | CURRENT_DATE |  |

#### Tabela: `cadastro.pessoa_contato`

**Descrição:** Telefones, WhatsApp, e-mails e outros canais de contato da pessoa.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `pessoa_id` | `bigint` |  | pessoa(id) | Não |  |  |
| `tipo_contato` | `varchar(20)` |  |  | Não |  | Restrição: CHECK (((tipo_contato)::text = ANY ((ARRAY['telefone'::character varying, 'celular'::character varying, 'whatsapp'::character varying, 'email'::character varying, 'outro'::character varying])::text[]))) |
| `valor` | `varchar(180)` |  |  | Não |  |  |
| `principal` | `boolean` |  |  | Não | false |  |
| `verificado` | `boolean` |  |  | Não | false |  |
| `observacao` | `varchar(255)` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `cadastro.pessoa_documento`

**Descrição:** Documentos pessoais: CPF, RG, titulo de eleitor e outros identificadores.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `pessoa_id` | `bigint` |  | pessoa(id) | Não |  |  |
| `tipo_documento` | `varchar(20)` |  |  | Não |  | Restrição: CHECK (((tipo_documento)::text = ANY ((ARRAY['cpf'::character varying, 'rg'::character varying, 'titulo_eleitor'::character varying, 'cnh'::character varying, 'passaporte'::character varying, 'outro'::character varying])::text[]))) |
| `numero` | `varchar(40)` |  |  | Não |  |  |
| `orgao_emissor` | `varchar(40)` |  |  | Sim |  |  |
| `uf_emissor` | `character(2)` |  |  | Sim |  |  |
| `data_emissao` | `date` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `cadastro.pessoa_endereco`

**Descrição:** Associacao entre pessoa e endereco (residencial, eleitoral, comercial ou temporario).

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `pessoa_id` | `bigint` |  | pessoa(id) | Não |  |  |
| `endereco_id` | `bigint` |  | endereco(id) | Não |  |  |
| `tipo` | `varchar(20)` |  |  | Não | 'residencial'::character varying | Restrição: CHECK (((tipo)::text = ANY ((ARRAY['residencial'::character varying, 'eleitoral'::character varying, 'comercial'::character varying, 'temporario'::character varying, 'outro'::character varying])::text[]))) |
| `principal` | `boolean` |  |  | Não | false |  |

#### Tabela: `cadastro.pessoa_nucleo_familiar`

**Descrição:** Associacao pessoa x nucleo familiar, permitindo multiplos vinculos quando necessario.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `pessoa_id` | `bigint` |  | pessoa(id) | Não |  |  |
| `nucleo_familiar_id` | `bigint` |  | nucleo_familiar(id) | Não |  |  |
| `parentesco` | `varchar(40)` |  |  | Sim |  |  |
| `responsavel` | `boolean` |  |  | Não | false |  |

#### Tabela: `cadastro.pessoa_pessoa_tipo`

**Descrição:** Associacao pessoa x tipos, permitindo que a mesma pessoa seja lider e eleitor, por exemplo.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `pessoa_id` | `bigint` | Sim | pessoa(id) | Não |  |  |
| `pessoa_tipo_id` | `smallint` | Sim | pessoa_tipo(id) | Não |  |  |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `cadastro.pessoa_rede_social`

**Descrição:** Perfis sociais associados a pessoa: Instagram, Facebook, TikTok, X e outros.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `pessoa_id` | `bigint` |  | pessoa(id) | Não |  |  |
| `rede` | `varchar(30)` |  |  | Não |  | Restrição: CHECK (((rede)::text = ANY ((ARRAY['instagram'::character varying, 'facebook'::character varying, 'tiktok'::character varying, 'x'::character varying, 'youtube'::character varying, 'linkedin'::character varying, 'outro'::character varying])::text[]))) |
| `usuario_perfil` | `varchar(120)` |  |  | Sim |  |  |
| `url` | `text` |  |  | Sim |  |  |
| `seguidores` | `integer` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `cadastro.pessoa_tag`

**Descrição:** Associacao entre pessoas e tags.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `pessoa_id` | `bigint` | Sim | pessoa(id) | Não |  |  |
| `tag_id` | `bigint` | Sim | tag(id) | Não |  |  |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `atribuido_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `cadastro.pessoa_tipo`

**Descrição:** Classificacao de pessoa: eleitor, apoiador, lider, coordenador, liderado, telefonista, contato institucional, voluntario.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `codigo` | `varchar(40)` |  |  | Não |  |  |
| `nome` | `varchar(80)` |  |  | Não |  |  |
| `descricao` | `varchar(255)` |  |  | Sim |  |  |

#### Tabela: `cadastro.profissao`

**Descrição:** Cadastro padronizado de profissoes para segmentacao e relatorios.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `integer` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Sim |  | Isolamento de dados (Multitenant) |
| `nome` | `varchar(120)` |  |  | Não |  |  |
| `cbo` | `varchar(10)` |  |  | Sim |  |  |

#### Tabela: `cadastro.relacionamento_pessoa`

**Descrição:** Relacoes entre pessoas: familiar, lideranca, amizade, apoio politico, institucional ou comunitario.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `pessoa_origem_id` | `bigint` |  | pessoa(id) | Não |  | Restrição: CHECK ((pessoa_origem_id <> pessoa_destino_id)) |
| `pessoa_destino_id` | `bigint` |  | pessoa(id) | Não |  | Restrição: CHECK ((pessoa_origem_id <> pessoa_destino_id)) |
| `tipo_relacao` | `varchar(40)` |  |  | Não |  | Restrição: CHECK (((tipo_relacao)::text = ANY ((ARRAY['familiar'::character varying, 'lideranca'::character varying, 'amizade'::character varying, 'apoio_politico'::character varying, 'contato_institucional'::character varying, 'comunitario'::character varying, 'outro'::character varying])::text[]))) |
| `descricao` | `varchar(255)` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `cadastro.religiao`

**Descrição:** Religioes ou denominacoes (coleta condicionada a base legal adequada - LGPD).

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `nome` | `varchar(80)` |  |  | Não |  |  |

#### Tabela: `cadastro.suspeita_duplicidade`

**Descrição:** Possiveis duplicidades por CPF, telefone, e-mail, titulo de eleitor, nome e data de nascimento.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `pessoa_id` | `bigint` |  | pessoa(id) | Não |  | Restrição: CHECK ((pessoa_id <> pessoa_duplicada_id)) |
| `pessoa_duplicada_id` | `bigint` |  | pessoa(id) | Não |  | Restrição: CHECK ((pessoa_id <> pessoa_duplicada_id)) |
| `criterio` | `varchar(40)` |  |  | Não |  | Restrição: CHECK (((criterio)::text = ANY ((ARRAY['cpf'::character varying, 'telefone'::character varying, 'email'::character varying, 'titulo_eleitor'::character varying, 'nome_data_nascimento'::character varying, 'fuzzy'::character varying])::text[]))) |
| `score_similaridade` | `numeric(5,2)` |  |  | Sim |  | Restrição: CHECK (((score_similaridade >= (0)::numeric) AND (score_similaridade <= (100)::numeric))) |
| `status` | `varchar(20)` |  |  | Não | 'pendente'::character varying | Restrição: CHECK (((status)::text = ANY ((ARRAY['pendente'::character varying, 'confirmada'::character varying, 'descartada'::character varying, 'mesclada'::character varying])::text[]))) |
| `resolvido_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `resolvido_em` | `timestamptz` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `cadastro.tag`

**Descrição:** Marcador de segmentacao: META 30, META 100, evangelico, juventude, saude, bairro especifico ou grupo estrategico.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `nome` | `varchar(80)` |  |  | Não |  |  |
| `cor` | `varchar(9)` |  |  | Sim |  |  |
| `categoria` | `varchar(40)` |  |  | Sim |  |  |
| `descricao` | `varchar(255)` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `cadastro.validacao_cadastro`

**Descrição:** Controla revisao, aprovacao, rejeicao ou pendencias de cadastros incompletos, duplicados ou sem lider.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `pessoa_id` | `bigint` |  | pessoa(id) | Não |  |  |
| `motivo` | `varchar(40)` |  |  | Não |  | Restrição: CHECK (((motivo)::text = ANY ((ARRAY['incompleto'::character varying, 'duplicado'::character varying, 'sem_lider'::character varying, 'dados_invalidos'::character varying, 'revisao_periodica'::character varying, 'outro'::character varying])::text[]))) |
| `status` | `varchar(20)` |  |  | Não | 'pendente'::character varying | Restrição: CHECK (((status)::text = ANY ((ARRAY['pendente'::character varying, 'aprovado'::character varying, 'rejeitado'::character varying, 'em_revisao'::character varying])::text[]))) |
| `observacao` | `text` |  |  | Sim |  |  |
| `revisado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `revisado_em` | `timestamptz` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

### 2.5. Schema `territorio`

**Descrição:** Estrutura territorial operacional e georreferenciamento.

#### Tabela: `territorio.area_mapa`

**Descrição:** Poligonos ou areas geograficas customizadas usadas em mapas, filtros e dashboards.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `nome` | `varchar(150)` |  |  | Não |  |  |
| `descricao` | `text` |  |  | Sim |  |  |
| `geom` | `geography(MultiPolygon,4326)` |  |  | Não |  |  |
| `cor` | `varchar(9)` |  |  | Sim |  |  |
| `criado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `territorio.geocodificacao`

**Descrição:** Resultados de geocodificacao de enderecos, eventos e demandas, com precisao, provedor e status.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `entidade_tipo` | `varchar(30)` |  |  | Não |  | Restrição: CHECK (((entidade_tipo)::text = ANY ((ARRAY['endereco'::character varying, 'evento'::character varying, 'demanda'::character varying, 'local_votacao'::character varying, 'pessoa'::character varying])::text[]))) |
| `entidade_id` | `bigint` |  |  | Não |  |  |
| `endereco_texto` | `text` |  |  | Sim |  |  |
| `latitude` | `numeric(10,7)` |  |  | Sim |  |  |
| `longitude` | `numeric(10,7)` |  |  | Sim |  |  |
| `geom` | `geography(Point,4326)` |  |  | Sim |  |  |
| `precisao` | `varchar(30)` |  |  | Sim |  | Restrição: CHECK (((precisao)::text = ANY ((ARRAY['exata'::character varying, 'aproximada'::character varying, 'centroide'::character varying, 'interpolada'::character varying, 'falha'::character varying])::text[]))) |
| `provedor` | `varchar(40)` |  |  | Sim |  |  |
| `status` | `varchar(20)` |  |  | Não | 'pendente'::character varying | Restrição: CHECK (((status)::text = ANY ((ARRAY['pendente'::character varying, 'sucesso'::character varying, 'falha'::character varying, 'revisar'::character varying])::text[]))) |
| `processado_em` | `timestamptz` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `territorio.lideranca_territorio`

**Descrição:** Territorios sob responsabilidade de lideres ou coordenadores.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `lideranca_id` | `bigint` |  | lideranca(id) | Não |  |  |
| `territorio_id` | `bigint` |  | territorio(id) | Não |  |  |
| `responsabilidade` | `varchar(20)` |  |  | Não | 'principal'::character varying | Restrição: CHECK (((responsabilidade)::text = ANY ((ARRAY['principal'::character varying, 'apoio'::character varying, 'compartilhada'::character varying])::text[]))) |

#### Tabela: `territorio.pessoa_territorio`

**Descrição:** Associa pessoas a territorios de moradia, atuacao, votacao ou responsabilidade.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `pessoa_id` | `bigint` |  | pessoa(id) | Não |  |  |
| `territorio_id` | `bigint` |  | territorio(id) | Não |  |  |
| `vinculo` | `varchar(20)` |  |  | Não | 'moradia'::character varying | Restrição: CHECK (((vinculo)::text = ANY ((ARRAY['moradia'::character varying, 'atuacao'::character varying, 'votacao'::character varying, 'responsabilidade'::character varying])::text[]))) |

#### Tabela: `territorio.territorio`

**Descrição:** Unidade territorial operacional: regiao, microrregiao, cidade, bairro, zona, secao ou area customizada.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `tipo_territorio_id` | `smallint` |  | tipo_territorio(id) | Não |  |  |
| `nome` | `varchar(150)` |  |  | Não |  |  |
| `estado_id` | `smallint` |  | estado(id) | Sim |  |  |
| `municipio_id` | `integer` |  | municipio(id) | Sim |  |  |
| `bairro_id` | `integer` |  | bairro(id) | Sim |  |  |
| `zona_eleitoral_id` | `integer` |  | zona_eleitoral(id) | Sim |  |  |
| `secao_eleitoral_id` | `bigint` |  | secao_eleitoral(id) | Sim |  |  |
| `geom` | `geography(MultiPolygon,4326)` |  |  | Sim |  |  |
| `ativo` | `boolean` |  |  | Não | true |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `territorio.territorio_hierarquia`

**Descrição:** Relacao pai-filho entre territorios, formando a arvore territorial.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `territorio_pai_id` | `bigint` |  | territorio(id) | Não |  | Restrição: CHECK ((territorio_pai_id <> territorio_filho_id)) |
| `territorio_filho_id` | `bigint` |  | territorio(id) | Não |  | Restrição: CHECK ((territorio_pai_id <> territorio_filho_id)) |

#### Tabela: `territorio.tipo_territorio`

**Descrição:** Classifica territorios: estado, municipio, bairro, zona, secao, microrregiao, comunidade ou area personalizada.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `codigo` | `varchar(40)` |  |  | Não |  |  |
| `nome` | `varchar(80)` |  |  | Não |  |  |
| `descricao` | `varchar(255)` |  |  | Sim |  |  |

### 2.6. Schema `agenda`

**Descrição:** Agenda politica: eventos, convites, presencas e pautas.

#### Tabela: `agenda.convite`

**Descrição:** Convite recebido ou emitido para evento, com origem, indicacao, arquivo anexado e status.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `evento_id` | `bigint` |  | evento(id) | Sim |  |  |
| `direcao` | `varchar(20)` |  |  | Não | 'recebido'::character varying | Restrição: CHECK (((direcao)::text = ANY ((ARRAY['recebido'::character varying, 'emitido'::character varying])::text[]))) |
| `origem` | `varchar(120)` |  |  | Sim |  |  |
| `pessoa_indicou_id` | `bigint` |  | pessoa(id) | Sim |  |  |
| `arquivo_id` | `bigint` |  | arquivo(id) | Sim |  |  |
| `status` | `varchar(20)` |  |  | Não | 'pendente'::character varying | Restrição: CHECK (((status)::text = ANY ((ARRAY['pendente'::character varying, 'aceito'::character varying, 'recusado'::character varying, 'confirmado'::character varying])::text[]))) |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `agenda.evento`

**Descrição:** Compromisso, reuniao, agenda politica, evento comunitario, religioso, partidario, institucional ou cultural.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `uuid_publico` | `uuid` |  |  | Não | gen_random_uuid() | Identificador público para APIs |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `tipo_evento_id` | `smallint` |  | tipo_evento(id) | Sim |  |  |
| `status_evento_id` | `smallint` |  | status_evento(id) | Sim |  |  |
| `titulo` | `varchar(180)` |  |  | Não |  |  |
| `descricao` | `text` |  |  | Sim |  |  |
| `data_inicio` | `timestamptz` |  |  | Não |  | Restrição: CHECK (((data_fim IS NULL) OR (data_fim >= data_inicio))) |
| `data_fim` | `timestamptz` |  |  | Sim |  | Restrição: CHECK (((data_fim IS NULL) OR (data_fim >= data_inicio))) |
| `local_nome` | `varchar(180)` |  |  | Sim |  |  |
| `endereco_id` | `bigint` |  | endereco(id) | Sim |  |  |
| `municipio_id` | `integer` |  | municipio(id) | Sim |  |  |
| `bairro_id` | `integer` |  | bairro(id) | Sim |  |  |
| `zona_eleitoral_id` | `integer` |  | zona_eleitoral(id) | Sim |  |  |
| `territorio_id` | `bigint` |  | territorio(id) | Sim |  |  |
| `latitude` | `numeric(10,7)` |  |  | Sim |  |  |
| `longitude` | `numeric(10,7)` |  |  | Sim |  |  |
| `geom` | `geography(Point,4326)` |  |  | Sim |  |  |
| `responsavel_pessoa_id` | `bigint` |  | pessoa(id) | Sim |  |  |
| `origem_convite` | `varchar(120)` |  |  | Sim |  |  |
| `pessoa_indicou_id` | `bigint` |  | pessoa(id) | Sim |  |  |
| `presenca_parlamentar` | `boolean` |  |  | Não | false |  |
| `presenca_representante` | `boolean` |  |  | Não | false |  |
| `numero_presentes` | `integer` |  |  | Sim |  | Restrição: CHECK (((numero_presentes IS NULL) OR (numero_presentes >= 0))) |
| `criado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |
| `excluido_em` | `timestamptz` |  |  | Sim |  |  |

#### Tabela: `agenda.evento_lideranca`

**Descrição:** Lideres ou coordenadores envolvidos em determinado evento.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `evento_id` | `bigint` | Sim | evento(id) | Não |  |  |
| `lideranca_id` | `bigint` | Sim | lideranca(id) | Não |  |  |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `papel` | `varchar(40)` |  |  | Sim |  |  |

#### Tabela: `agenda.evento_participante`

**Descrição:** Pessoas participantes do evento, incluindo presenca, papel e observacoes.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `evento_id` | `bigint` |  | evento(id) | Não |  |  |
| `pessoa_id` | `bigint` |  | pessoa(id) | Não |  |  |
| `papel` | `varchar(40)` |  |  | Sim |  |  |
| `presente` | `boolean` |  |  | Sim |  |  |
| `observacao` | `varchar(255)` |  |  | Sim |  |  |

#### Tabela: `agenda.pauta_evento`

**Descrição:** Pautas discutidas no evento, temas tratados e encaminhamentos.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `evento_id` | `bigint` |  | evento(id) | Não |  |  |
| `titulo` | `varchar(180)` |  |  | Não |  |  |
| `descricao` | `text` |  |  | Sim |  |  |
| `encaminhamento` | `text` |  |  | Sim |  |  |
| `ordem` | `smallint` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `agenda.presenca_evento`

**Descrição:** Registro detalhado de presenca do parlamentar, representante, lideres, convidados e numero estimado de presentes.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `evento_id` | `bigint` |  | evento(id) | Não |  |  |
| `presenca_parlamentar` | `boolean` |  |  | Não | false |  |
| `presenca_representante` | `boolean` |  |  | Não | false |  |
| `nome_representante` | `varchar(180)` |  |  | Sim |  |  |
| `numero_lideres_presentes` | `integer` |  |  | Sim |  |  |
| `numero_convidados` | `integer` |  |  | Sim |  |  |
| `numero_estimado_presentes` | `integer` |  |  | Sim |  |  |
| `observacao` | `text` |  |  | Sim |  |  |
| `registrado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `registrado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `agenda.status_evento`

**Descrição:** Situacao do evento: planejado, confirmado, realizado, cancelado ou remarcado.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `codigo` | `varchar(30)` |  |  | Não |  |  |
| `nome` | `varchar(60)` |  |  | Não |  |  |

#### Tabela: `agenda.tipo_evento`

**Descrição:** Classifica eventos: politico, religioso, comunitario, partidario, institucional ou cultural.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Sim |  | Isolamento de dados (Multitenant) |
| `codigo` | `varchar(40)` |  |  | Não |  |  |
| `nome` | `varchar(80)` |  |  | Não |  |  |

### 2.7. Schema `demanda`

**Descrição:** Demandas, pedidos, atendimentos e movimentacoes.

#### Tabela: `demanda.atendimento`

**Descrição:** Acao de atendimento vinculada a uma demanda, com responsavel, prazo, resultado e data de execucao.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `demanda_id` | `bigint` |  | demanda(id) | Não |  |  |
| `responsavel_atendimento_id` | `bigint` |  | responsavel_atendimento(id) | Sim |  |  |
| `resultado_atendimento_id` | `smallint` |  | resultado_atendimento(id) | Sim |  |  |
| `descricao` | `text` |  |  | Sim |  |  |
| `prazo` | `date` |  |  | Sim |  |  |
| `data_execucao` | `date` |  |  | Sim |  |  |
| `tempo_atendimento_horas` | `numeric(10,2)` |  |  | Sim |  |  |
| `criado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `demanda.categoria_demanda`

**Descrição:** Classifica demandas: saude, educacao, infraestrutura, emprego, seguranca, assistencia social, transporte ou habitacao.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Sim |  | Isolamento de dados (Multitenant) |
| `codigo` | `varchar(40)` |  |  | Não |  |  |
| `nome` | `varchar(80)` |  |  | Não |  |  |

#### Tabela: `demanda.demanda`

**Descrição:** Solicitacao, pedido ou necessidade registrada por pessoa, lideranca, comunidade ou evento.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `uuid_publico` | `uuid` |  |  | Não | gen_random_uuid() | Identificador público para APIs |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `protocolo` | `varchar(30)` |  |  | Sim |  |  |
| `categoria_demanda_id` | `smallint` |  | categoria_demanda(id) | Sim |  |  |
| `prioridade_demanda_id` | `smallint` |  | prioridade_demanda(id) | Sim |  |  |
| `status_demanda_id` | `smallint` |  | status_demanda(id) | Não |  |  |
| `origem_demanda_id` | `smallint` |  | origem_demanda(id) | Sim |  |  |
| `titulo` | `varchar(180)` |  |  | Sim |  |  |
| `descricao` | `text` |  |  | Não |  |  |
| `pessoa_solicitante_id` | `bigint` |  | pessoa(id) | Sim |  |  |
| `lideranca_indicacao_id` | `bigint` |  | lideranca(id) | Sim |  |  |
| `evento_id` | `bigint` |  | evento(id) | Sim |  |  |
| `territorio_id` | `bigint` |  | territorio(id) | Sim |  |  |
| `municipio_id` | `integer` |  | municipio(id) | Sim |  |  |
| `bairro_id` | `integer` |  | bairro(id) | Sim |  |  |
| `latitude` | `numeric(10,7)` |  |  | Sim |  |  |
| `longitude` | `numeric(10,7)` |  |  | Sim |  |  |
| `geom` | `geography(Point,4326)` |  |  | Sim |  |  |
| `data_solicitacao` | `date` |  |  | Não | CURRENT_DATE |  |
| `prazo` | `date` |  |  | Sim |  |  |
| `classificacao_automatica` | `boolean` |  |  | Não | false |  |
| `criado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |
| `excluido_em` | `timestamptz` |  |  | Sim |  |  |

#### Tabela: `demanda.movimentacao_demanda`

**Descrição:** Historico de mudancas de status, responsaveis, prazos, observacoes e encaminhamentos da demanda.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `demanda_id` | `bigint` |  | demanda(id) | Não |  |  |
| `status_anterior_id` | `smallint` |  | status_demanda(id) | Sim |  |  |
| `status_novo_id` | `smallint` |  | status_demanda(id) | Sim |  |  |
| `responsavel_anterior_id` | `bigint` |  | responsavel_atendimento(id) | Sim |  |  |
| `responsavel_novo_id` | `bigint` |  | responsavel_atendimento(id) | Sim |  |  |
| `observacao` | `text` |  |  | Sim |  |  |
| `usuario_id` | `bigint` |  | usuario(id) | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `demanda.origem_demanda`

**Descrição:** Origem da demanda: evento, ligacao, WhatsApp, cadastro manual, lider, comunidade ou importacao.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `codigo` | `varchar(30)` |  |  | Não |  |  |
| `nome` | `varchar(60)` |  |  | Não |  |  |

#### Tabela: `demanda.prioridade_demanda`

**Descrição:** Grau de prioridade operacional ou estrategica da demanda.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `codigo` | `varchar(20)` |  |  | Não |  |  |
| `nome` | `varchar(40)` |  |  | Não |  |  |
| `peso` | `smallint` |  |  | Sim |  |  |

#### Tabela: `demanda.responsavel_atendimento`

**Descrição:** Pessoa, usuario, setor ou area responsavel pelo atendimento de uma demanda.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `nome` | `varchar(150)` |  |  | Não |  |  |
| `tipo` | `varchar(20)` |  |  | Não | 'usuario'::character varying | Restrição: CHECK (((tipo)::text = ANY ((ARRAY['usuario'::character varying, 'pessoa'::character varying, 'setor'::character varying, 'area'::character varying])::text[]))) |
| `usuario_id` | `bigint` |  | usuario(id) | Sim |  |  |
| `pessoa_id` | `bigint` |  | pessoa(id) | Sim |  |  |
| `area` | `varchar(120)` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `demanda.resultado_atendimento`

**Descrição:** Resultado do atendimento: solucionado, parcialmente atendido ou nao atendido.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `codigo` | `varchar(30)` |  |  | Não |  |  |
| `nome` | `varchar(60)` |  |  | Não |  |  |

#### Tabela: `demanda.status_demanda`

**Descrição:** Situacao da demanda: pendente, em andamento, concluida, cancelada, nao atendida ou parcialmente atendida.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `codigo` | `varchar(30)` |  |  | Não |  |  |
| `nome` | `varchar(60)` |  |  | Não |  |  |
| `ordem` | `smallint` |  |  | Sim |  |  |
| `final` | `boolean` |  |  | Não | false |  |

### 2.8. Schema `meta`

**Descrição:** Metas de votos, acompanhamento, alertas de risco e ranking de liderancas.

#### Tabela: `meta.acompanhamento_meta`

**Descrição:** Historico de evolucao da meta: projecao, confirmacao, percentual atingido e situacao de risco.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `meta_voto_id` | `bigint` |  | meta_voto(id) | Não |  |  |
| `data_referencia` | `date` |  |  | Não | CURRENT_DATE |  |
| `quantidade_projetada` | `integer` |  |  | Sim |  | Restrição: CHECK (((quantidade_projetada IS NULL) OR (quantidade_projetada >= 0))) |
| `quantidade_confirmada` | `integer` |  |  | Sim |  | Restrição: CHECK (((quantidade_confirmada IS NULL) OR (quantidade_confirmada >= 0))) |
| `quantidade_eleitores_vinculados` | `integer` |  |  | Sim |  |  |
| `percentual_atingido` | `numeric(5,2)` |  |  | Sim |  | Restrição: CHECK (((percentual_atingido IS NULL) OR (percentual_atingido >= (0)::numeric))) |
| `situacao_risco` | `varchar(20)` |  |  | Não | 'normal'::character varying | Restrição: CHECK (((situacao_risco)::text = ANY ((ARRAY['normal'::character varying, 'atencao'::character varying, 'risco'::character varying, 'critico'::character varying])::text[]))) |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `meta.alerta_meta`

**Descrição:** Alertas para metas abaixo do esperado, por exemplo abaixo de 70% do previsto.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `meta_voto_id` | `bigint` |  | meta_voto(id) | Não |  |  |
| `tipo_alerta` | `varchar(30)` |  |  | Não | 'meta_abaixo_esperado'::character varying | Restrição: CHECK (((tipo_alerta)::text = ANY ((ARRAY['meta_abaixo_esperado'::character varying, 'meta_estagnada'::character varying, 'prazo_proximo'::character varying, 'outro'::character varying])::text[]))) |
| `percentual_referencia` | `numeric(5,2)` |  |  | Sim |  |  |
| `mensagem` | `varchar(255)` |  |  | Sim |  |  |
| `severidade` | `varchar(20)` |  |  | Não | 'media'::character varying | Restrição: CHECK (((severidade)::text = ANY ((ARRAY['baixa'::character varying, 'media'::character varying, 'alta'::character varying, 'critica'::character varying])::text[]))) |
| `resolvido` | `boolean` |  |  | Não | false |  |
| `gerado_em` | `timestamptz` |  |  | Não | now() |  |
| `resolvido_em` | `timestamptz` |  |  | Sim |  |  |

#### Tabela: `meta.meta_voto`

**Descrição:** Meta de votos para lider, equipe, territorio, comunidade, nucleo familiar ou campanha inteira.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `tipo_meta_voto_id` | `smallint` |  | tipo_meta_voto(id) | Não |  |  |
| `periodo_meta_id` | `bigint` |  | periodo_meta(id) | Sim |  |  |
| `titulo` | `varchar(150)` |  |  | Sim |  |  |
| `quantidade_meta` | `integer` |  |  | Não |  | Restrição: CHECK ((quantidade_meta >= 0)) |
| `lideranca_id` | `bigint` |  | lideranca(id) | Sim |  |  |
| `coordenador_id` | `bigint` |  | lideranca(id) | Sim |  |  |
| `territorio_id` | `bigint` |  | territorio(id) | Sim |  |  |
| `municipio_id` | `integer` |  | municipio(id) | Sim |  |  |
| `bairro_id` | `integer` |  | bairro(id) | Sim |  |  |
| `zona_eleitoral_id` | `integer` |  | zona_eleitoral(id) | Sim |  |  |
| `secao_eleitoral_id` | `bigint` |  | secao_eleitoral(id) | Sim |  |  |
| `comunidade_id` | `bigint` |  | comunidade(id) | Sim |  |  |
| `nucleo_familiar_id` | `bigint` |  | nucleo_familiar(id) | Sim |  |  |
| `status` | `varchar(20)` |  |  | Não | 'ativa'::character varying | Restrição: CHECK (((status)::text = ANY ((ARRAY['ativa'::character varying, 'concluida'::character varying, 'cancelada'::character varying, 'em_risco'::character varying, 'suspensa'::character varying])::text[]))) |
| `criado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `meta.meta_voto_alvo`

**Descrição:** Aponta o alvo da meta de forma flexivel: lideranca, territorio, equipe, comunidade, nucleo familiar ou pessoa.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `meta_voto_id` | `bigint` |  | meta_voto(id) | Não |  |  |
| `tipo_alvo` | `varchar(30)` |  |  | Não |  | Restrição: CHECK (((tipo_alvo)::text = ANY ((ARRAY['lideranca'::character varying, 'territorio'::character varying, 'equipe'::character varying, 'comunidade'::character varying, 'nucleo_familiar'::character varying, 'pessoa'::character varying])::text[]))) |
| `alvo_id` | `bigint` |  |  | Não |  |  |
| `quantidade_atribuida` | `integer` |  |  | Sim |  | Restrição: CHECK (((quantidade_atribuida IS NULL) OR (quantidade_atribuida >= 0))) |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `meta.periodo_meta`

**Descrição:** Periodo de validade da meta, com inicio, fim, ciclo e eleicao relacionada.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `nome` | `varchar(120)` |  |  | Não |  |  |
| `data_inicio` | `date` |  |  | Não |  | Restrição: CHECK ((data_fim >= data_inicio)) |
| `data_fim` | `date` |  |  | Não |  | Restrição: CHECK ((data_fim >= data_inicio)) |
| `ciclo` | `varchar(30)` |  |  | Sim |  |  |
| `eleicao_id` | `bigint` |  | eleicao(id) | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `meta.ranking_lideranca`

**Descrição:** Ranking calculado de lideres por desempenho: cadastros, confirmacoes, eventos, demandas e atingimento de metas.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `lideranca_id` | `bigint` |  | lideranca(id) | Não |  |  |
| `data_referencia` | `date` |  |  | Não | CURRENT_DATE |  |
| `posicao` | `integer` |  |  | Sim |  |  |
| `total_cadastros` | `integer` |  |  | Não | 0 |  |
| `total_confirmacoes` | `integer` |  |  | Não | 0 |  |
| `total_eventos` | `integer` |  |  | Não | 0 |  |
| `total_demandas` | `integer` |  |  | Não | 0 |  |
| `percentual_meta` | `numeric(5,2)` |  |  | Sim |  |  |
| `pontuacao` | `numeric(12,2)` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `meta.tipo_meta_voto`

**Descrição:** Classifica a meta: global, territorial, por lider, por equipe, por comunidade ou por nucleo familiar.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `codigo` | `varchar(30)` |  |  | Não |  |  |
| `nome` | `varchar(60)` |  |  | Não |  |  |

### 2.9. Schema `comunicacao`

**Descrição:** Comunicacao e relacionamento: interacoes, redes sociais, mensagens e campanhas.

#### Tabela: `comunicacao.campanha_comunicacao`

**Descrição:** Acao de comunicacao segmentada para publicos: aniversariantes, lideres, comunidades ou territorios.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `nome` | `varchar(150)` |  |  | Não |  |  |
| `descricao` | `text` |  |  | Sim |  |  |
| `canal_comunicacao_id` | `smallint` |  | canal_comunicacao(id) | Sim |  |  |
| `publico_alvo` | `jsonb` |  |  | Não | '{}'::jsonb |  |
| `data_agendada` | `timestamptz` |  |  | Sim |  |  |
| `status` | `varchar(20)` |  |  | Não | 'rascunho'::character varying | Restrição: CHECK (((status)::text = ANY ((ARRAY['rascunho'::character varying, 'agendada'::character varying, 'enviando'::character varying, 'concluida'::character varying, 'cancelada'::character varying])::text[]))) |
| `criado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `comunicacao.canal_comunicacao`

**Descrição:** Canal usado na comunicacao: WhatsApp, telefone, e-mail, Instagram, SMS ou presencial.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `codigo` | `varchar(30)` |  |  | Não |  |  |
| `nome` | `varchar(60)` |  |  | Não |  |  |

#### Tabela: `comunicacao.consentimento_comunicacao`

**Descrição:** Consentimento, base legal, preferencia de contato e eventual opt-out (LGPD).

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `pessoa_id` | `bigint` |  | pessoa(id) | Não |  |  |
| `canal_comunicacao_id` | `smallint` |  | canal_comunicacao(id) | Sim |  |  |
| `base_legal` | `varchar(60)` |  |  | Sim |  |  |
| `consentido` | `boolean` |  |  | Não | true |  |
| `finalidade` | `varchar(180)` |  |  | Sim |  |  |
| `data_consentimento` | `timestamptz` |  |  | Não | now() |  |
| `data_opt_out` | `timestamptz` |  |  | Sim |  |  |
| `origem` | `varchar(60)` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `comunicacao.engajamento_social`

**Descrição:** Metricas de curtidas, comentarios, compartilhamentos, alcance e interacoes por publicacao ou perfil.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `publicacao_social_id` | `bigint` |  | publicacao_social(id) | Sim |  |  |
| `perfil_social_monitorado_id` | `bigint` |  | perfil_social_monitorado(id) | Sim |  |  |
| `data_referencia` | `date` |  |  | Não | CURRENT_DATE |  |
| `curtidas` | `integer` |  |  | Não | 0 |  |
| `comentarios` | `integer` |  |  | Não | 0 |  |
| `compartilhamentos` | `integer` |  |  | Não | 0 |  |
| `alcance` | `integer` |  |  | Sim |  |  |
| `interacoes` | `integer` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `comunicacao.interacao`

**Descrição:** Contato com pessoa: ligacao, WhatsApp, visita, reuniao, mensagem, e-mail ou atendimento presencial.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `pessoa_id` | `bigint` |  | pessoa(id) | Sim |  |  |
| `tipo_interacao_id` | `smallint` |  | tipo_interacao(id) | Sim |  |  |
| `canal_comunicacao_id` | `smallint` |  | canal_comunicacao(id) | Sim |  |  |
| `lideranca_id` | `bigint` |  | lideranca(id) | Sim |  |  |
| `demanda_id` | `bigint` |  | demanda(id) | Sim |  |  |
| `evento_id` | `bigint` |  | evento(id) | Sim |  |  |
| `direcao` | `varchar(10)` |  |  | Não | 'saida'::character varying | Restrição: CHECK (((direcao)::text = ANY ((ARRAY['entrada'::character varying, 'saida'::character varying])::text[]))) |
| `assunto` | `varchar(180)` |  |  | Sim |  |  |
| `conteudo` | `text` |  |  | Sim |  |  |
| `resultado` | `varchar(120)` |  |  | Sim |  |  |
| `data_interacao` | `timestamptz` |  |  | Não | now() |  |
| `registrado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `comunicacao.mensagem_comunicacao`

**Descrição:** Mensagem individual ou em lote enviada ou registrada manualmente.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `campanha_comunicacao_id` | `bigint` |  | campanha_comunicacao(id) | Sim |  |  |
| `pessoa_id` | `bigint` |  | pessoa(id) | Sim |  |  |
| `canal_comunicacao_id` | `smallint` |  | canal_comunicacao(id) | Sim |  |  |
| `destinatario` | `varchar(180)` |  |  | Sim |  |  |
| `conteudo` | `text` |  |  | Sim |  |  |
| `status` | `varchar(20)` |  |  | Não | 'pendente'::character varying | Restrição: CHECK (((status)::text = ANY ((ARRAY['pendente'::character varying, 'enviada'::character varying, 'entregue'::character varying, 'lida'::character varying, 'falha'::character varying])::text[]))) |
| `enviado_em` | `timestamptz` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `comunicacao.perfil_social_monitorado`

**Descrição:** Perfil de rede social monitorado ou cadastrado, vinculado a pessoa, lideranca, campanha ou organizacao.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `rede` | `varchar(30)` |  |  | Não |  | Restrição: CHECK (((rede)::text = ANY ((ARRAY['instagram'::character varying, 'facebook'::character varying, 'tiktok'::character varying, 'x'::character varying, 'youtube'::character varying, 'whatsapp'::character varying, 'outro'::character varying])::text[]))) |
| `identificador` | `varchar(150)` |  |  | Não |  |  |
| `url` | `text` |  |  | Sim |  |  |
| `pessoa_id` | `bigint` |  | pessoa(id) | Sim |  |  |
| `lideranca_id` | `bigint` |  | lideranca(id) | Sim |  |  |
| `monitorar` | `boolean` |  |  | Não | true |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `comunicacao.publicacao_social`

**Descrição:** Publicacao em rede social capturada ou registrada manualmente para analise de engajamento.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `perfil_social_monitorado_id` | `bigint` |  | perfil_social_monitorado(id) | Não |  |  |
| `id_externo` | `varchar(120)` |  |  | Sim |  |  |
| `url` | `text` |  |  | Sim |  |  |
| `conteudo` | `text` |  |  | Sim |  |  |
| `tipo_midia` | `varchar(20)` |  |  | Sim |  |  |
| `publicado_em` | `timestamptz` |  |  | Sim |  |  |
| `capturado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `comunicacao.tipo_interacao`

**Descrição:** Classifica interacoes por canal e finalidade.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `codigo` | `varchar(30)` |  |  | Não |  |  |
| `nome` | `varchar(60)` |  |  | Não |  |  |

### 2.10. Schema `eleicao`

**Descrição:** Eleições, campanhas eleitorais e acompanhamento operacional do dia da votação.

#### Tabela: `eleicao.campanha_eleicao`

**Descrição:** Campanha eleitoral de um político ou candidato, vinculada ao tenant assinante e a uma eleição.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `uuid_publico` | `uuid` |  |  | Não | gen_random_uuid() | Identificador público para APIs |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Político/candidato assinante e isolamento multitenant |
| `eleicao_id` | `bigint` |  | eleicao(id) | Não |  | Eleição disputada pela campanha |
| `nome` | `varchar(180)` |  |  | Não |  | Nome de identificação da campanha |
| `cargo_pleiteado` | `varchar(120)` |  |  | Não |  | Cargo eletivo pleiteado pelo tenant nesta campanha |
| `ativa` | `boolean` |  |  | Não | false | Indica se a campanha está ativa |
| `data_ativacao` | `timestamptz` |  |  | Sim |  | Data e hora de ativação da campanha |
| `data_encerramento` | `timestamptz` |  |  | Sim |  | Data e hora de encerramento da campanha |
| `criado_por` | `bigint` |  | usuario(id) | Sim |  | Usuário responsável pelo cadastro |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |

Cada tenant pode possuir uma campanha por eleição, conforme a restrição única `(tenant_id, eleicao_id)`.

#### Tabela: `eleicao.campanha_configuracao`

**Descrição:** Configurações e parâmetros específicos de uma campanha eleitoral.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `campanha_eleicao_id` | `bigint` |  | campanha_eleicao(id) | Não |  | Campanha à qual a configuração pertence |
| `parametros` | `jsonb` |  |  | Não | '{}'::jsonb | Parâmetros operacionais específicos da campanha |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `eleicao.confirmacao_operacional_voto`

**Descrição:** Registro operacional informado por lider, eleitor ou equipe. NAO representa comprovacao oficial de voto individual (restricao etica/legal).

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `campanha_eleicao_id` | `bigint` |  | campanha_eleicao(id) | Não |  | Campanha eleitoral relacionada |
| `pessoa_id` | `bigint` |  | pessoa(id) | Não |  |  |
| `informado_por_tipo` | `varchar(20)` |  |  | Não |  | Restrição: CHECK (((informado_por_tipo)::text = ANY ((ARRAY['lider'::character varying, 'eleitor'::character varying, 'equipe'::character varying])::text[]))) |
| `informado_por_usuario_id` | `bigint` |  | usuario(id) | Sim |  |  |
| `confirmado` | `boolean` |  |  | Não | false |  |
| `observacao` | `varchar(255)` |  |  | Sim |  |  |
| `data_confirmacao` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `eleicao.eleicao`

**Descrição:** Cadastro da eleicao de referencia: ano, tipo, turno, data e escopo territorial.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Sim |  | Isolamento de dados (Multitenant) |
| `ano` | `smallint` |  |  | Não |  |  |
| `tipo` | `varchar(30)` |  |  | Não |  | Restrição: CHECK (((tipo)::text = ANY ((ARRAY['municipal'::character varying, 'estadual'::character varying, 'federal'::character varying, 'suplementar'::character varying, 'outra'::character varying])::text[]))) |
| `turno` | `smallint` |  |  | Não | 1 | Restrição: CHECK ((turno = ANY (ARRAY[1, 2]))) |
| `data_eleicao` | `date` |  |  | Não |  |  |
| `escopo_uf_id` | `smallint` |  | estado(id) | Sim |  |  |
| `escopo_municipio_id` | `integer` |  | municipio(id) | Sim |  |  |
| `descricao` | `varchar(180)` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `eleicao.ocorrencia_eleicao`

**Descrição:** Ocorrencias do dia da eleicao: transporte, dificuldade de contato, problema em local de votacao ou solicitacao de apoio.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `campanha_eleicao_id` | `bigint` |  | campanha_eleicao(id) | Não |  | Campanha eleitoral relacionada |
| `pessoa_id` | `bigint` |  | pessoa(id) | Sim |  |  |
| `lideranca_id` | `bigint` |  | lideranca(id) | Sim |  |  |
| `local_votacao_id` | `integer` |  | local_votacao(id) | Sim |  |  |
| `tipo` | `varchar(40)` |  |  | Não |  | Restrição: CHECK (((tipo)::text = ANY ((ARRAY['transporte'::character varying, 'dificuldade_contato'::character varying, 'problema_local'::character varying, 'solicitacao_apoio'::character varying, 'outro'::character varying])::text[]))) |
| `descricao` | `text` |  |  | Sim |  |  |
| `status` | `varchar(20)` |  |  | Não | 'aberta'::character varying | Restrição: CHECK (((status)::text = ANY ((ARRAY['aberta'::character varying, 'em_andamento'::character varying, 'resolvida'::character varying, 'cancelada'::character varying])::text[]))) |
| `registrado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `eleicao.painel_eleicao_snapshot`

**Descrição:** Fotografia periodica dos indicadores do modo eleicao para dashboards em tempo real ou historico.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `campanha_eleicao_id` | `bigint` |  | campanha_eleicao(id) | Não |  | Campanha eleitoral relacionada |
| `capturado_em` | `timestamptz` |  |  | Não | now() |  |
| `total_eleitores` | `integer` |  |  | Sim |  |  |
| `total_confirmados` | `integer` |  |  | Sim |  |  |
| `total_pendentes` | `integer` |  |  | Sim |  |  |
| `total_sem_resposta` | `integer` |  |  | Sim |  |  |
| `percentual_confirmacao` | `numeric(5,2)` |  |  | Sim |  |  |
| `indicadores` | `jsonb` |  |  | Não | '{}'::jsonb |  |

#### Tabela: `eleicao.status_eleitor_eleicao`

**Descrição:** Status operacional do eleitor no dia da eleicao: nao contatado, contatado, confirmado, pendente, precisa de apoio ou sem resposta.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `campanha_eleicao_id` | `bigint` |  | campanha_eleicao(id) | Não |  | Campanha eleitoral relacionada |
| `pessoa_id` | `bigint` |  | pessoa(id) | Não |  |  |
| `lideranca_id` | `bigint` |  | lideranca(id) | Sim |  |  |
| `status` | `varchar(30)` |  |  | Não | 'nao_contatado'::character varying | Restrição: CHECK (((status)::text = ANY ((ARRAY['nao_contatado'::character varying, 'contatado'::character varying, 'confirmado'::character varying, 'pendente'::character varying, 'precisa_apoio'::character varying, 'sem_resposta'::character varying])::text[]))) |
| `zona_eleitoral_id` | `integer` |  | zona_eleitoral(id) | Sim |  |  |
| `secao_eleitoral_id` | `bigint` |  | secao_eleitoral(id) | Sim |  |  |
| `local_votacao_id` | `integer` |  | local_votacao(id) | Sim |  |  |
| `atualizado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `atualizado_em` | `timestamptz` |  |  | Não | now() |  |

### 2.11. Schema `arquivo`

**Descrição:** Arquivos, anexos, fotos e documentos extraidos.

#### Tabela: `arquivo.anexo`

**Descrição:** Associacao de arquivo a entidades do sistema: pessoa, evento, demanda, comunicacao ou importacao.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `arquivo_id` | `bigint` |  | arquivo(id) | Não |  |  |
| `tipo_anexo_id` | `smallint` |  | tipo_anexo(id) | Sim |  |  |
| `entidade_tipo` | `varchar(30)` |  |  | Não |  | Restrição: CHECK (((entidade_tipo)::text = ANY ((ARRAY['pessoa'::character varying, 'evento'::character varying, 'demanda'::character varying, 'interacao'::character varying, 'importacao'::character varying, 'comunidade'::character varying, 'lideranca'::character varying, 'convite'::character varying])::text[]))) |
| `entidade_id` | `bigint` |  |  | Não |  |  |
| `descricao` | `varchar(255)` |  |  | Sim |  |  |
| `criado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `arquivo.arquivo`

**Descrição:** Registro logico de arquivo armazenado em data lake/storage com nome, tipo, tamanho, hash e localizacao.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `uuid_publico` | `uuid` |  |  | Não | gen_random_uuid() | Identificador público para APIs |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `nome_original` | `varchar(255)` |  |  | Não |  |  |
| `nome_armazenado` | `varchar(255)` |  |  | Sim |  |  |
| `mime_type` | `varchar(120)` |  |  | Sim |  |  |
| `extensao` | `varchar(20)` |  |  | Sim |  |  |
| `tamanho_bytes` | `bigint` |  |  | Sim |  | Restrição: CHECK (((tamanho_bytes IS NULL) OR (tamanho_bytes >= 0))) |
| `hash_sha256` | `character(64)` |  |  | Sim |  |  |
| `provedor_storage` | `varchar(40)` |  |  | Não | 's3'::character varying | Restrição: CHECK (((provedor_storage)::text = ANY ((ARRAY['s3'::character varying, 'azure_blob'::character varying, 'seaweedfs'::character varying, 'gcs'::character varying, 'local'::character varying, 'outro'::character varying])::text[]))) |
| `bucket` | `varchar(120)` |  |  | Sim |  |  |
| `caminho` | `text` |  |  | Não |  |  |
| `url_publica` | `text` |  |  | Sim |  |  |
| `criado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
| `excluido_em` | `timestamptz` |  |  | Sim |  |  |

#### Tabela: `arquivo.documento_extraido`

**Descrição:** Texto ou metadados extraidos de PDFs, imagens, convites, pautas ou documentos enviados.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `arquivo_id` | `bigint` |  | arquivo(id) | Não |  |  |
| `texto_extraido` | `text` |  |  | Sim |  |  |
| `metadados` | `jsonb` |  |  | Não | '{}'::jsonb |  |
| `metodo_extracao` | `varchar(40)` |  |  | Sim |  |  |
| `idioma` | `varchar(10)` |  |  | Sim |  |  |
| `processado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `arquivo.tipo_anexo`

**Descrição:** Classifica anexos: foto, convite, pauta, documento pessoal, comprovante, imagem, PDF ou planilha.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `codigo` | `varchar(30)` |  |  | Não |  |  |
| `nome` | `varchar(60)` |  |  | Não |  |  |

### 2.12. Schema `etl`

**Descrição:** Importacao, fontes externas, staging, qualidade e jobs de processamento.

#### Tabela: `etl.erro_importacao`

**Descrição:** Erros encontrados durante leitura, validacao, padronizacao ou carga dos dados.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `importacao_id` | `bigint` |  | importacao(id) | Não |  |  |
| `importacao_linha_id` | `bigint` |  | importacao_linha(id) | Sim |  |  |
| `etapa` | `varchar(30)` |  |  | Sim |  | Restrição: CHECK (((etapa)::text = ANY ((ARRAY['leitura'::character varying, 'validacao'::character varying, 'padronizacao'::character varying, 'carga'::character varying, 'deduplicacao'::character varying])::text[]))) |
| `campo` | `varchar(80)` |  |  | Sim |  |  |
| `mensagem` | `text` |  |  | Não |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `etl.fonte_dado`

**Descrição:** Origem de dados importados: GESPED, TSE, IBGE, planilhas, formularios, APIs ou cadastro manual.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `codigo` | `varchar(40)` |  |  | Não |  |  |
| `nome` | `varchar(120)` |  |  | Não |  |  |
| `tipo` | `varchar(30)` |  |  | Não |  | Restrição: CHECK (((tipo)::text = ANY ((ARRAY['gesped'::character varying, 'tse'::character varying, 'ibge'::character varying, 'planilha'::character varying, 'formulario'::character varying, 'api'::character varying, 'manual'::character varying, 'outro'::character varying])::text[]))) |
| `descricao` | `varchar(255)` |  |  | Sim |  |  |

#### Tabela: `etl.importacao`

**Descrição:** Processo de importacao de arquivo, API ou base externa, com status, usuario, origem e periodo.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Sim |  | Isolamento de dados (Multitenant) |
| `fonte_dado_id` | `bigint` |  | fonte_dado(id) | Sim |  |  |
| `descricao` | `varchar(180)` |  |  | Sim |  |  |
| `tipo_destino` | `varchar(40)` |  |  | Sim |  |  |
| `status` | `varchar(20)` |  |  | Não | 'pendente'::character varying | Restrição: CHECK (((status)::text = ANY ((ARRAY['pendente'::character varying, 'processando'::character varying, 'concluida'::character varying, 'falha'::character varying, 'parcial'::character varying, 'cancelada'::character varying])::text[]))) |
| `total_linhas` | `integer` |  |  | Sim |  |  |
| `linhas_validas` | `integer` |  |  | Sim |  |  |
| `linhas_erro` | `integer` |  |  | Sim |  |  |
| `iniciado_em` | `timestamptz` |  |  | Sim |  |  |
| `concluido_em` | `timestamptz` |  |  | Sim |  |  |
| `criado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `etl.importacao_arquivo`

**Descrição:** Arquivos vinculados a uma importacao especifica.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `importacao_id` | `bigint` |  | importacao(id) | Não |  |  |
| `arquivo_id` | `bigint` |  | arquivo(id) | Sim |  |  |
| `nome_arquivo` | `varchar(255)` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `etl.importacao_linha`

**Descrição:** Registro granular de linhas importadas, erros, avisos e status de processamento.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `importacao_id` | `bigint` |  | importacao(id) | Não |  |  |
| `numero_linha` | `integer` |  |  | Sim |  |  |
| `conteudo_bruto` | `jsonb` |  |  | Sim |  |  |
| `status` | `varchar(20)` |  |  | Não | 'pendente'::character varying | Restrição: CHECK (((status)::text = ANY ((ARRAY['pendente'::character varying, 'processada'::character varying, 'erro'::character varying, 'aviso'::character varying, 'ignorada'::character varying])::text[]))) |
| `mensagem` | `text` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `etl.job_processamento`

**Descrição:** Jobs assincronos: geocodificacao, deduplicacao, NLP, importacao, relatorio ou calculo de indicadores (Celery/Redis).

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Sim |  | Isolamento de dados (Multitenant) |
| `tipo` | `varchar(40)` |  |  | Não |  | Restrição: CHECK (((tipo)::text = ANY ((ARRAY['geocodificacao'::character varying, 'deduplicacao'::character varying, 'nlp'::character varying, 'importacao'::character varying, 'relatorio'::character varying, 'indicador'::character varying, 'outro'::character varying])::text[]))) |
| `referencia` | `varchar(120)` |  |  | Sim |  |  |
| `status` | `varchar(20)` |  |  | Não | 'enfileirado'::character varying | Restrição: CHECK (((status)::text = ANY ((ARRAY['enfileirado'::character varying, 'executando'::character varying, 'concluido'::character varying, 'falha'::character varying, 'cancelado'::character varying])::text[]))) |
| `parametros` | `jsonb` |  |  | Não | '{}'::jsonb |  |
| `tentativas` | `smallint` |  |  | Não | 0 |  |
| `iniciado_em` | `timestamptz` |  |  | Sim |  |  |
| `concluido_em` | `timestamptz` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `etl.log_processamento`

**Descrição:** Logs tecnicos e operacionais dos jobs de processamento.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `job_processamento_id` | `bigint` |  | job_processamento(id) | Sim |  |  |
| `nivel` | `varchar(10)` |  |  | Não | 'info'::character varying | Restrição: CHECK (((nivel)::text = ANY ((ARRAY['debug'::character varying, 'info'::character varying, 'warn'::character varying, 'error'::character varying, 'critical'::character varying])::text[]))) |
| `mensagem` | `text` |  |  | Não |  |  |
| `contexto` | `jsonb` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `etl.regra_deduplicacao`

**Descrição:** Criterios configuraveis para identificar duplicidades por CPF, telefone, e-mail, titulo, nome/data de nascimento ou score fuzzy.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Sim |  | Isolamento de dados (Multitenant) |
| `nome` | `varchar(120)` |  |  | Não |  |  |
| `criterio` | `varchar(40)` |  |  | Não |  | Restrição: CHECK (((criterio)::text = ANY ((ARRAY['cpf'::character varying, 'telefone'::character varying, 'email'::character varying, 'titulo_eleitor'::character varying, 'nome_data_nascimento'::character varying, 'fuzzy'::character varying])::text[]))) |
| `limiar_score` | `numeric(5,2)` |  |  | Sim |  |  |
| `ativa` | `boolean` |  |  | Não | true |  |
| `configuracao` | `jsonb` |  |  | Não | '{}'::jsonb |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `etl.resultado_deduplicacao`

**Descrição:** Resultado da aplicacao das regras de deduplicacao sobre registros importados ou cadastrados.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Sim |  | Isolamento de dados (Multitenant) |
| `regra_deduplicacao_id` | `bigint` |  | regra_deduplicacao(id) | Sim |  |  |
| `importacao_id` | `bigint` |  | importacao(id) | Sim |  |  |
| `registro_origem_id` | `bigint` |  |  | Sim |  |  |
| `registro_duplicado_id` | `bigint` |  |  | Sim |  |  |
| `score` | `numeric(5,2)` |  |  | Sim |  |  |
| `decisao` | `varchar(20)` |  |  | Não | 'pendente'::character varying | Restrição: CHECK (((decisao)::text = ANY ((ARRAY['pendente'::character varying, 'duplicado'::character varying, 'distinto'::character varying, 'mesclar'::character varying])::text[]))) |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `etl.staging_eleitorado_tse`

**Descrição:** Area temporaria para bases TSE antes de normalizar em tabelas globais ou analiticas.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `importacao_id` | `bigint` |  | importacao(id) | Sim |  |  |
| `ano` | `smallint` |  |  | Sim |  |  |
| `uf` | `character(2)` |  |  | Sim |  |  |
| `codigo_municipio_tse` | `integer` |  |  | Sim |  |  |
| `nome_municipio` | `varchar(120)` |  |  | Sim |  |  |
| `numero_zona` | `smallint` |  |  | Sim |  |  |
| `numero_secao` | `smallint` |  |  | Sim |  |  |
| `genero` | `varchar(30)` |  |  | Sim |  |  |
| `faixa_etaria` | `varchar(40)` |  |  | Sim |  |  |
| `grau_instrucao` | `varchar(60)` |  |  | Sim |  |  |
| `estado_civil` | `varchar(40)` |  |  | Sim |  |  |
| `quantidade_eleitores` | `integer` |  |  | Sim |  |  |
| `dados_extras` | `jsonb` |  |  | Não | '{}'::jsonb |  |
| `status` | `varchar(20)` |  |  | Não | 'novo'::character varying | Restrição: CHECK (((status)::text = ANY ((ARRAY['novo'::character varying, 'validado'::character varying, 'carregado'::character varying, 'descartado'::character varying])::text[]))) |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `etl.staging_pessoa`

**Descrição:** Area temporaria para dados de pessoas antes da validacao, deduplicacao e carga definitiva.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `importacao_id` | `bigint` |  | importacao(id) | Sim |  |  |
| `tenant_id` | `bigint` |  | tenant(id) | Sim |  | Isolamento de dados (Multitenant) |
| `nome_completo` | `varchar(180)` |  |  | Sim |  |  |
| `cpf` | `varchar(20)` |  |  | Sim |  |  |
| `rg` | `varchar(40)` |  |  | Sim |  |  |
| `titulo_eleitor` | `varchar(20)` |  |  | Sim |  |  |
| `data_nascimento` | `date` |  |  | Sim |  |  |
| `telefone` | `varchar(20)` |  |  | Sim |  |  |
| `email` | `varchar(180)` |  |  | Sim |  |  |
| `endereco` | `text` |  |  | Sim |  |  |
| `municipio` | `varchar(120)` |  |  | Sim |  |  |
| `uf` | `character(2)` |  |  | Sim |  |  |
| `dados_extras` | `jsonb` |  |  | Não | '{}'::jsonb |  |
| `status` | `varchar(20)` |  |  | Não | 'novo'::character varying | Restrição: CHECK (((status)::text = ANY ((ARRAY['novo'::character varying, 'validado'::character varying, 'duplicado'::character varying, 'carregado'::character varying, 'descartado'::character varying])::text[]))) |
| `pessoa_id` | `bigint` |  | pessoa(id) | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

### 2.13. Schema `dw`

**Descrição:** Data Warehouse / analytics: fatos, dimensoes, indicadores e relatorios.

#### Tabela: `dw.dashboard_configuracao`

**Descrição:** Configuracao de paineis, filtros padrao, visoes por perfil e widgets habilitados.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `nome` | `varchar(120)` |  |  | Não |  |  |
| `perfil_acesso_id` | `bigint` |  | perfil_acesso(id) | Sim |  |  |
| `filtros_padrao` | `jsonb` |  |  | Não | '{}'::jsonb |  |
| `widgets` | `jsonb` |  |  | Não | '[]'::jsonb |  |
| `criado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `dw.fato_cadastro`

**Descrição:** Tabela analitica consolidada sobre evolucao de cadastros por periodo, territorio, origem, lider e perfil.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `data_referencia` | `date` |  |  | Não |  |  |
| `territorio_id` | `bigint` |  | territorio(id) | Sim |  |  |
| `lideranca_id` | `bigint` |  | lideranca(id) | Sim |  |  |
| `fonte_dado_id` | `bigint` |  | fonte_dado(id) | Sim |  |  |
| `pessoa_tipo_id` | `smallint` |  | pessoa_tipo(id) | Sim |  |  |
| `total_cadastros` | `integer` |  |  | Não | 0 |  |
| `total_novos` | `integer` |  |  | Não | 0 |  |
| `total_atualizados` | `integer` |  |  | Não | 0 |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `dw.fato_demanda`

**Descrição:** Tabela analitica consolidada sobre demandas por categoria, status, territorio, responsavel e tempo de atendimento.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `data_referencia` | `date` |  |  | Não |  |  |
| `categoria_demanda_id` | `smallint` |  | categoria_demanda(id) | Sim |  |  |
| `status_demanda_id` | `smallint` |  | status_demanda(id) | Sim |  |  |
| `territorio_id` | `bigint` |  | territorio(id) | Sim |  |  |
| `responsavel_atendimento_id` | `bigint` |  | responsavel_atendimento(id) | Sim |  |  |
| `total_demandas` | `integer` |  |  | Não | 0 |  |
| `total_concluidas` | `integer` |  |  | Não | 0 |  |
| `tempo_medio_atendimento_horas` | `numeric(12,2)` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `dw.fato_evento`

**Descrição:** Tabela analitica consolidada sobre eventos, presencas, liderancas envolvidas, demandas geradas e territorios.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `data_referencia` | `date` |  |  | Não |  |  |
| `tipo_evento_id` | `smallint` |  | tipo_evento(id) | Sim |  |  |
| `territorio_id` | `bigint` |  | territorio(id) | Sim |  |  |
| `total_eventos` | `integer` |  |  | Não | 0 |  |
| `total_presentes` | `integer` |  |  | Não | 0 |  |
| `total_demandas_geradas` | `integer` |  |  | Não | 0 |  |
| `presenca_parlamentar` | `integer` |  |  | Não | 0 |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `dw.fato_interacao`

**Descrição:** Tabela analitica consolidada sobre contatos, canais, frequencia, resultado e engajamento.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `data_referencia` | `date` |  |  | Não |  |  |
| `canal_comunicacao_id` | `smallint` |  | canal_comunicacao(id) | Sim |  |  |
| `lideranca_id` | `bigint` |  | lideranca(id) | Sim |  |  |
| `territorio_id` | `bigint` |  | territorio(id) | Sim |  |  |
| `total_interacoes` | `integer` |  |  | Não | 0 |  |
| `total_com_resultado` | `integer` |  |  | Não | 0 |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `dw.fato_meta_voto`

**Descrição:** Tabela analitica consolidada sobre metas, projecoes, confirmacoes, atingimento e risco.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `data_referencia` | `date` |  |  | Não |  |  |
| `meta_voto_id` | `bigint` |  | meta_voto(id) | Sim |  |  |
| `lideranca_id` | `bigint` |  | lideranca(id) | Sim |  |  |
| `territorio_id` | `bigint` |  | territorio(id) | Sim |  |  |
| `quantidade_meta` | `integer` |  |  | Sim |  |  |
| `quantidade_projetada` | `integer` |  |  | Sim |  |  |
| `quantidade_confirmada` | `integer` |  |  | Sim |  |  |
| `percentual_atingido` | `numeric(5,2)` |  |  | Sim |  |  |
| `em_risco` | `boolean` |  |  | Não | false |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `dw.indicador`

**Descrição:** Catalogo de indicadores: total de cadastrados, lideres ativos, demandas pendentes, eventos realizados ou metas em risco.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `smallint` | Sim |  | Não | Auto-increment | Chave primária |
| `codigo` | `varchar(60)` |  |  | Não |  |  |
| `nome` | `varchar(150)` |  |  | Não |  |  |
| `descricao` | `varchar(255)` |  |  | Sim |  |  |
| `unidade` | `varchar(30)` |  |  | Sim |  |  |

#### Tabela: `dw.indicador_valor`

**Descrição:** Valor historico de um indicador por data, tenant, territorio, lider ou outro recorte.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `indicador_id` | `smallint` |  | indicador(id) | Não |  |  |
| `data_referencia` | `date` |  |  | Não |  |  |
| `territorio_id` | `bigint` |  | territorio(id) | Sim |  |  |
| `lideranca_id` | `bigint` |  | lideranca(id) | Sim |  |  |
| `recorte` | `jsonb` |  |  | Não | '{}'::jsonb |  |
| `valor` | `numeric(18,4)` |  |  | Não |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `dw.perfil_eleitorado_secao_tse`

**Descrição:** Base agregada do TSE por secao eleitoral e local de votacao, para analises territoriais e metas.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `ano` | `smallint` |  |  | Não |  |  |
| `estado_id` | `smallint` |  | estado(id) | Sim |  |  |
| `municipio_id` | `integer` |  | municipio(id) | Sim |  |  |
| `zona_eleitoral_id` | `integer` |  | zona_eleitoral(id) | Sim |  |  |
| `secao_eleitoral_id` | `bigint` |  | secao_eleitoral(id) | Sim |  |  |
| `local_votacao_id` | `integer` |  | local_votacao(id) | Sim |  |  |
| `genero` | `varchar(30)` |  |  | Sim |  |  |
| `faixa_etaria` | `varchar(40)` |  |  | Sim |  |  |
| `grau_instrucao` | `varchar(60)` |  |  | Sim |  |  |
| `quantidade_eleitores` | `integer` |  |  | Não | 0 |  |
| `carregado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `dw.perfil_eleitorado_tse`

**Descrição:** Base agregada do TSE com perfil do eleitorado por UF, municipio, zona, genero, faixa etaria, escolaridade, raca/cor e outras dimensoes.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `ano` | `smallint` |  |  | Não |  |  |
| `estado_id` | `smallint` |  | estado(id) | Sim |  |  |
| `municipio_id` | `integer` |  | municipio(id) | Sim |  |  |
| `zona_eleitoral_id` | `integer` |  | zona_eleitoral(id) | Sim |  |  |
| `genero` | `varchar(30)` |  |  | Sim |  |  |
| `faixa_etaria` | `varchar(40)` |  |  | Sim |  |  |
| `grau_instrucao` | `varchar(60)` |  |  | Sim |  |  |
| `estado_civil` | `varchar(40)` |  |  | Sim |  |  |
| `raca_cor` | `varchar(40)` |  |  | Sim |  |  |
| `quantidade_eleitores` | `integer` |  |  | Não | 0 |  |
| `carregado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `dw.relatorio`

**Descrição:** Definicao de relatorios automaticos ou manuais: aniversariantes, metas, demandas, agenda e ranking de lideres.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Sim |  | Isolamento de dados (Multitenant) |
| `codigo` | `varchar(60)` |  |  | Não |  |  |
| `nome` | `varchar(150)` |  |  | Não |  |  |
| `descricao` | `varchar(255)` |  |  | Sim |  |  |
| `tipo` | `varchar(30)` |  |  | Sim |  | Restrição: CHECK (((tipo)::text = ANY ((ARRAY['aniversariantes'::character varying, 'metas'::character varying, 'demandas'::character varying, 'agenda'::character varying, 'ranking'::character varying, 'cadastros'::character varying, 'atendimentos'::character varying, 'personalizado'::character varying])::text[]))) |
| `formato_saida` | `varchar(20)` |  |  | Sim |  | Restrição: CHECK (((formato_saida)::text = ANY ((ARRAY['pdf'::character varying, 'excel'::character varying, 'dashboard'::character varying, 'notificacao'::character varying])::text[]))) |
| `parametros_definicao` | `jsonb` |  |  | Não | '{}'::jsonb |  |
| `automatico` | `boolean` |  |  | Não | false |  |
| `agendamento_cron` | `varchar(60)` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `dw.relatorio_execucao`

**Descrição:** Historico de geracao de relatorios: parametros usados, arquivo gerado e usuario solicitante.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `relatorio_id` | `bigint` |  | relatorio(id) | Não |  |  |
| `parametros` | `jsonb` |  |  | Não | '{}'::jsonb |  |
| `arquivo_id` | `bigint` |  | arquivo(id) | Sim |  |  |
| `status` | `varchar(20)` |  |  | Não | 'gerando'::character varying | Restrição: CHECK (((status)::text = ANY ((ARRAY['gerando'::character varying, 'concluido'::character varying, 'falha'::character varying])::text[]))) |
| `solicitado_por` | `bigint` |  | usuario(id) | Sim |  |  |
| `iniciado_em` | `timestamptz` |  |  | Não | now() |  |
| `concluido_em` | `timestamptz` |  |  | Sim |  |  |

### 2.14. Schema `auditoria`

**Descrição:** Trilha de auditoria de acoes sensiveis e exportacoes (LGPD).

#### Tabela: `auditoria.log_auditoria`

**Descrição:** Trilha de auditoria para criacao, edicao, exclusao, acesso, exportacao e acoes sensiveis (LGPD).

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Sim |  | Isolamento de dados (Multitenant) |
| `usuario_id` | `bigint` |  | usuario(id) | Sim |  |  |
| `acao` | `varchar(20)` |  |  | Não |  | Restrição: CHECK (((acao)::text = ANY ((ARRAY['criar'::character varying, 'editar'::character varying, 'excluir'::character varying, 'acessar'::character varying, 'exportar'::character varying, 'login'::character varying, 'logout'::character varying, 'confirmar'::character varying])::text[]))) |
| `schema_nome` | `varchar(40)` |  |  | Sim |  |  |
| `tabela` | `varchar(80)` |  |  | Sim |  |  |
| `registro_id` | `bigint` |  |  | Sim |  |  |
| `dados_anteriores` | `jsonb` |  |  | Sim |  |  |
| `dados_novos` | `jsonb` |  |  | Sim |  |  |
| `ip_origem` | `inet` |  |  | Sim |  |  |
| `user_agent` | `text` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |

#### Tabela: `auditoria.log_exportacao`

**Descrição:** Registro de exportacoes de dados: usuario, filtros, volume exportado e finalidade.

| Coluna | Tipo | PK | FK | Nulo | Default | Descrição |
|--------|------|:---:|:---:|:---:|---------|-----------|
| `id` | `bigint` | Sim |  | Não | Auto-increment | Chave primária |
| `tenant_id` | `bigint` |  | tenant(id) | Não |  | Isolamento de dados (Multitenant) |
| `usuario_id` | `bigint` |  | usuario(id) | Sim |  |  |
| `entidade` | `varchar(80)` |  |  | Sim |  |  |
| `filtros` | `jsonb` |  |  | Não | '{}'::jsonb |  |
| `volume_registros` | `integer` |  |  | Sim |  |  |
| `formato` | `varchar(20)` |  |  | Sim |  |  |
| `finalidade` | `varchar(255)` |  |  | Sim |  |  |
| `arquivo_id` | `bigint` |  | arquivo(id) | Sim |  |  |
| `ip_origem` | `inet` |  |  | Sim |  |  |
| `criado_em` | `timestamptz` |  |  | Não | now() |  |
