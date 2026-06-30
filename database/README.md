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
```

Em Linux/macOS:

```bash
export DATABASE_ADMIN_URL='postgresql://postgres:senha@localhost:5432/inteligencia_politica'
psql "$DATABASE_ADMIN_URL" -v ON_ERROR_STOP=1 \
  -f "database/migrations/001 - ddl_inteligencia_politica.sql"
psql "$DATABASE_ADMIN_URL" -v ON_ERROR_STOP=1 \
  -f "database/migrations/002 - tenants_planos_onboarding.sql"
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
