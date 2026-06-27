# Backend Core

API FastAPI em monolito modular. Requer Python 3.11+ e PostgreSQL com a migration
de `../database/migrations` aplicada.

## Desenvolvimento

```powershell
cd backend_core
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Endpoints de infraestrutura:

- `GET /health`: disponibilidade da API, sem acessar dependencias externas.
- `GET /internal/health?check_database=true`: inclui uma consulta `SELECT 1` ao banco.
- `GET /docs`: OpenAPI agrupado por dominio.

Comandos de qualidade:

```powershell
ruff check .
ruff format --check .
mypy src
pytest
```

## Convencao de modulos

Cada dominio possui `router.py`, `schemas.py`, `service.py` e `repository.py`.
Rotas tratam HTTP e validacao; services concentram regras de negocio; repositories
sao a unica camada que executa consultas. O modulo `tenants` e a implementacao de
referencia desse fluxo.
