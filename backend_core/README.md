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

Autenticacao e usuarios:

- `POST /api/v1/auth/login`: recebe `tenant_slug`, `email` e `senha`.
- `POST /api/v1/auth/logout`: revoga a sessao do Bearer token.
- `POST /api/v1/auth/refresh`: rotaciona access e refresh tokens.
- `GET /api/v1/auth/me`: retorna usuario, tenant, perfis e permissoes.
- `/api/v1/auth/mfa/*`: configura, confirma ou desabilita TOTP para gestores.
- `/api/v1/auth/sessions`: lista e revoga sessoes/dispositivos do usuario.
- `/api/v1/users`: CRUD administrativo, perfis e reset de senha.
- `/api/v1/users/{id}/territorial-access`: consulta e substitui escopos territoriais.

O JWT contem `tenant_id`, usuario, perfis, permissoes e o identificador da sessao.
Refresh tokens sao rotacionados e o token anterior deixa de ser aceito imediatamente.
Cada sessao possui expiracao absoluta e expira tambem por inatividade conforme
`SESSION_IDLE_MINUTES`. Segredos TOTP sao criptografados com `MFA_ENCRYPTION_KEY`.
O backend valida a sessao no banco e aplica `app.current_tenant_id` antes de
entregar a conexao aos endpoints privados. A API deve conectar como
`app_inteligencia`, nunca como superusuario, para que o RLS seja efetivo.

### Politica de senha

Senhas de usuarios, inclusive senhas temporarias emitidas no reset administrativo,
devem:

- ter entre `PASSWORD_MIN_LENGTH` (8 por padrao) e 128 caracteres;
- conter ao menos uma letra minuscula e uma letra maiuscula;
- conter ao menos um algarismo;
- conter ao menos um caractere especial (nao alfanumerico).

A API aplica a mesma politica na criacao de usuario, no reset administrativo e na
troca de senha. Senhas sao armazenadas exclusivamente como hash Argon2id; a senha
temporaria em texto claro e retornada uma unica vez ao gestor e exige troca no
proximo acesso. Nunca registre senhas em logs, arquivos ou historico do terminal.

Depois de criar o primeiro tenant por onboarding, crie o gestor inicial sem
gravar senha em arquivo ou no historico do terminal:

```powershell
python -m app.auth.bootstrap --tenant-slug campanha-exemplo `
  --name "Gestor inicial" --email gestor@example.com --profile gestor_saas
```

O comando solicita e confirma a senha de forma oculta.

Cadastro:

- `GET/POST /api/v1/cadastro/pessoas`: listagem filtrada e cadastro completo.
- `GET/PATCH/DELETE /api/v1/cadastro/pessoas/{id}`: detalhe, edicao e inativacao.
- `/api/v1/cadastro/pessoas/{id}/*`: documentos, contatos, enderecos, eleitor,
  lideranca, tipos, indicacoes, relacionamentos e complemento politico.
- `/api/v1/cadastro/hierarquia`: consulta e manutencao da hierarquia.
- `/api/v1/cadastro/nucleos-familiares`, `/comunidades` e `/tags`: segmentacao.
- `/api/v1/cadastro/validacoes` e `/duplicidades`: filas de qualidade cadastral.
- `GET /api/v1/cadastro/duplicidades/{id}/merge-preview`: comparacao assistida.
- `POST /api/v1/cadastro/duplicidades/{id}/merge`: merge auditavel para gestores.
- `GET /api/v1/cadastro/pessoas/busca-rapida`: busca por nome, documento ou telefone.

Comandos de qualidade:

```powershell
ruff check .
ruff format --check .
mypy src
pytest
```

Testes de integracao usam `TEST_DATABASE_URL`. A API e as conexoes de preparacao
dos testes apontam automaticamente para essa mesma URL:

```powershell
$env:TEST_DATABASE_URL = "postgresql+asyncpg://usuario:senha@localhost:5432/vurix_test"
pytest tests/test_cadastro_integration.py
```

O banco de teste deve receber todas as migrations, inclusive `005`, `006` e `007`,
antes da execucao. A aplicacao das migrations exige uma conta com permissao de
alteracao de schema; a role restrita da API nao deve ser usada para isso.

## Convencao de modulos

Cada dominio possui `router.py`, `schemas.py`, `service.py` e `repository.py`.
Rotas tratam HTTP e validacao; services concentram regras de negocio; repositories
sao a unica camada que executa consultas. O modulo `tenants` e a implementacao de
referencia desse fluxo.
