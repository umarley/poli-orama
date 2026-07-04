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

## Completude cadastral

O Celery Beat enfileira diariamente um job `indicador` por tenant ativo. O horario
padrao e 02:30 (`America/Sao_Paulo`) e pode ser alterado com
`COMPLETENESS_JOB_HOUR` e `COMPLETENESS_JOB_MINUTE`. O processamento usa lotes
configurados por `COMPLETENESS_JOB_BATCH_SIZE` e impede jobs simultaneos do mesmo
indicador e tenant.

O score varia de 0 a 100 e usa os seguintes pesos:

- nome completo: 10;
- data de nascimento: 10;
- sexo, estado civil, escolaridade, profissao e religiao: 5 cada;
- ao menos um documento, contato e endereco: 15 cada;
- ao menos um tipo de pessoa: 5.

Cadastros inativos ou excluidos nao sao recalculados. Cada lote define
`app.current_tenant_id` antes de consultar ou atualizar tabelas protegidas por RLS.

Para executar manualmente:

```powershell
jobs enqueue-completeness --tenant-id 1 --wait
jobs enqueue-completeness --tenant-id 1 --batch-size 500
```

O job registra as quantidades `processadas` e `atualizadas` em
`etl.log_processamento`.

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
docker compose exec worker jobs enqueue-completeness --tenant-id 1 --wait
```
## Alertas de demandas

O beat agenda diariamente `jobs.demandas.enqueue_deadline_alerts`. Para cada tenant
ativo, o worker cria alertas idempotentes para demandas vencendo ou vencidas e resolve
alertas que deixaram de se aplicar. Configure com `DEMAND_DEADLINES_ENABLED`,
`DEMAND_DEADLINES_HOUR` e `DEMAND_DEADLINES_LEAD_DAYS`.
