# Vurix Eleitoral

Monolito modular composto por API FastAPI, frontend React e banco PostgreSQL.
Os comandos abaixo devem ser executados a partir desta pasta.

## Requisitos

- Python 3.11 ou superior
- Node.js 20.19 ou superior
- pnpm 11
- PostgreSQL com a migration de `database/migrations` aplicada
- Docker Desktop ou Docker Engine com Compose, para o ambiente conteinerizado

## Backend

Instalacao:

```powershell
cd backend_core
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

O arquivo `backend_core/.env` deve conter a URL do PostgreSQL. Para iniciar e
validar a API:

```powershell
cd backend_core
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod "http://localhost:8000/internal/health?check_database=true"
```

Qualidade:

```powershell
cd backend_core
.\.venv\Scripts\Activate.ps1
ruff check .
ruff format .
mypy src
pytest
```

## Frontend

Instalacao e execucao:

```powershell
cd frontend_core
pnpm install --frozen-lockfile
Copy-Item .env.example .env
pnpm dev
```

Qualidade:

```powershell
cd frontend_core
pnpm lint
pnpm format
pnpm typecheck
pnpm test
pnpm build
pnpm test:e2e
```

## Banco de dados

A API usa `DATABASE_URL` de `backend_core/.env`. O health interno acima executa
`SELECT 1` e retorna HTTP 503 quando o PostgreSQL nao esta acessivel.

A aplicacao e a validacao automatizada estao documentadas em
`database/README.md`. Credenciais reais nao devem ser versionadas.

## Worker

```powershell
cd backend_jobs_celery
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
docker compose up -d redis
celery -A jobs.celery_app worker --loglevel=INFO --pool=solo
```

Em outro terminal:

```powershell
cd backend_jobs_celery
.\.venv\Scripts\Activate.ps1
jobs enqueue-test --wait
jobs enqueue-test --simulate-error --wait
```

## Docker Compose

Para subir API, frontend, worker, Redis e PostgreSQL/PostGIS local:

```powershell
Copy-Item .env.example .env
docker compose --profile local-db up --build
```

Com um PostgreSQL externo, configure `API_DATABASE_URL` e `JOBS_DATABASE_URL` no
`.env` da raiz e execute sem o profile:

```powershell
docker compose up --build
```

Validacoes:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod "http://localhost:8000/internal/health?check_database=true"
docker compose exec worker jobs enqueue-test --wait
```

Encerrar:

```powershell
docker compose --profile local-db down
```

## Integracao continua

O workflow `.github/workflows/ci.yml` roda em pushes para `main` e `develop` e em
pull requests. Ele valida backend, frontend, migration, worker, execucao real de
jobs via Redis e a construcao das imagens Docker. A integracao e bloqueada quando
lint, formatacao, typecheck, testes, validacao do banco ou build falham.
