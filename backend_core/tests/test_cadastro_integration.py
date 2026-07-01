import os
from dataclasses import dataclass
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.auth.security import hash_password
from app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
PASSWORD = "Senha-cadastro-123!"

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL nao configurada para testes de integracao do cadastro.",
)


@dataclass(frozen=True)
class TenantContext:
    id: int
    slug: str
    email: str


async def _create_tenant(engine: AsyncEngine, suffix: str, label: str) -> TenantContext:
    slug = f"cadastro-{label}-{suffix}"
    email = f"cadastro-{label}-{suffix}@example.test"
    async with engine.begin() as connection:
        tenant_id = int(
            await connection.scalar(
                text("INSERT INTO public.tenant (nome, slug) VALUES (:name, :slug) RETURNING id"),
                {"name": f"Cadastro {label}", "slug": slug},
            )
        )
        await connection.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )
        user_id = int(
            await connection.scalar(
                text(
                    "INSERT INTO auth.usuario "
                    "(tenant_id, nome, email, hash_senha) "
                    "VALUES (:tenant_id, :name, :email, :password) RETURNING id"
                ),
                {
                    "tenant_id": tenant_id,
                    "name": f"Gestor {label}",
                    "email": email,
                    "password": hash_password(PASSWORD),
                },
            )
        )
        await connection.execute(
            text(
                "INSERT INTO auth.usuario_perfil "
                "(usuario_id, perfil_acesso_id, tenant_id) "
                "SELECT :user_id, id, :tenant_id FROM auth.perfil_acesso "
                "WHERE tenant_id IS NULL AND codigo = 'gestor'"
            ),
            {"user_id": user_id, "tenant_id": tenant_id},
        )
    return TenantContext(id=tenant_id, slug=slug, email=email)


def _login(client: TestClient, context: TenantContext) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "tenant_slug": context.slug,
            "email": context.email,
            "senha": PASSWORD,
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _cleanup(engine: AsyncEngine, tenant_ids: list[int]) -> None:
    if tenant_ids:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM public.tenant WHERE id = ANY(:tenant_ids)"),
                {"tenant_ids": tenant_ids},
            )


async def _assert_required_schema(engine: AsyncEngine) -> None:
    required = {
        ("auth", "sessao_usuario", "ultimo_uso_em"): "005 - auth_p2_mfa_sessoes.sql",
        ("cadastro", "pessoa_nucleo_familiar", "observacao"): (
            "006 - cadastro_pessoas_constraints.sql"
        ),
        ("cadastro", "comunidade", "territorio_id"): ("006 - cadastro_pessoas_constraints.sql"),
        ("cadastro", "tag", "ativo"): "006 - cadastro_pessoas_constraints.sql",
        ("cadastro", "pessoa_merge", "id"): "007 - cadastro_merge_assistido.sql",
    }
    async with engine.connect() as connection:
        rows = await connection.execute(
            text(
                "SELECT table_schema, table_name, column_name "
                "FROM information_schema.columns "
                "WHERE (table_schema, table_name, column_name) IN "
                "(('auth','sessao_usuario','ultimo_uso_em'), "
                " ('cadastro','pessoa_nucleo_familiar','observacao'), "
                " ('cadastro','comunidade','territorio_id'), "
                " ('cadastro','tag','ativo'), "
                " ('cadastro','pessoa_merge','id'))"
            )
        )
        existing = {(str(schema), str(table), str(column)) for schema, table, column in rows}
    missing = sorted(set(required) - existing)
    if missing:
        migrations = sorted({required[item] for item in missing})
        missing_names = ", ".join(".".join(item) for item in missing)
        pytest.fail(
            "Banco de integracao desatualizado. "
            f"Colunas ausentes: {missing_names}. "
            f"Aplique as migrations: {', '.join(migrations)}.",
            pytrace=False,
        )


def _person_payload(
    name: str,
    *,
    cpf: str | None = None,
    title: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    birth_date: str = "1985-04-12",
) -> dict[str, object]:
    documents: list[dict[str, object]] = []
    if cpf:
        documents.append({"tipo_documento": "cpf", "numero": cpf})
    contacts: list[dict[str, object]] = []
    if phone:
        contacts.append(
            {
                "tipo_contato": "whatsapp",
                "valor": phone,
                "principal": True,
            }
        )
    if email:
        contacts.append(
            {
                "tipo_contato": "email",
                "valor": email,
                "principal": True,
            }
        )
    payload: dict[str, object] = {
        "nome_completo": name,
        "data_nascimento": birth_date,
        "documentos": documents,
        "contatos": contacts,
        "enderecos": [],
        "redes_sociais": [],
        "tipo_ids": [],
    }
    if title:
        payload["eleitor"] = {
            "titulo_eleitor": title,
            "situacao_titulo": "regular",
        }
    return payload


