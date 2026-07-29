# Banco de dados

O schema requer PostgreSQL 14+ (recomendado 16+) com PostGIS. A migration cria
extensoes, schemas, tabelas, funcoes, triggers, politicas RLS e a role
`app_inteligencia`; por isso deve ser aplicada com uma conta administradora.

## Aplicar localmente

Defina uma URL administrativa apenas na sessao do terminal. Nao versione
credenciais:

```powershell
$env:DATABASE_ADMIN_URL = "postgresql://postgres:senha@localhost:5432/inteligencia_politica"
psql $env:DATABASE_ADMIN_URL -v ON_ERROR_STOP=1 -f ".\database\migrations\001 - ddl_inteligencia_politica.sql"
psql $env:DATABASE_ADMIN_URL -v ON_ERROR_STOP=1 -f ".\database\migrations\002 - tenants_planos_onboarding.sql"
psql $env:DATABASE_ADMIN_URL -v ON_ERROR_STOP=1 -f ".\database\migrations\003 - auth_rbac_auditoria_p0.sql"
psql $env:DATABASE_ADMIN_URL -v ON_ERROR_STOP=1 -f ".\database\migrations\004 - auth_p1_acesso_territorial.sql"
psql $env:DATABASE_ADMIN_URL -v ON_ERROR_STOP=1 -f ".\database\migrations\005 - auth_p2_mfa_sessoes.sql"
psql $env:DATABASE_ADMIN_URL -v ON_ERROR_STOP=1 -f ".\database\migrations\006 - cadastro_pessoas_constraints.sql"
psql $env:DATABASE_ADMIN_URL -v ON_ERROR_STOP=1 -f ".\database\migrations\007 - cadastro_merge_assistido.sql"
psql $env:DATABASE_ADMIN_URL -v ON_ERROR_STOP=1 -f ".\database\migrations\008 - territorios_georreferenciamento.sql"
psql $env:DATABASE_ADMIN_URL -v ON_ERROR_STOP=1 -f ".\database\migrations\009 - metas_votos_rankings_alertas.sql"
psql $env:DATABASE_ADMIN_URL -v ON_ERROR_STOP=1 -f ".\database\migrations\010 - importacao_etl_qualidade_dados.sql"
psql $env:DATABASE_ADMIN_URL -v ON_ERROR_STOP=1 -f ".\database\migrations\011 - agenda_eventos.sql"
psql $env:DATABASE_ADMIN_URL -v ON_ERROR_STOP=1 -f ".\database\migrations\012 - demandas_atendimentos.sql"
psql $env:DATABASE_ADMIN_URL -v ON_ERROR_STOP=1 -f ".\database\migrations\016 - demandas_indices_alertas.sql"
```

Em Linux/macOS:

```bash
export DATABASE_ADMIN_URL='postgresql://postgres:senha@localhost:5432/inteligencia_politica'
psql "$DATABASE_ADMIN_URL" -v ON_ERROR_STOP=1 \
  -f "database/migrations/001 - ddl_inteligencia_politica.sql"
psql "$DATABASE_ADMIN_URL" -v ON_ERROR_STOP=1 \
  -f "database/migrations/002 - tenants_planos_onboarding.sql"
psql "$DATABASE_ADMIN_URL" -v ON_ERROR_STOP=1 \
  -f "database/migrations/003 - auth_rbac_auditoria_p0.sql"
psql "$DATABASE_ADMIN_URL" -v ON_ERROR_STOP=1 \
  -f "database/migrations/004 - auth_p1_acesso_territorial.sql"
psql "$DATABASE_ADMIN_URL" -v ON_ERROR_STOP=1 \
  -f "database/migrations/005 - auth_p2_mfa_sessoes.sql"
psql "$DATABASE_ADMIN_URL" -v ON_ERROR_STOP=1 \
  -f "database/migrations/006 - cadastro_pessoas_constraints.sql"
psql "$DATABASE_ADMIN_URL" -v ON_ERROR_STOP=1 \
  -f "database/migrations/007 - cadastro_merge_assistido.sql"
psql "$DATABASE_ADMIN_URL" -v ON_ERROR_STOP=1 \
  -f "database/migrations/008 - territorios_georreferenciamento.sql"
psql "$DATABASE_ADMIN_URL" -v ON_ERROR_STOP=1 \
  -f "database/migrations/009 - metas_votos_rankings_alertas.sql"
psql "$DATABASE_ADMIN_URL" -v ON_ERROR_STOP=1 \
  -f "database/migrations/010 - importacao_etl_qualidade_dados.sql"
psql "$DATABASE_ADMIN_URL" -v ON_ERROR_STOP=1 \
  -f "database/migrations/011 - agenda_eventos.sql"
psql "$DATABASE_ADMIN_URL" -v ON_ERROR_STOP=1 \
  -f "database/migrations/012 - demandas_atendimentos.sql"
psql "$DATABASE_ADMIN_URL" -v ON_ERROR_STOP=1 \
  -f "database/migrations/016 - demandas_indices_alertas.sql"
```

