"""Cria dados iniciais idempotentes para desenvolvimento e testes.

O script exige que as migrations do banco tenham sido aplicadas. A senha dos
usuarios e lida de SEED_PASSWORD ou solicitada de forma interativa, sem ser
recebida como argumento de linha de comando.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import asyncpg
from argon2 import PasswordHasher


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = PROJECT_ROOT / "backend_core" / ".env"
PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)

PROFILE_NAMES = {
    "gestor_saas": "Gestor SaaS",
    "gestor": "Gestor",
    "coordenador_territorial": "Coordenador territorial",
    "lider": "Lider",
    "telefonista": "Telefonista/Atendimento",
    "administrativo": "Administrativo/RH",
}


@dataclass(frozen=True)
class TenantSeed:
    name: str
    slug: str
    document: str
    primary_color: str


TENANTS = (
    TenantSeed("Campanha Aurora", "campanha-aurora", "10000000000101", "#1D4ED8"),
    TenantSeed("Campanha Horizonte", "campanha-horizonte", "10000000000292", "#047857"),
    TenantSeed("Campanha Renovacao", "campanha-renovacao", "10000000000373", "#B45309"),
)


def read_env_file(path: Path) -> dict[str, str]:
    """Le um arquivo dotenv simples sem sobrescrever o ambiente do processo."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key.strip()] = value
    return values


def normalize_database_url(url: str) -> str:
    """Converte URLs SQLAlchemy/asyncpg para o formato aceito pelo asyncpg."""
    normalized = url.strip()
    if normalized.startswith("postgresql+asyncpg://"):
        normalized = "postgresql://" + normalized.removeprefix("postgresql+asyncpg://")
    elif normalized.startswith("postgres+asyncpg://"):
        normalized = "postgresql://" + normalized.removeprefix("postgres+asyncpg://")
    return normalized


def validate_database_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname or not parsed.path:
        raise ValueError("A URL deve apontar para um banco PostgreSQL valido.")


def validate_password(password: str) -> None:
    requirements = (
        (len(password) >= 8, "ter ao menos 8 caracteres"),
        (len(password) <= 128, "ter no maximo 128 caracteres"),
        (bool(re.search(r"[a-z]", password)), "conter letra minuscula"),
        (bool(re.search(r"[A-Z]", password)), "conter letra maiuscula"),
        (bool(re.search(r"\d", password)), "conter numero"),
        (bool(re.search(r"[^A-Za-z0-9]", password)), "conter caractere especial"),
    )
    failures = [message for valid, message in requirements if not valid]
    if failures:
        raise ValueError("A senha deve " + ", ".join(failures) + ".")


def resolve_password() -> str:
    password = os.getenv("SEED_PASSWORD")
    if password is not None:
        validate_password(password)
        return password
    if not sys.stdin.isatty():
        raise ValueError("Defina SEED_PASSWORD para executar o seed sem terminal interativo.")
    password = getpass.getpass("Senha compartilhada dos usuarios de seed: ")
    confirmation = getpass.getpass("Confirme a senha: ")
    if password != confirmation:
        raise ValueError("As senhas nao conferem.")
    validate_password(password)
    return password


async def require_schema(connection: asyncpg.Connection) -> dict[str, int]:
    required_tables = (
        "public.plano_assinatura",
        "public.tenant",
        "public.tenant_configuracao",
        "auth.usuario",
        "auth.perfil_acesso",
        "auth.usuario_perfil",
    )
    missing = [
        table
        for table in required_tables
        if await connection.fetchval("SELECT to_regclass($1)", table) is None
    ]
    if missing:
        raise RuntimeError(
            "Migrations pendentes; tabelas ausentes: " + ", ".join(sorted(missing))
        )

    rows = await connection.fetch(
        """
        SELECT id, codigo
        FROM auth.perfil_acesso
        WHERE tenant_id IS NULL AND codigo = ANY($1::text[])
        """,
        list(PROFILE_NAMES),
    )
    profiles = {str(row["codigo"]): int(row["id"]) for row in rows}
    missing_profiles = sorted(set(PROFILE_NAMES) - set(profiles))
    if missing_profiles:
        raise RuntimeError(
            "A migration 003 deve criar os perfis: " + ", ".join(missing_profiles)
        )
    return profiles


async def upsert_plan(connection: asyncpg.Connection) -> int:
    return int(
        await connection.fetchval(
            """
            INSERT INTO public.plano_assinatura (
                slug, nome, descricao, preco_mensal, moeda, limite_usuarios,
                limite_pessoas, limite_armazenamento_mb, recursos,
                ordem_comercial, ativo
            )
            VALUES (
                'desenvolvimento', 'Desenvolvimento',
                'Plano local para desenvolvimento e testes.', 0, 'BRL',
                100, 100000, 10240,
                '{"todos_recursos": true, "ambiente_seed": true}'::jsonb,
                999, TRUE
            )
            ON CONFLICT (slug) DO UPDATE SET
                nome = EXCLUDED.nome,
                descricao = EXCLUDED.descricao,
                limite_usuarios = EXCLUDED.limite_usuarios,
                limite_pessoas = EXCLUDED.limite_pessoas,
                limite_armazenamento_mb = EXCLUDED.limite_armazenamento_mb,
                recursos = EXCLUDED.recursos,
                ativo = TRUE,
                atualizado_em = now()
            RETURNING id
            """
        )
    )


