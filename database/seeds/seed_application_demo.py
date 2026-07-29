"""Popula dados demonstrativos completos para os tenants 1, 2 e 3.

Os dados pessoais vêm dos arquivos lote-*.json desta pasta. Zona, seção e local
de votação são escolhidos do CSV oficial informado em ``data/`` e resolvidos
contra os catálogos ``global`` já importados no PostgreSQL.

O seed é seguro para repetição: antes de inserir, remove somente registros
criados por este script, identificados pelo prefixo ``[SEED DEMO]``. Ele nunca
remove cadastros manuais. Toda a execução de cada tenant ocorre em uma única
transação. Use ``--dry-run`` para validar arquivos, banco e referências e então
desfazer as alterações ao final.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import random
import re
import sys
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

import asyncpg


SEED_PREFIX = "[S]"
SEED_VERSION = "2026.07"
SEEDS_DIR = Path(__file__).resolve().parent
APP_ROOT = SEEDS_DIR.parents[1]
PROJECT_ROOT = APP_ROOT.parent
DEFAULT_ENV_FILE = APP_ROOT / "backend_core" / ".env"
DEFAULT_ELECTORAL_CSV = PROJECT_ROOT / "data" / "eleitorado_local_votacao_ATUAL.csv"
GO_STATE_CODE = 52
SEED_ELECTION = {
    "ano": 2026,
    "tipo": "estadual",
    "turno": 1,
    "data_eleicao": date(2026, 10, 4),
}
SEED_CARGO_PLEITEADO = "Deputado(a) Estadual"

TENANT_FILES: dict[int, tuple[str, ...]] = {
    1: ("lote-1.json",),
    2: ("lote-2.json",),
    3: ("lote-3.json", "lote-4.json", "lote-5.json"),
}

TENANT_THEMES = {
    1: {
        "name": "Mobilização comunitária",
        "tags": ("Apoiador confirmado", "Saúde", "Primeira visita", "Mobilização de bairro"),
        "community": "Rede de bairros",
        "goal_factor": 8,
    },
    2: {
        "name": "Participação e juventude",
        "tags": ("Voluntário", "Educação", "Juventude", "Formador de opinião"),
        "community": "Frentes cidadãs",
        "goal_factor": 11,
    },
    3: {
        "name": "Expansão territorial",
        "tags": ("Liderança local", "Infraestrutura", "Evento", "Apoiador estratégico"),
        "community": "Núcleos regionais",
        "goal_factor": 14,
    },
}


@dataclass(frozen=True)
class ElectoralRow:
    city_tse_code: int
    city_name: str
    zone_number: int
    section_number: int
    polling_place_code: int
    polling_place_name: str
    address: str
    neighborhood: str
    cep: str | None
    latitude: float | None
    longitude: float | None


@dataclass
class SeedPerson:
    id: int
    source: dict[str, Any]
    city_code: int
    territory_id: int
    address_id: int
    electoral: dict[str, int | None]


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key.strip()] = value
    return values


def normalize_database_url(url: str) -> str:
    value = url.strip()
    for prefix in ("postgresql+asyncpg://", "postgres+asyncpg://"):
        if value.startswith(prefix):
            return "postgresql://" + value.removeprefix(prefix)
    return value


def validate_database_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname or not parsed.path:
        raise ValueError("A URL deve apontar para um banco PostgreSQL válido.")


def repair_mojibake(value: Any) -> Any:
    """Corrige textos UTF-8 que foram serializados como Latin-1 nos lotes."""
    if isinstance(value, list):
        return [repair_mojibake(item) for item in value]
    if isinstance(value, dict):
        return {key: repair_mojibake(item) for key, item in value.items()}
    if not isinstance(value, str) or not any(token in value for token in ("Ã", "Â", "â")):
        return value
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def normalized(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    return " ".join("".join(char for char in text if not unicodedata.combining(char)).upper().split())


def digits(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def parse_birth_date(value: str) -> date:
    return datetime.strptime(value, "%d/%m/%Y").date()


def parse_decimal(value: str) -> float | None:
    if not value or value in {"-1", "#NULO"}:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def load_people(tenant_ids: Iterable[int]) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = {}
    for tenant_id in tenant_ids:
        people: list[dict[str, Any]] = []
        seen_cpfs: set[str] = set()
        for filename in TENANT_FILES[tenant_id]:
            path = SEEDS_DIR / filename
            if not path.exists():
                raise FileNotFoundError(f"Arquivo de pessoas não encontrado: {path}")
            raw = path.read_bytes()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("cp1252")
            payload = repair_mojibake(json.loads(text))
            if not isinstance(payload, list):
                raise ValueError(f"{filename} deve conter uma lista JSON.")
            for item in payload:
                cpf = digits(item.get("cpf"))
                if len(cpf) != 11:
                    raise ValueError(f"CPF inválido em {filename}: {item.get('cpf')!r}")
                if cpf in seen_cpfs:
                    raise ValueError(f"CPF repetido no tenant {tenant_id}: {cpf}")
                seen_cpfs.add(cpf)
                people.append(item)
        result[tenant_id] = people
    return result


def load_go_electoral_rows(path: Path) -> dict[str, list[ElectoralRow]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV eleitoral não encontrado: {path}")
    by_city: dict[str, list[ElectoralRow]] = defaultdict(list)
    seen: set[tuple[int, int, int, int]] = set()
    sample = path.read_bytes()[:65536]
    try:
        sample.decode("utf-8-sig")
        encoding = "utf-8-sig"
    except UnicodeDecodeError:
        encoding = "cp1252"
    with path.open("r", encoding=encoding, newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";", quotechar='"')
        required = {
            "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_ZONA", "NR_SECAO",
            "NR_LOCAL_VOTACAO", "NM_LOCAL_VOTACAO", "DS_ENDERECO", "NM_BAIRRO",
            "NR_CEP", "NR_LATITUDE", "NR_LONGITUDE", "DS_SITU_LOCAL_VOTACAO",
            "DS_SITU_SECAO",
        }
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            missing = sorted(required - set(reader.fieldnames or []))
            raise ValueError("Colunas ausentes no CSV eleitoral: " + ", ".join(missing))
        for row in reader:
            if row["SG_UF"] != "GO" or row["DS_SITU_SECAO"] != "ATIVO":
                continue
            if row["DS_SITU_LOCAL_VOTACAO"] not in {"ATIVO", "BLOQUEADO"}:
                continue
            try:
                key = (
                    int(row["CD_MUNICIPIO"]), int(row["NR_ZONA"]),
                    int(row["NR_LOCAL_VOTACAO"]), int(row["NR_SECAO"]),
                )
            except ValueError:
                continue
            if key in seen:
                continue
            seen.add(key)
            item = ElectoralRow(
                city_tse_code=key[0], city_name=row["NM_MUNICIPIO"], zone_number=key[1],
                polling_place_code=key[2], section_number=key[3],
                polling_place_name=row["NM_LOCAL_VOTACAO"], address=row["DS_ENDERECO"],
                neighborhood=row["NM_BAIRRO"], cep=digits(row["NR_CEP"]) or None,
                latitude=parse_decimal(row["NR_LATITUDE"]),
                longitude=parse_decimal(row["NR_LONGITUDE"]),
            )
            by_city[normalized(item.city_name)].append(item)
    if not by_city:
        raise ValueError("O CSV não contém seções ativas de Goiás.")
    return by_city


async def require_schema(connection: asyncpg.Connection) -> None:
    required = (
        "cadastro.pessoa", "cadastro.eleitor", "cadastro.lideranca",
        "territorio.territorio", "agenda.evento", "demanda.demanda",
        "meta.meta_voto", "comunicacao.interacao", "global.local_votacao",
        "eleicao.eleicao", "eleicao.campanha_eleicao",
    )
    missing = [name for name in required if await connection.fetchval("SELECT to_regclass($1)", name) is None]
    if missing:
        raise RuntimeError("Migrations pendentes; tabelas ausentes: " + ", ".join(missing))


async def catalog_id(
    connection: asyncpg.Connection,
    table: str,
    code: str,
    tenant_id: int | None = None,
) -> int:
    allowed = {
        "cadastro.pessoa_tipo", "agenda.tipo_evento", "agenda.status_evento",
        "demanda.categoria_demanda", "demanda.status_demanda",
        "demanda.prioridade_demanda", "demanda.origem_demanda",
        "demanda.resultado_atendimento", "meta.tipo_meta_voto",
        "comunicacao.canal_comunicacao", "comunicacao.tipo_interacao",
        "territorio.tipo_territorio",
    }
    if table not in allowed:
        raise ValueError(f"Catálogo não permitido: {table}")
    has_tenant = await connection.fetchval(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=$1 AND table_name=$2 AND column_name='tenant_id')",
        *table.split("."),
    )
    tenant_clause = "AND (tenant_id=$2 OR tenant_id IS NULL) ORDER BY tenant_id DESC NULLS LAST" if has_tenant else ""
    args: tuple[Any, ...] = (code, tenant_id) if has_tenant else (code,)
    value = await connection.fetchval(f"SELECT id FROM {table} WHERE codigo=$1 {tenant_clause} LIMIT 1", *args)
    if value is None:
        raise RuntimeError(f"Catálogo obrigatório ausente: {table}.{code}")
    return int(value)


async def cleanup_seed_data(connection: asyncpg.Connection, tenant_id: int) -> None:
    marker = f"{SEED_PREFIX}%"
    # Ordem protege FKs sem ON DELETE CASCADE. Apenas itens explicitamente marcados são removidos.
    for statement in (
        "DELETE FROM comunicacao.campanha_comunicacao WHERE tenant_id=$1 AND nome LIKE $2",
        "DELETE FROM meta.meta_voto WHERE tenant_id=$1 AND titulo LIKE $2",
        "DELETE FROM meta.periodo_meta WHERE tenant_id=$1 AND nome LIKE $2",
        "DELETE FROM demanda.demanda WHERE tenant_id=$1 AND titulo LIKE $2",
        "DELETE FROM agenda.evento WHERE tenant_id=$1 AND titulo LIKE $2",
        "DELETE FROM cadastro.equipe WHERE tenant_id=$1 AND nome LIKE $2",
        "DELETE FROM cadastro.comunidade WHERE tenant_id=$1 AND descricao LIKE $2",
        "DELETE FROM cadastro.tag WHERE tenant_id=$1 AND descricao LIKE $2",
        "DELETE FROM cadastro.nucleo_familiar WHERE tenant_id=$1 AND nome LIKE $2",
        "DELETE FROM territorio.territorio WHERE tenant_id=$1 AND nome LIKE $2",
        "DELETE FROM cadastro.pessoa WHERE tenant_id=$1 AND observacoes LIKE $2",
        "DELETE FROM cadastro.endereco WHERE tenant_id=$1 AND ponto_referencia LIKE $2",
    ):
        await connection.execute(statement, tenant_id, marker)


async def load_municipalities(connection: asyncpg.Connection) -> dict[str, asyncpg.Record]:
    rows = await connection.fetch(
        "SELECT codigo_ibge,codigo_tse,nome,latitude,longitude FROM global.municipio WHERE codigo_uf_ibge=$1",
        GO_STATE_CODE,
    )
    if not rows:
        raise RuntimeError("Municípios de Goiás não foram importados em global.municipio.")
    return {normalized(str(row["nome"])): row for row in rows}


async def resolve_electoral(
    connection: asyncpg.Connection,
    city_code: int,
    csv_row: ElectoralRow,
) -> dict[str, int | None]:
    zone_id = await connection.fetchval(
        "SELECT id FROM global.zona_eleitoral WHERE codigo_municipio_ibge=$1 AND numero_zona=$2 LIMIT 1",
        city_code, csv_row.zone_number,
    )
    if zone_id is None:
        return {"zone_id": None, "place_id": None, "section_id": None}
    place_id = await connection.fetchval(
        "SELECT id FROM global.local_votacao WHERE codigo_municipio_ibge=$1 AND codigo_local=$2 LIMIT 1",
        city_code, csv_row.polling_place_code,
    )
    if place_id is None:
        place_id = await connection.fetchval(
            "SELECT id FROM global.local_votacao WHERE codigo_municipio_ibge=$1 AND zona_eleitoral_id=$2 ORDER BY id LIMIT 1",
            city_code, zone_id,
        )
    section_id = await connection.fetchval(
        "SELECT id FROM global.secao_eleitoral WHERE zona_eleitoral_id=$1 AND numero_secao=$2 AND ($3::bigint IS NULL OR local_votacao_id=$3) LIMIT 1",
        zone_id, csv_row.section_number, place_id,
    )
    if section_id is None:
        section_id = await connection.fetchval(
            "SELECT id FROM global.secao_eleitoral WHERE zona_eleitoral_id=$1 AND ($2::bigint IS NULL OR local_votacao_id=$2) ORDER BY id LIMIT 1",
            zone_id, place_id,
        )
    return {
        "zone_id": int(zone_id),
        "place_id": int(place_id) if place_id else None,
        "section_id": int(section_id) if section_id else None,
    }


async def create_territories(
    connection: asyncpg.Connection,
    tenant_id: int,
    people: list[dict[str, Any]],
    municipalities: dict[str, asyncpg.Record],
) -> tuple[dict[int, int], dict[tuple[int, str], int]]:
    city_type = await catalog_id(connection, "territorio.tipo_territorio", "municipio", tenant_id)
    neighborhood_type = await catalog_id(connection, "territorio.tipo_territorio", "bairro", tenant_id)
    city_territories: dict[int, int] = {}
    neighborhood_territories: dict[tuple[int, str], int] = {}
    for person in people:
        municipality = municipalities[normalized(person["cidade"])]
        city_code = int(municipality["codigo_ibge"])
        if city_code not in city_territories:
            territory_id = int(await connection.fetchval(
                "INSERT INTO territorio.territorio (tenant_id,tipo_territorio_id,nome,codigo_uf_ibge,codigo_municipio_ibge,ativo) VALUES ($1,$2,$3,$4,$5,TRUE) RETURNING id",
                tenant_id, city_type, f"{SEED_PREFIX} {municipality['nome']}", GO_STATE_CODE, city_code,
            ))
            city_territories[city_code] = territory_id
        neighborhood = str(person.get("bairro") or "Sem bairro")
        key = (city_code, normalized(neighborhood))
        if key not in neighborhood_territories:
            territory_id = int(await connection.fetchval(
                "INSERT INTO territorio.territorio (tenant_id,tipo_territorio_id,nome,codigo_uf_ibge,codigo_municipio_ibge,ativo) VALUES ($1,$2,$3,$4,$5,TRUE) RETURNING id",
                tenant_id, neighborhood_type, f"{SEED_PREFIX} {neighborhood} - {municipality['nome']}", GO_STATE_CODE, city_code,
            ))
            neighborhood_territories[key] = territory_id
            await connection.execute(
                "INSERT INTO territorio.territorio_hierarquia (tenant_id,territorio_pai_id,territorio_filho_id) VALUES ($1,$2,$3)",
                tenant_id, city_territories[city_code], territory_id,
            )
    return city_territories, neighborhood_territories


async def create_people(
    connection: asyncpg.Connection,
    tenant_id: int,
    sources: list[dict[str, Any]],
    municipalities: dict[str, asyncpg.Record],
    electoral_rows: dict[str, list[ElectoralRow]],
    neighborhood_territories: dict[tuple[int, str], int],
    rng: random.Random,
    user_id: int | None,
) -> list[SeedPerson]:
    voter_type = await catalog_id(connection, "cadastro.pessoa_tipo", "eleitor")
    supporter_type = await catalog_id(connection, "cadastro.pessoa_tipo", "apoiador")
    education_ids = [int(row["id"]) for row in await connection.fetch("SELECT id FROM cadastro.escolaridade ORDER BY id")]
    civil_ids = [int(row["id"]) for row in await connection.fetch("SELECT id FROM cadastro.estado_civil ORDER BY ordem,id")]
    profession_ids = [int(row["id"]) for row in await connection.fetch("SELECT id FROM cadastro.profissao WHERE tenant_id IS NULL OR tenant_id=$1 ORDER BY id", tenant_id)]
    religion_ids = [int(row["id"]) for row in await connection.fetch("SELECT id FROM cadastro.religiao ORDER BY id")]
    result: list[SeedPerson] = []
    city_offsets: dict[str, int] = defaultdict(int)
    for index, source in enumerate(sources):
        city_key = normalized(source["cidade"])
        municipality = municipalities.get(city_key)
        if municipality is None:
            raise RuntimeError(f"Município do lote não encontrado no banco: {source['cidade']}")
        candidates = electoral_rows.get(city_key)
        if not candidates:
            raise RuntimeError(f"Município sem seção eleitoral no CSV de Goiás: {source['cidade']}")
        csv_row = candidates[city_offsets[city_key] % len(candidates)]
        city_offsets[city_key] += 1
        city_code = int(municipality["codigo_ibge"])
        electoral = await resolve_electoral(connection, city_code, csv_row)
        sex = {"MASCULINO": "M", "FEMININO": "F"}.get(normalized(str(source.get("sexo", ""))), "N")
        created_at = datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 150))
        observations = (
            f"{SEED_PREFIX} v{SEED_VERSION}; origem lote JSON. "
            f"Interesses: {TENANT_THEMES[tenant_id]['name']}. "
            f"Referências familiares: mãe {source.get('mae', 'não informada')}; pai {source.get('pai', 'não informado')}."
        )
        person_id = int(await connection.fetchval(
            """INSERT INTO cadastro.pessoa
               (tenant_id,nome_completo,apelido,sexo,data_nascimento,estado_civil,
                escolaridade_id,profissao_id,religiao_id,nivel_engajamento,
                score_confiabilidade,completude_cadastral,observacoes,ativo,
                criado_por,atualizado_por,criado_em,atualizado_em)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,0,$12,TRUE,$13,$13,$14,$14)
               RETURNING id""",
            tenant_id, source["nome"], str(source["nome"]).split()[0], sex,
            parse_birth_date(source["data_nasc"]), rng.choice(civil_ids) if civil_ids else None,
            rng.choice(education_ids) if education_ids else None,
            rng.choice(profession_ids) if profession_ids else None,
            rng.choice(religion_ids) if religion_ids and index % 3 else None,
            rng.randint(2, 10), round(rng.uniform(72, 99), 2), observations,
            user_id, created_at,
        ))
        cpf, rg = digits(source["cpf"]), digits(source["rg"])
        await connection.executemany(
            "INSERT INTO cadastro.pessoa_documento (tenant_id,pessoa_id,tipo_documento,numero,orgao_emissor,uf_emissor) VALUES ($1,$2,$3,$4,$5,$6)",
            [(tenant_id, person_id, "cpf", cpf, "Receita Federal", "GO"),
             (tenant_id, person_id, "rg", rg, "SSP", "GO")],
        )
        contacts = [
            (tenant_id, person_id, "whatsapp", str(source["celular"]), True, index % 4 != 0),
            (tenant_id, person_id, "email", str(source["email"]), False, index % 3 != 0),
        ]
        if source.get("telefone_fixo"):
            contacts.append((tenant_id, person_id, "telefone", str(source["telefone_fixo"]), False, False))
        await connection.executemany(
            "INSERT INTO cadastro.pessoa_contato (tenant_id,pessoa_id,tipo_contato,valor,principal,verificado) VALUES ($1,$2,$3,$4,$5,$6)",
            contacts,
        )
        latitude = csv_row.latitude if csv_row.latitude is not None else municipality["latitude"]
        longitude = csv_row.longitude if csv_row.longitude is not None else municipality["longitude"]
        if latitude is not None:
            latitude = float(latitude) + rng.uniform(-0.012, 0.012)
        if longitude is not None:
            longitude = float(longitude) + rng.uniform(-0.012, 0.012)
        address_id = int(await connection.fetchval(
            """INSERT INTO cadastro.endereco
               (tenant_id,codigo_municipio_ibge,bairro_texto,logradouro,numero,cep,
                ponto_referencia,latitude,longitude,geocodificado)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) RETURNING id""",
            tenant_id, city_code, source.get("bairro"), source.get("endereco"),
            str(source.get("numero") or "S/N"), digits(source.get("cep"))[:8] or None,
            f"{SEED_PREFIX} Próximo a {csv_row.polling_place_name}", latitude, longitude,
            latitude is not None and longitude is not None,
        ))
        await connection.execute(
            "INSERT INTO cadastro.pessoa_endereco (tenant_id,pessoa_id,endereco_id,tipo,principal) VALUES ($1,$2,$3,'residencial',TRUE)",
            tenant_id, person_id, address_id,
        )
        await connection.executemany(
            "INSERT INTO cadastro.pessoa_pessoa_tipo (tenant_id,pessoa_id,pessoa_tipo_id) VALUES ($1,$2,$3)",
            [(tenant_id, person_id, voter_type), (tenant_id, person_id, supporter_type)] if index % 5 else [(tenant_id, person_id, voter_type)],
        )
        title_number = f"{tenant_id:02d}{index + 1:010d}"[-12:]
        await connection.execute(
            """INSERT INTO cadastro.eleitor
               (tenant_id,pessoa_id,titulo_eleitor,zona_eleitoral_id,secao_eleitoral_id,
                local_votacao_id,codigo_municipio_ibge,situacao_titulo)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8)""",
            tenant_id, person_id, title_number, electoral["zone_id"], electoral["section_id"],
            electoral["place_id"], city_code, "regular" if index % 17 else "desconhecido",
        )
        territory_key = (city_code, normalized(str(source.get("bairro") or "Sem bairro")))
        territory_id = neighborhood_territories[territory_key]
        await connection.execute(
            "INSERT INTO territorio.pessoa_territorio (tenant_id,pessoa_id,territorio_id,vinculo) VALUES ($1,$2,$3,'moradia')",
            tenant_id, person_id, territory_id,
        )
        result.append(SeedPerson(person_id, source, city_code, territory_id, address_id, electoral))
    return result


async def create_segmentation(
    connection: asyncpg.Connection,
    tenant_id: int,
    people: list[SeedPerson],
    rng: random.Random,
) -> None:
    theme = TENANT_THEMES[tenant_id]
    colors = ("#2563EB", "#059669", "#D97706", "#7C3AED")
    tag_ids: list[int] = []
    for index, name in enumerate(theme["tags"]):
        tag_ids.append(int(await connection.fetchval(
            "INSERT INTO cadastro.tag (tenant_id,nome,cor,categoria,descricao) VALUES ($1,$2,$3,'seed_demo',$4) RETURNING id",
            tenant_id, name, colors[index], f"{SEED_PREFIX} Segmentação demonstrativa",
        )))
    cities = sorted({person.city_code for person in people})
    community_ids: list[int] = []
    for index, city_code in enumerate(cities[: max(3, min(8, len(cities)))]):
        community_ids.append(int(await connection.fetchval(
            "INSERT INTO cadastro.comunidade (tenant_id,nome,tipo,descricao,codigo_municipio_ibge) VALUES ($1,$2,'territorial',$3,$4) RETURNING id",
            tenant_id, f"{theme['community']} {index + 1}", f"{SEED_PREFIX} Comunidade para demonstração", city_code,
        )))
    for index, person in enumerate(people):
        for tag_id in rng.sample(tag_ids, k=1 + (index % min(2, len(tag_ids)))):
            await connection.execute(
                "INSERT INTO cadastro.pessoa_tag (tenant_id,pessoa_id,tag_id) VALUES ($1,$2,$3)",
                tenant_id, person.id, tag_id,
            )
        community_id = community_ids[index % len(community_ids)]
        await connection.execute(
            "INSERT INTO cadastro.pessoa_comunidade (tenant_id,pessoa_id,comunidade_id,papel,desde) VALUES ($1,$2,$3,$4,$5)",
            tenant_id, person.id, community_id, "membro" if index % 7 else "mobilizador",
            date.today() - timedelta(days=30 + index),
        )
        await connection.execute(
            """INSERT INTO cadastro.pessoa_complemento_politico
               (tenant_id,pessoa_id,vinculo_politico,cargo_funcao,temas_interesse,
                nivel_engajamento,observacoes)
               VALUES ($1,$2,$3,$4,$5::jsonb,$6,$7)""",
            tenant_id, person.id, "apoiador" if index % 4 else "simpatizante",
            "mobilizador de bairro" if index % 9 == 0 else None,
            json.dumps(list(theme["tags"][1:3]), ensure_ascii=False), 3 + index % 8,
            f"{SEED_PREFIX} Perfil político para demonstração",
        )
    for start in range(0, len(people), 4):
        members = people[start : start + 4]
        family_id = int(await connection.fetchval(
            "INSERT INTO cadastro.nucleo_familiar (tenant_id,nome,pessoa_referencia_id,endereco_id,quantidade_membros) VALUES ($1,$2,$3,$4,$5) RETURNING id",
            tenant_id, f"{SEED_PREFIX} Família {members[0].source['nome'].split()[-1]} {start // 4 + 1}", members[0].id,
            members[0].address_id, len(members),
        ))
        for member_index, member in enumerate(members):
            await connection.execute(
                "INSERT INTO cadastro.pessoa_nucleo_familiar (tenant_id,pessoa_id,nucleo_familiar_id,parentesco,responsavel) VALUES ($1,$2,$3,$4,$5)",
                tenant_id, member.id, family_id, "responsável" if member_index == 0 else "familiar", member_index == 0,
            )


async def create_leadership_network(
    connection: asyncpg.Connection,
    tenant_id: int,
    people: list[SeedPerson],
    rng: random.Random,
) -> list[dict[str, Any]]:
    counts = {1: (1, 2, 5), 2: (1, 3, 6), 3: (1, 5, 15)}[tenant_id]
    general_count, coordinator_count, leader_count = counts
    total = general_count + coordinator_count + leader_count
    leader_type = await catalog_id(connection, "cadastro.pessoa_tipo", "lider")
    coordinator_type = await catalog_id(connection, "cadastro.pessoa_tipo", "coordenador")
    records: list[dict[str, Any]] = []
    for index, person in enumerate(people[:total]):
        if index < general_count:
            kind, coordinator_id = "coordenador_geral", None
        elif index < general_count + coordinator_count:
            kind, coordinator_id = "coordenador_territorial", records[0]["id"]
        else:
            kind = "lider"
            coordinators = records[general_count : general_count + coordinator_count]
            coordinator_id = coordinators[(index - general_count - coordinator_count) % len(coordinators)]["id"]
        leadership_id = int(await connection.fetchval(
            "INSERT INTO cadastro.lideranca (tenant_id,pessoa_id,tipo_lideranca,coordenador_id,apelido_campanha,ativo) VALUES ($1,$2,$3,$4,$5,TRUE) RETURNING id",
            tenant_id, person.id, kind, coordinator_id, person.source["nome"].split()[0],
        ))
        records.append({"id": leadership_id, "person": person, "kind": kind, "coordinator_id": coordinator_id})
        await connection.execute(
            "INSERT INTO cadastro.pessoa_pessoa_tipo (tenant_id,pessoa_id,pessoa_tipo_id) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING",
            tenant_id, person.id, coordinator_type if "coordenador" in kind else leader_type,
        )
        await connection.execute(
            "INSERT INTO territorio.lideranca_territorio (tenant_id,lideranca_id,territorio_id,responsabilidade) VALUES ($1,$2,$3,'principal')",
            tenant_id, leadership_id, person.territory_id,
        )
    operational_leaders = [item for item in records if item["kind"] == "lider"]
    for index, person in enumerate(people[total:]):
        leader = operational_leaders[index % len(operational_leaders)]
        await connection.execute(
            "INSERT INTO cadastro.hierarquia_lideranca (tenant_id,lideranca_superior_id,pessoa_subordinada_id,papel_subordinado,data_inicio,ativo) VALUES ($1,$2,$3,$4,$5,TRUE)",
            tenant_id, leader["id"], person.id, "apoiador" if index % 3 else "eleitor",
            date.today() - timedelta(days=rng.randint(10, 180)),
        )
        if index > 0:
            indicator = people[max(0, total + index - rng.randint(1, min(index, 5)))].id
            await connection.execute(
                "INSERT INTO cadastro.indicacao (tenant_id,pessoa_indicada_id,pessoa_indicante_id,origem,contexto,data_indicacao) VALUES ($1,$2,$3,'liderança',$4,$5)",
                tenant_id, person.id, indicator, f"{SEED_PREFIX} Indicação durante mobilização",
                date.today() - timedelta(days=rng.randint(1, 90)),
            )
    return records


async def create_interactions(
    connection: asyncpg.Connection,
    tenant_id: int,
    people: list[SeedPerson],
    leaders: list[dict[str, Any]],
    rng: random.Random,
    user_id: int | None,
) -> None:
    channels = {
        code: await catalog_id(connection, "comunicacao.canal_comunicacao", code, tenant_id)
        for code in ("whatsapp", "telefone", "presencial")
    }
    types = {
        code: await catalog_id(connection, "comunicacao.tipo_interacao", code, tenant_id)
        for code in ("ligacao", "visita", "reuniao")
    }
    subjects = (
        "Visita ao comitê", "Contato de acompanhamento", "Convite para evento",
        "Demanda do bairro", "Confirmação de apoio",
    )
    for index, person in enumerate(people):
        interaction_count = 2 + index % 4
        for interaction_index in range(interaction_count):
            subject = subjects[(index + interaction_index + tenant_id) % len(subjects)]
            is_visit = "Visita" in subject
            channel = "presencial" if is_visit else ("whatsapp" if interaction_index % 2 else "telefone")
            interaction_type = "visita" if is_visit else ("reuniao" if "Demanda" in subject else "ligacao")
            await connection.execute(
                """INSERT INTO comunicacao.interacao
                   (tenant_id,pessoa_id,tipo_interacao_id,canal_comunicacao_id,
                    lideranca_id,direcao,assunto,conteudo,resultado,data_interacao,registrado_por)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)""",
                tenant_id, person.id, types[interaction_type], channels[channel],
                leaders[index % len(leaders)]["id"], "entrada" if interaction_index % 3 == 0 else "saida",
                subject, f"{SEED_PREFIX} Registro de relacionamento e escuta ativa com o eleitor.",
                rng.choice(("Aguardando retorno", "Encaminhado à equipe", "Concluído", "Presença confirmada")),
                datetime.now(timezone.utc) - timedelta(days=interaction_index * 8 + index % 12, hours=rng.randint(0, 8)),
                user_id,
            )


async def create_teams(
    connection: asyncpg.Connection,
    tenant_id: int,
    people: list[SeedPerson],
    leaders: list[dict[str, Any]],
) -> None:
    operational = [leader for leader in leaders if leader["kind"] == "lider"]
    for index, leader in enumerate(operational):
        team_id = int(await connection.fetchval(
            "INSERT INTO cadastro.equipe (tenant_id,nome,lideranca_id,territorio_id,ativo) VALUES ($1,$2,$3,$4,TRUE) RETURNING id",
            tenant_id, f"{SEED_PREFIX} Equipe {index + 1:02d} - {leader['person'].source['nome'].split()[0]}",
            leader["id"], leader["person"].territory_id,
        ))
        members = people[index::len(operational)][:8]
        await connection.executemany(
            "INSERT INTO cadastro.equipe_pessoa (tenant_id,equipe_id,pessoa_id) VALUES ($1,$2,$3)",
            [(tenant_id, team_id, person.id) for person in members],
        )


async def ensure_election(connection: asyncpg.Connection) -> int:
    election_id = await connection.fetchval(
        "SELECT id FROM eleicao.eleicao WHERE ano=$1 AND tipo=$2 AND turno=$3 "
        "AND codigo_uf_ibge=$4 AND codigo_municipio_ibge IS NULL",
        SEED_ELECTION["ano"], SEED_ELECTION["tipo"], SEED_ELECTION["turno"], GO_STATE_CODE,
    )
    if election_id is not None:
        return int(election_id)
    return int(await connection.fetchval(
        """INSERT INTO eleicao.eleicao (ano,tipo,turno,data_eleicao,codigo_uf_ibge,descricao)
           VALUES ($1,$2,$3,$4,$5,$6) RETURNING id""",
        SEED_ELECTION["ano"], SEED_ELECTION["tipo"], SEED_ELECTION["turno"], SEED_ELECTION["data_eleicao"],
        GO_STATE_CODE, f"{SEED_PREFIX} Eleição demonstrativa {SEED_ELECTION['ano']}",
    ))


async def ensure_active_campaign(
    connection: asyncpg.Connection,
    tenant_id: int,
    election_id: int,
    user_id: int | None,
) -> None:
    active_id = await connection.fetchval(
        "SELECT id FROM eleicao.campanha_eleicao WHERE tenant_id=$1 AND ativa LIMIT 1",
        tenant_id,
    )
    if active_id is not None:
        return
    campaign_id = await connection.fetchval(
        "SELECT id FROM eleicao.campanha_eleicao WHERE tenant_id=$1 AND eleicao_id=$2",
        tenant_id, election_id,
    )
    if campaign_id is not None:
        await connection.execute(
            "UPDATE eleicao.campanha_eleicao SET ativa=TRUE, data_ativacao=COALESCE(data_ativacao, now()) WHERE id=$1",
            campaign_id,
        )
        return
    await connection.execute(
        """INSERT INTO eleicao.campanha_eleicao
           (tenant_id,eleicao_id,nome,cargo_pleiteado,ativa,criado_por,data_ativacao)
           VALUES ($1,$2,$3,$4,TRUE,$5,now())""",
        tenant_id, election_id, f"{SEED_PREFIX} {TENANT_THEMES[tenant_id]['name']}",
        SEED_CARGO_PLEITEADO, user_id,
    )


async def create_goals(
    connection: asyncpg.Connection,
    tenant_id: int,
    leaders: list[dict[str, Any]],
    rng: random.Random,
    user_id: int | None,
) -> None:
    campaign_id = await connection.fetchval(
        "SELECT id FROM eleicao.campanha_eleicao "
        "WHERE tenant_id=$1 AND ativa ORDER BY id DESC LIMIT 1",
        tenant_id,
    )
    if campaign_id is None:
        raise RuntimeError(f"Tenant {tenant_id} nao possui campanha ativa.")
    period_id = int(await connection.fetchval(
        "INSERT INTO meta.periodo_meta (tenant_id,nome,data_inicio,data_fim,ciclo,ativo) VALUES ($1,$2,$3,$4,'campanha',TRUE) RETURNING id",
        tenant_id, f"{SEED_PREFIX} Ciclo eleitoral demonstrativo {tenant_id}", date.today() - timedelta(days=90), date.today() + timedelta(days=120),
    ))
    goal_type = await catalog_id(connection, "meta.tipo_meta_voto", "lider", tenant_id)
    for index, leader in enumerate(leaders):
        target = TENANT_THEMES[tenant_id]["goal_factor"] * (6 + index)
        achieved = int(target * rng.uniform(0.35, 1.12))
        percentage = round(100 * achieved / target, 2)
        status = "concluida" if percentage >= 100 else ("em_risco" if percentage < 55 else "ativa")
        goal_id = int(await connection.fetchval(
            """INSERT INTO meta.meta_voto
               (tenant_id,campanha_eleicao_id,tipo_meta_voto_id,periodo_meta_id,titulo,quantidade_meta,
                lideranca_id,coordenador_id,territorio_id,status,criado_por,
                score_risco,fatores_risco,risco_calculado_em)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb,now()) RETURNING id""",
            tenant_id, campaign_id, goal_type, period_id,
            f"{SEED_PREFIX} Meta de {leader['person'].source['nome'].split()[0]}", target,
            leader["id"], leader["coordinator_id"], leader["person"].territory_id,
            status, user_id, max(0, 100 - percentage),
            json.dumps({"seed": True, "ritmo": "alto" if percentage >= 70 else "atenção"}),
        ))
        for days_ago, factor in ((60, 0.25), (30, 0.58), (0, 1.0)):
            confirmed = min(target, int(achieved * factor))
            current_percentage = round(100 * confirmed / target, 2)
            risk = "normal" if current_percentage >= (35 if days_ago else 70) else "risco"
            await connection.execute(
                """INSERT INTO meta.acompanhamento_meta
                   (tenant_id,meta_voto_id,data_referencia,quantidade_projetada,
                    quantidade_confirmada,quantidade_eleitores_vinculados,percentual_atingido,situacao_risco,
                    observacao,criado_por)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
                tenant_id, goal_id, date.today() - timedelta(days=days_ago),
                confirmed + rng.randint(2, 12), confirmed, confirmed + rng.randint(1, 8),
                current_percentage, risk, f"{SEED_PREFIX} Acompanhamento automático", user_id,
            )