@pytest.mark.asyncio
async def test_cad_047_creates_complete_person_registration() -> None:
    """CAD-047: pessoa completa com documento, contato, endereco, tipo e eleitor."""
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL)
    tenant_ids: list[int] = []
    suffix = uuid4().hex[:10]
    try:
        await _assert_required_schema(engine)
        context = await _create_tenant(engine, suffix, "completo")
        tenant_ids.append(context.id)
        async with engine.connect() as connection:
            person_type_id = int(
                await connection.scalar(
                    text("SELECT id FROM cadastro.pessoa_tipo WHERE codigo = 'eleitor'")
                )
            )

        with TestClient(app) as client:
            headers = _login(client, context)
            response = client.post(
                "/api/v1/cadastro/pessoas",
                headers=headers,
                json={
                    "nome_completo": "Maria Cadastro Completo",
                    "sexo": "F",
                    "data_nascimento": "1985-04-12",
                    "documentos": [
                        {
                            "tipo_documento": "cpf",
                            "numero": "52998224725",
                            "orgao_emissor": "RFB",
                        }
                    ],
                    "contatos": [
                        {
                            "tipo_contato": "whatsapp",
                            "valor": "11999990001",
                            "principal": True,
                        },
                        {
                            "tipo_contato": "email",
                            "valor": f"maria-{suffix}@example.test",
                            "principal": True,
                        },
                    ],
                    "enderecos": [
                        {
                            "tipo": "residencial",
                            "principal": True,
                            "endereco": {
                                "cep": "01001-000",
                                "logradouro": "Praca da Se",
                                "numero": "100",
                                "bairro_texto": "Se",
                            },
                        }
                    ],
                    "redes_sociais": [
                        {
                            "rede": "instagram",
                            "usuario_perfil": f"maria_{suffix}",
                        }
                    ],
                    "tipo_ids": [person_type_id],
                    "eleitor": {
                        "titulo_eleitor": "123456789012",
                        "situacao_titulo": "regular",
                    },
                    "lideranca": {
                        "tipo_lideranca": "coordenador_geral",
                        "meta_votos": 100,
                        "ativo": True,
                    },
                },
            )
            assert response.status_code == 201, response.text
            person = response.json()
            assert person["tenant_id"] == context.id
            assert person["documentos"][0]["numero"] == "52998224725"
            assert {item["tipo_contato"] for item in person["contatos"]} == {
                "whatsapp",
                "email",
            }
            assert person["enderecos"][0]["endereco"]["bairro_texto"] == "Se"
            assert person["tipos"][0]["codigo"] == "eleitor"
            assert person["eleitor"]["titulo_eleitor"] == "123456789012"
            assert person["lideranca"]["meta_votos"] == 100

            detail = client.get(f"/api/v1/cadastro/pessoas/{person['id']}", headers=headers)
            assert detail.status_code == 200, detail.text
            assert detail.json()["redes_sociais"][0]["rede"] == "instagram"

        async with engine.connect() as connection:
            audit_count = int(
                (
                    await connection.scalar(
                        text(
                            "SELECT count(*) FROM auditoria.log_auditoria "
                            "WHERE tenant_id = :tenant_id "
                            "AND tabela = 'pessoa' AND acao = 'criar'"
                        ),
                        {"tenant_id": context.id},
                    )
                )
                or 0
            )
            assert audit_count == 1
    finally:
        await _cleanup(engine, tenant_ids)
        await engine.dispose()