async def upsert_tenant(
    connection: asyncpg.Connection, tenant: TenantSeed, plan_id: int
) -> int:
    tenant_id = int(
        await connection.fetchval(
            """
            INSERT INTO public.tenant (
                nome, slug, documento, tem_mandato, plano_assinatura_id,
                data_inicio_contrato, status
            )
            VALUES ($1, $2, $3, FALSE, $4, CURRENT_DATE, 'ativo')
            ON CONFLICT (slug) DO UPDATE SET
                nome = EXCLUDED.nome,
                documento = EXCLUDED.documento,
                plano_assinatura_id = EXCLUDED.plano_assinatura_id,
                status = 'ativo',
                excluido_em = NULL,
                atualizado_em = now()
            RETURNING id
            """,
            tenant.name,
            tenant.slug,
            tenant.document,
            plan_id,
        )
    )
    await connection.execute(
        """
        INSERT INTO public.tenant_configuracao (
            tenant_id, nome_publico, cor_primaria, fuso_horario,
            percentual_alerta_meta, integracoes, preferencias
        )
        VALUES (
            $1, $2, $3, 'America/Sao_Paulo', 70,
            '{}'::jsonb,
            '{"ambiente": "desenvolvimento", "dados_seed": true}'::jsonb
        )
        ON CONFLICT (tenant_id) DO UPDATE SET
            nome_publico = EXCLUDED.nome_publico,
            cor_primaria = EXCLUDED.cor_primaria,
            fuso_horario = EXCLUDED.fuso_horario,
            preferencias = EXCLUDED.preferencias,
            atualizado_em = now()
        """,
        tenant_id,
        tenant.name,
        tenant.primary_color,
    )
    return tenant_id


async def upsert_user(
    connection: asyncpg.Connection,
    *,
    tenant_id: int,
    tenant_name: str,
    profile_code: str,
    profile_id: int,
    password_hash: str,
) -> tuple[int, str]:
    email = f"{profile_code}@seed.vurix.local"
    user_id = int(
        await connection.fetchval(
            """
            INSERT INTO auth.usuario (
                tenant_id, nome, email, hash_senha, mfa_habilitado, status,
                tentativas_login, senha_alterada_em, deve_alterar_senha
            )
            VALUES ($1, $2, $3, $4, FALSE, 'ativo', 0, now(), FALSE)
            ON CONFLICT (tenant_id, email) DO UPDATE SET
                nome = EXCLUDED.nome,
                hash_senha = EXCLUDED.hash_senha,
                status = 'ativo',
                tentativas_login = 0,
                deve_alterar_senha = FALSE,
                excluido_em = NULL,
                atualizado_em = now()
            RETURNING id
            """,
            tenant_id,
            f"{PROFILE_NAMES[profile_code]} - {tenant_name}",
            email,
            password_hash,
        )
    )
    await connection.execute(
        "DELETE FROM auth.usuario_perfil WHERE usuario_id = $1",
        user_id,
    )
    await connection.execute(
        """
        INSERT INTO auth.usuario_perfil (usuario_id, perfil_acesso_id, tenant_id)
        VALUES ($1, $2, $3)
        ON CONFLICT DO NOTHING
        """,
        user_id,
        profile_id,
        tenant_id,
    )
    return user_id, email


async def seed(database_url: str, password: str) -> list[tuple[str, str, str, int]]:
    connection = await asyncpg.connect(database_url)
    credentials: list[tuple[str, str, str, int]] = []
    try:
        async with connection.transaction():
            profiles = await require_schema(connection)
            plan_id = await upsert_plan(connection)
            password_hash = PASSWORD_HASHER.hash(password)
            for tenant in TENANTS:
                tenant_id = await upsert_tenant(connection, tenant, plan_id)
                await connection.execute(
                    "SELECT set_config('app.current_tenant_id', $1, true)",
                    str(tenant_id),
                )
                for profile_code, profile_id in profiles.items():
                    user_id, email = await upsert_user(
                        connection,
                        tenant_id=tenant_id,
                        tenant_name=tenant.name,
                        profile_code=profile_code,
                        profile_id=profile_id,
                        password_hash=password_hash,
                    )
                    credentials.append((tenant.slug, profile_code, email, user_id))
    finally:
        await connection.close()
    return credentials


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cria tenants e usuarios iniciais idempotentes para desenvolvimento/testes."
    )
    parser.add_argument(
        "--database-url",
        help="URL PostgreSQL. Padrao: DATABASE_URL ou o arquivo informado em --env-file.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_ENV_FILE,
        help=f"Arquivo dotenv usado como fallback (padrao: {DEFAULT_ENV_FILE}).",
    )
    parser.add_argument(
        "--environment",
        choices=("local", "test"),
        help="Ambiente alvo. Padrao: ENVIRONMENT do processo/.env ou local.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env_file = read_env_file(args.env_file)
    environment = (
        args.environment
        or os.getenv("ENVIRONMENT")
        or env_file.get("ENVIRONMENT")
        or "local"
    ).lower()
    if environment not in {"local", "test"}:
        print(
            "Erro: o seed so pode ser executado com ENVIRONMENT=local ou test.",
            file=sys.stderr,
        )
        return 2
    database_url = args.database_url or os.getenv("DATABASE_URL") or env_file.get("DATABASE_URL")
    if not database_url:
        print(
            "Erro: informe --database-url, DATABASE_URL ou um arquivo .env com DATABASE_URL.",
            file=sys.stderr,
        )
        return 2
    try:
        database_url = normalize_database_url(database_url)
        validate_database_url(database_url)
        password = resolve_password()
        credentials = asyncio.run(seed(database_url, password))
    except (ValueError, RuntimeError, asyncpg.PostgresError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    print(f"Seed concluido: {len(TENANTS)} tenants e {len(credentials)} usuarios.")
    print("Use a senha fornecida em SEED_PASSWORD ou no prompt.")
    print()
    print(f"{'TENANT':<22} {'PERFIL':<26} {'EMAIL':<38} ID")
    for tenant_slug, profile_code, email, user_id in credentials:
        print(f"{tenant_slug:<22} {profile_code:<26} {email:<38} {user_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