async def create_events_and_demands(
    connection: asyncpg.Connection,
    tenant_id: int,
    people: list[SeedPerson],
    leaders: list[dict[str, Any]],
    rng: random.Random,
    user_id: int | None,
) -> None:
    event_types = [await catalog_id(connection, "agenda.tipo_evento", code, tenant_id) for code in ("politico", "comunitario", "institucional")]
    status_planned = await catalog_id(connection, "agenda.status_evento", "planejado", tenant_id)
    status_done = await catalog_id(connection, "agenda.status_evento", "realizado", tenant_id)
    event_ids: list[int] = []
    event_count = {1: 8, 2: 10, 3: 18}[tenant_id]
    for index in range(event_count):
        person = people[(index * 5) % len(people)]
        past = index < event_count // 2
        start_date = datetime.now(timezone.utc) + timedelta(days=(-35 + index * 5) if past else (index + 2) * 3)
        event_id = int(await connection.fetchval(
            """INSERT INTO agenda.evento
               (tenant_id,tipo_evento_id,status_evento_id,titulo,descricao,data_inicio,
                data_fim,local_nome,codigo_municipio_ibge,territorio_id,
                responsavel_pessoa_id,numero_presentes,criado_por)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13) RETURNING id""",
            tenant_id, event_types[index % len(event_types)], status_done if past else status_planned,
            f"{SEED_PREFIX} {TENANT_THEMES[tenant_id]['name']} #{index + 1}",
            "Encontro demonstrativo com lideranças, apoiadores e moradores.", start_date,
            start_date + timedelta(hours=2), person.source.get("bairro"), person.city_code,
            person.territory_id, leaders[index % len(leaders)]["person"].id,
            rng.randint(18, 140) if past else None, user_id,
        ))
        event_ids.append(event_id)
        participants = rng.sample(people, k=min(len(people), 6 + index % 8))
        await connection.executemany(
            "INSERT INTO agenda.evento_participante (tenant_id,evento_id,pessoa_id,papel,presente,observacao) VALUES ($1,$2,$3,'convidado',$4,$5)",
            [(tenant_id, event_id, person_item.id, past and participant_index % 4 != 0, f"{SEED_PREFIX} Participação") for participant_index, person_item in enumerate(participants)],
        )
        await connection.execute(
            "INSERT INTO agenda.evento_lideranca (tenant_id,evento_id,lideranca_id,papel) VALUES ($1,$2,$3,'responsável')",
            tenant_id, event_id, leaders[index % len(leaders)]["id"],
        )
        await connection.execute(
            "INSERT INTO agenda.pauta_evento (tenant_id,evento_id,titulo,descricao,encaminhamento,ordem) VALUES ($1,$2,'Prioridades locais',$3,$4,1)",
            tenant_id, event_id, "Levantamento das prioridades apresentadas pela comunidade.", "Consolidar demandas e responsáveis.",
        )
        if past:
            await connection.execute(
                """INSERT INTO agenda.presenca_evento
                   (tenant_id,evento_id,presenca_parlamentar,presenca_representante,
                    numero_lideres_presentes,numero_convidados,numero_estimado_presentes,
                    observacao,registrado_por)
                   VALUES ($1,$2,$3,TRUE,$4,$5,$6,$7,$8)""",
                tenant_id, event_id, index % 3 == 0, min(5, len(leaders)), len(participants),
                rng.randint(25, 160), f"{SEED_PREFIX} Presença consolidada", user_id,
            )

    categories = [await catalog_id(connection, "demanda.categoria_demanda", code, tenant_id) for code in ("saude", "educacao", "infraestrutura", "transporte")]
    priorities = [await catalog_id(connection, "demanda.prioridade_demanda", code, tenant_id) for code in ("baixa", "media", "alta", "urgente")]
    origins = [await catalog_id(connection, "demanda.origem_demanda", code, tenant_id) for code in ("evento", "whatsapp", "lider")]
    statuses = [await catalog_id(connection, "demanda.status_demanda", code, tenant_id) for code in ("pendente", "em_andamento", "concluida")]
    demand_count = {1: 12, 2: 16, 3: 32}[tenant_id]
    titles = ("Consulta especializada", "Iluminação pública", "Vaga em creche", "Linha de ônibus", "Regularização de via")
    for index in range(demand_count):
        person = people[(index * 3) % len(people)]
        status_index = index % len(statuses)
        requested = date.today() - timedelta(days=rng.randint(0, 80))
        await connection.execute(
            """INSERT INTO demanda.demanda
               (tenant_id,protocolo,categoria_demanda_id,prioridade_demanda_id,
                status_demanda_id,origem_demanda_id,titulo,descricao,
                pessoa_solicitante_id,lideranca_indicacao_id,evento_id,territorio_id,
                codigo_municipio_ibge,data_solicitacao,prazo,classificacao_automatica,
                classificacao_detalhes,criado_por)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,TRUE,$16::jsonb,$17)""",
            tenant_id, f"SD-{tenant_id}-{index + 1:04d}", categories[index % len(categories)],
            priorities[(index + tenant_id) % len(priorities)], statuses[status_index],
            origins[index % len(origins)], f"{SEED_PREFIX} {titles[index % len(titles)]}",
            "Solicitação demonstrativa registrada durante o relacionamento com a comunidade.",
            person.id, leaders[index % len(leaders)]["id"], event_ids[index % len(event_ids)] if index % 3 == 0 else None,
            person.territory_id, person.city_code, requested,
            requested + timedelta(days=15 + index % 25),
            json.dumps({"seed": True, "confianca": round(rng.uniform(0.72, 0.98), 2)}), user_id,
        )