@pytest.mark.asyncio
async def test_cad_048_blocks_strong_and_flags_soft_duplicates() -> None:
    """CAD-048: CPF/titulo bloqueiam; telefone/e-mail/nome-data geram suspeita."""
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL)
    tenant_ids: list[int] = []
    suffix = uuid4().hex[:10]
    try:
        await _assert_required_schema(engine)
        context = await _create_tenant(engine, suffix, "duplicidade")
        tenant_ids.append(context.id)
        phone = "11999990002"
        email = f"duplicidade-{suffix}@example.test"
        title = "223456789012"
        with TestClient(app) as client:
            headers = _login(client, context)
            first = client.post(
                "/api/v1/cadastro/pessoas",
                headers=headers,
                json=_person_payload(
                    "Pessoa Duplicada",
                    cpf="52998224725",
                    title=title,
                    phone=phone,
                    email=email,
                ),
            )
            assert first.status_code == 201, first.text

            duplicate_cpf = client.post(
                "/api/v1/cadastro/pessoas",
                headers=headers,
                json=_person_payload(
                    "Outro Nome",
                    cpf="52998224725",
                ),
            )
            assert duplicate_cpf.status_code == 422
            assert duplicate_cpf.json()["code"] == "strong_duplicate"
            assert duplicate_cpf.json()["details"]["criterio"] == "cpf"

            duplicate_title = client.post(
                "/api/v1/cadastro/pessoas",
                headers=headers,
                json=_person_payload(
                    "Outro Titulo",
                    title=title,
                ),
            )
            assert duplicate_title.status_code == 422
            assert duplicate_title.json()["details"]["criterio"] == "titulo_eleitor"

            soft_duplicate = client.post(
                "/api/v1/cadastro/pessoas",
                headers=headers,
                json=_person_payload(
                    "Pessoa Duplicada",
                    phone=phone,
                    email=email,
                ),
            )
            assert soft_duplicate.status_code == 201, soft_duplicate.text

            suspicions = client.get(
                "/api/v1/cadastro/duplicidades",
                headers=headers,
                params={"status": "pendente"},
            )
            assert suspicions.status_code == 200, suspicions.text
            criteria = {item["criterio"] for item in suspicions.json()}
            assert {"telefone", "email", "nome_data_nascimento"} <= criteria
            assert all(item["tenant_id"] == context.id for item in suspicions.json())
    finally:
        await _cleanup(engine, tenant_ids)
        await engine.dispose()


@pytest.mark.asyncio
async def test_cad_049_rejects_cycles_and_respects_tenant() -> None:
    """CAD-049: hierarquia rejeita ciclo e nao aceita pessoas de outro tenant."""
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL)
    tenant_ids: list[int] = []
    suffix = uuid4().hex[:10]
    try:
        await _assert_required_schema(engine)
        tenant_a = await _create_tenant(engine, suffix, "hierarquia-a")
        tenant_b = await _create_tenant(engine, suffix, "hierarquia-b")
        tenant_ids.extend([tenant_a.id, tenant_b.id])
        with TestClient(app) as client:
            headers_a = _login(client, tenant_a)
            headers_b = _login(client, tenant_b)

            coordinator = client.post(
                "/api/v1/cadastro/pessoas",
                headers=headers_a,
                json={
                    **_person_payload(
                        "Coordenador A",
                        cpf="52998224725",
                    ),
                    "lideranca": {
                        "tipo_lideranca": "coordenador_geral",
                        "ativo": True,
                    },
                },
            )
            assert coordinator.status_code == 201, coordinator.text
            coordinator_body = coordinator.json()

            leader = client.post(
                "/api/v1/cadastro/pessoas",
                headers=headers_a,
                json={
                    **_person_payload("Lider B"),
                    "lideranca": {
                        "tipo_lideranca": "lider",
                        "coordenador_id": coordinator_body["lideranca"]["id"],
                        "ativo": True,
                    },
                    "lideranca_superior_id": coordinator_body["lideranca"]["id"],
                    "papel_subordinado": "lider",
                },
            )
            assert leader.status_code == 201, leader.text
            leader_body = leader.json()

            subleader = client.post(
                "/api/v1/cadastro/pessoas",
                headers=headers_a,
                json={
                    **_person_payload("Sublider C"),
                    "lideranca": {
                        "tipo_lideranca": "sublider",
                        "coordenador_id": leader_body["lideranca"]["id"],
                        "ativo": True,
                    },
                    "lideranca_superior_id": leader_body["lideranca"]["id"],
                    "papel_subordinado": "lider",
                },
            )
            assert subleader.status_code == 201, subleader.text
            subleader_body = subleader.json()

            cycle = client.post(
                "/api/v1/cadastro/hierarquia",
                headers=headers_a,
                json={
                    "lideranca_superior_id": subleader_body["lideranca"]["id"],
                    "pessoa_subordinada_id": coordinator_body["id"],
                    "papel_subordinado": "lider",
                },
            )
            assert cycle.status_code == 422, cycle.text
            assert cycle.json()["code"] == "leadership_cycle"

            foreign_person = client.post(
                "/api/v1/cadastro/pessoas",
                headers=headers_b,
                json=_person_payload(
                    "Pessoa Tenant B",
                    cpf="52998224725",
                ),
            )
            assert foreign_person.status_code == 201, foreign_person.text
            foreign_id = foreign_person.json()["id"]

            assert (
                client.get(f"/api/v1/cadastro/pessoas/{foreign_id}", headers=headers_a).status_code
                == 404
            )
            cross_tenant_link = client.post(
                "/api/v1/cadastro/hierarquia",
                headers=headers_a,
                json={
                    "lideranca_superior_id": coordinator_body["lideranca"]["id"],
                    "pessoa_subordinada_id": foreign_id,
                    "papel_subordinado": "liderado",
                },
            )
            assert cross_tenant_link.status_code == 404
    finally:
        await _cleanup(engine, tenant_ids)
        await engine.dispose()