A migration deve ser aplicada uma unica vez em um banco vazio. O uso de
`ON_ERROR_STOP=1` impede que o processo continue depois de uma instrucao
invalida. Depois da instalacao, altere a senha inicial da role:

```sql
ALTER ROLE app_inteligencia PASSWORD 'uma-senha-forte-e-exclusiva';
```

Configure `backend_core/.env` com uma URL SQLAlchemy/asyncpg:

```dotenv
DATABASE_URL=postgresql+asyncpg://app_inteligencia:senha@localhost:5432/inteligencia_politica
```

O worker aceita uma URL PostgreSQL comum:

```dotenv
JOBS_DATABASE_URL=postgresql://app_inteligencia:senha@localhost:5432/inteligencia_politica
```

## Validar schema e tabelas

O validador extrai a estrutura esperada diretamente da migration e compara com
os catalogos do PostgreSQL:

```powershell
cd backend_core
.\.venv\Scripts\Activate.ps1
cd ..
python database/scripts/validate_schema.py --env-file backend_core/.env
```

Tambem e possivel usar `DATABASE_URL` ou `--database-url`. O comando lista cada
schema e tabela esperada, retorna codigo zero quando tudo existe e codigo um
quando encontra ausencias.

## Docker

O profile `local-db` do Compose inicializa automaticamente um PostgreSQL 16 com
PostGIS e aplica a migration quando o volume ainda esta vazio:

```powershell
docker compose --profile local-db up postgres
docker compose --profile local-db down
```

Para reaplicar do zero em ambiente estritamente local:

```powershell
docker compose --profile local-db down --volumes
docker compose --profile local-db up postgres
```

O segundo comando remove dados do volume local; nao deve ser usado em ambientes
compartilhados ou de producao.

## Dados iniciais para desenvolvimento e testes

Depois de aplicar todas as migrations, instale as dependencias e execute o seed:

```powershell
python -m pip install -r database/requirements.txt
$env:SEED_PASSWORD = Read-Host "Senha dos usuarios de seed" -MaskInput
python database/seeds/seed_development.py --env-file backend_core/.env
Remove-Item Env:SEED_PASSWORD
```

Sem `SEED_PASSWORD`, o script solicita e confirma a senha de forma oculta. Ele
cria ou atualiza tres tenants, suas configuracoes, um plano de desenvolvimento e
um usuario para cada perfil global em cada tenant. O comando e idempotente e
imprime os slugs, perfis e e-mails que podem ser usados no login.

Use `--database-url` para informar a conexao diretamente. URLs no formato
`postgresql+asyncpg://` tambem sao aceitas. O script somente permite os ambientes
`local` e `test`.

### Massa completa para demonstração

Com os tenants 17, 18 e 19 já existentes e os catálogos globais/eleitorais
importados, valide a massa completa sem persistir alterações:

```powershell
python database/seeds/seed_application_demo.py --env-file backend_core/.env --dry-run
```

Depois do dry-run bem-sucedido, grave os dados:

```powershell
python database/seeds/seed_application_demo.py --env-file backend_core/.env
```

O script usa `lote-1.json` no tenant 17, `lote-2.json` no tenant 18 e os lotes
3, 4 e 5 no tenant 19. Ele cria pessoas, documentos, contatos, endereços e
coordenadas, dados eleitorais, segmentações, territórios, hierarquia de líderes,
equipes, comunidades, núcleos familiares, indicações, interações, metas,
eventos e demandas. A execução é idempotente: somente a massa marcada com
`[SEED DEMO]` é substituída. Para validar apenas o tenant em uso:

```powershell
python database/seeds/seed_application_demo.py --env-file backend_core/.env --tenants 19 --dry-run
```