async def update_completeness(connection: asyncpg.Connection, tenant_id: int) -> None:
    exists = await connection.fetchval("SELECT to_regprocedure('cadastro.calcular_completude_cadastral(bigint)') IS NOT NULL")
    if exists:
        await connection.execute(
            "UPDATE cadastro.pessoa SET completude_cadastral=cadastro.calcular_completude_cadastral(id) WHERE tenant_id=$1 AND observacoes LIKE $2",
            tenant_id, f"{SEED_PREFIX}%",
        )


async def seed_tenant(
    connection: asyncpg.Connection,
    tenant_id: int,
    sources: list[dict[str, Any]],
    electoral_rows: dict[str, list[ElectoralRow]],
    seed_number: int,
    dry_run: bool,
) -> dict[str, int]:
    transaction = connection.transaction()
    await transaction.start()
    try:
        await connection.execute("SELECT set_config('app.current_tenant_id',$1,true)", str(tenant_id))
        tenant = await connection.fetchrow("SELECT id,nome FROM public.tenant WHERE id=$1 AND excluido_em IS NULL", tenant_id)
        if tenant is None:
            raise RuntimeError(f"Tenant {tenant_id} não existe ou foi excluído.")
        user_id = await connection.fetchval(
            "SELECT id FROM auth.usuario WHERE tenant_id=$1 AND status='ativo' AND excluido_em IS NULL ORDER BY id LIMIT 1",
            tenant_id,
        )
        municipalities = await load_municipalities(connection)
        missing_cities = sorted({source["cidade"] for source in sources if normalized(source["cidade"]) not in municipalities})
        if missing_cities:
            raise RuntimeError("Municípios não encontrados no catálogo global: " + ", ".join(missing_cities))
        election_id = await ensure_election(connection)
        await ensure_active_campaign(connection, tenant_id, election_id, int(user_id) if user_id else None)
        await cleanup_seed_data(connection, tenant_id)
        rng = random.Random(seed_number + tenant_id * 1009)
        _, neighborhood_territories = await create_territories(connection, tenant_id, sources, municipalities)
        people = await create_people(
            connection, tenant_id, sources, municipalities, electoral_rows,
            neighborhood_territories, rng, int(user_id) if user_id else None,
        )
        await create_segmentation(connection, tenant_id, people, rng)
        leaders = await create_leadership_network(connection, tenant_id, people, rng)
        await create_interactions(connection, tenant_id, people, leaders, rng, int(user_id) if user_id else None)
        await create_teams(connection, tenant_id, people, leaders)
        await create_goals(connection, tenant_id, leaders, rng, int(user_id) if user_id else None)
        await create_events_and_demands(connection, tenant_id, people, leaders, rng, int(user_id) if user_id else None)
        await update_completeness(connection, tenant_id)
        stats = {
            "pessoas": len(people), "liderancas": len(leaders),
            "territorios": len(neighborhood_territories),
            "eventos": {1: 8, 2: 10, 3: 18}[tenant_id],
            "demandas": {1: 12, 2: 16, 3: 32}[tenant_id],
        }
        if dry_run:
            await transaction.rollback()
        else:
            await transaction.commit()
        return stats
    except BaseException:
        await transaction.rollback()
        raise


