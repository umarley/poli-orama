# Backend Jobs Celery

Worker para jobs de importacao, deduplicacao, geocodificacao e processamento
pesado. Redis e usado como broker/backend; o estado operacional e persistido em
`etl.job_processamento` e `etl.log_processamento`.

## Instalar

```powershell
cd backend_jobs_celery
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Configure `JOBS_DATABASE_URL` para o mesmo PostgreSQL da API. Inicie Redis e o
worker:

```powershell
docker compose up -d redis
celery -A jobs.celery_app worker --loglevel=INFO --pool=solo
```

Em outro terminal, envie um job e aguarde a conclusao:

```powershell
jobs enqueue-test --wait
jobs enqueue-test --simulate-error --wait
jobs status 1
```

O primeiro job termina como `concluido`. O segundo gera uma falha controlada,
registra log de nivel `error` e termina como `falha`.

## Qualidade

```powershell
ruff check .
ruff format --check .
mypy src
pytest
```

## Docker

```powershell
docker compose --profile local-db up --build
docker compose exec worker jobs enqueue-test --wait
```