@pytest.mark.asyncio
async def test_cad_051_merges_duplicates_with_audit_and_history() -> None:
    """CAD-051: gestor escolhe o principal e o merge preserva snapshots e auditoria."""
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL)
    tenant_ids: list[int] = []
    suffix = uuid4().hex[:10]
    try:
        await _assert_required_schema(engine)
        context = await _create_tenant(engine, suffix, "merge")
        tenant_ids.append(context.id)
        phone = "11999990551"
        source_email = f"origem-merge-{suffix}@example.test"

        with TestClient(app) as client:
            headers = _login(client, context)
            principal_response = client.post(
                "/api/v1/cadastro/pessoas",
                headers=headers,
                json={
                    **_person_payload("Pessoa Principal", phone=phone),
                    "apelido": "Principal",
                },
            )
            assert principal_response.status_code == 201, principal_response.text
            principal = principal_response.json()

            source_response = client.post(
                "/api/v1/cadastro/pessoas",
                headers=headers,
                json={
                    **_person_payload(
                        "Pessoa Origem",
                        phone=phone,
                        email=source_email,
                    ),
                    "apelido": "Apelido da origem",
                },
            )
            assert source_response.status_code == 201, source_response.text
            source = source_response.json()

            duplicate_response = client.get(
                "/api/v1/cadastro/duplicidades",
                headers=headers,
                params={"status": "pendente"},
            )
            assert duplicate_response.status_code == 200, duplicate_response.text
            duplicate = next(
                item
                for item in duplicate_response.json()
                if item["criterio"] == "telefone"
                and {item["pessoa_id"], item["pessoa_duplicada_id"]}
                == {principal["id"], source["id"]}
            )

            preview = client.get(
                f"/api/v1/cadastro/duplicidades/{duplicate['id']}/merge-preview",
                headers=headers,
            )
            assert preview.status_code == 200, preview.text
            assert {preview.json()["pessoa_a"]["id"], preview.json()["pessoa_b"]["id"]} == {
                principal["id"],
                source["id"],
            }
            assert "apelido" in {conflict["campo"] for conflict in preview.json()["conflitos"]}

            merge_response = client.post(
                f"/api/v1/cadastro/duplicidades/{duplicate['id']}/merge",
                headers=headers,
                json={
                    "pessoa_principal_id": principal["id"],
                    "campos_origem": ["apelido"],
                    "confirmar": True,
                },
            )
            assert merge_response.status_code == 200, merge_response.text
            merge = merge_response.json()
            assert merge["pessoa_principal"]["id"] == principal["id"]
            assert merge["pessoa_principal"]["apelido"] == "Apelido da origem"
            assert source_email in {
                contact["valor"] for contact in merge["pessoa_principal"]["contatos"]
            }

            source_detail = client.get(
                f"/api/v1/cadastro/pessoas/{source['id']}",
                headers=headers,
            )
            assert source_detail.status_code == 404

            repeated_merge = client.post(
                f"/api/v1/cadastro/duplicidades/{duplicate['id']}/merge",
                headers=headers,
                json={
                    "pessoa_principal_id": principal["id"],
                    "campos_origem": [],
                    "confirmar": True,
                },
            )
            assert repeated_merge.status_code == 422
            assert repeated_merge.json()["code"] == "duplicate_already_merged"

        async with engine.connect() as connection:
            merge_row = (
                await connection.execute(
                    text(
                        "SELECT pessoa_principal_id, pessoa_origem_id, "
                        "snapshot_principal, snapshot_origem "
                        "FROM cadastro.pessoa_merge "
                        "WHERE tenant_id = :tenant_id"
                    ),
                    {"tenant_id": context.id},
                )
            ).one()
            assert merge_row.pessoa_principal_id == principal["id"]
            assert merge_row.pessoa_origem_id == source["id"]
            assert merge_row.snapshot_principal["id"] == principal["id"]
            assert merge_row.snapshot_origem["id"] == source["id"]

            audit_count = int(
                (
                    await connection.scalar(
                        text(
                            "SELECT count(*) FROM auditoria.log_auditoria "
                            "WHERE tenant_id = :tenant_id "
                            "AND tabela = 'pessoa_merge' AND acao = 'mesclar'"
                        ),
                        {"tenant_id": context.id},
                    )
                )
                or 0
            )
            assert audit_count == 1
    finally:
        await _cleanup(engine, tenant_ids)
        await engine.dispose()