async def run(args: argparse.Namespace, database_url: str) -> dict[int, dict[str, int]]:
    people_by_tenant = load_people(args.tenants)
    electoral_rows = load_go_electoral_rows(args.electoral_csv)
    connection = await asyncpg.connect(database_url)
    try:
        await require_schema(connection)
        result: dict[int, dict[str, int]] = {}
        for tenant_id in args.tenants:
            result[tenant_id] = await seed_tenant(
                connection, tenant_id, people_by_tenant[tenant_id], electoral_rows,
                args.seed, args.dry_run,
            )
        return result
    finally:
        await connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Popula dados completos de demonstração para os tenants 1, 2 e 3.")
    parser.add_argument("--database-url", help="URL PostgreSQL; padrão: DATABASE_URL ou --env-file.")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--environment", choices=("local", "test"))
    parser.add_argument("--tenants", type=int, nargs="+", default=[1, 2, 3], choices=sorted(TENANT_FILES))
    parser.add_argument("--electoral-csv", type=Path, default=DEFAULT_ELECTORAL_CSV)
    parser.add_argument("--seed", type=int, default=20260721, help="Semente aleatória determinística.")
    parser.add_argument("--dry-run", action="store_true", help="Valida e executa tudo, mas desfaz cada transação.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env = read_env_file(args.env_file)
    environment = (args.environment or os.getenv("ENVIRONMENT") or env.get("ENVIRONMENT") or "local").lower()
    if environment not in {"local", "test"}:
        print("Erro: este seed só pode executar com ENVIRONMENT=local ou test.", file=sys.stderr)
        return 2
    database_url = args.database_url or os.getenv("DATABASE_URL") or env.get("DATABASE_URL")
    if not database_url:
        print("Erro: informe --database-url, DATABASE_URL ou --env-file.", file=sys.stderr)
        return 2
    try:
        database_url = normalize_database_url(database_url)
        validate_database_url(database_url)
        stats = asyncio.run(run(args, database_url))
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError, asyncpg.PostgresError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    mode = "DRY-RUN concluído (nenhuma alteração persistida)" if args.dry_run else "Seed concluído"
    print(mode + ".")
    for tenant_id, tenant_stats in stats.items():
        summary = ", ".join(f"{key}={value}" for key, value in tenant_stats.items())
        print(f"Tenant {tenant_id}: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
