"""Contratos HTTP do modulo de importacao."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SourceType = Literal[
    "gesped", "tse", "ibge", "planilha", "formulario", "api", "manual", "outro"
]
ImportStatus = Literal[
    "pendente", "processando", "concluida", "falha", "parcial", "cancelada"
]


class EtlSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class SourceCreate(EtlSchema):
    codigo: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9_]+$")
    nome: str = Field(min_length=2, max_length=120)
    tipo: SourceType
    descricao: str | None = Field(default=None, max_length=255)


class SourceUpdate(EtlSchema):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    tipo: SourceType | None = None
    descricao: str | None = Field(default=None, max_length=255)
    ativo: bool | None = None


class SourceResponse(SourceCreate):
    id: int
    tenant_id: int | None
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime


class ColumnMappingUpdate(EtlSchema):
    mapeamento: dict[str, str] = Field(min_length=1)
    parametros: dict[str, Any] = Field(default_factory=dict)
    reprocessar: bool = True


class ImportFileResponse(EtlSchema):
    id: int
    arquivo_id: int | None
    nome_arquivo: str | None


class ImportResponse(EtlSchema):
    id: int
    tenant_id: int
    fonte_dado_id: int
    fonte_nome: str
    descricao: str | None
    tipo_destino: str | None
    status: ImportStatus
    parametros: dict[str, Any]
    mapeamento_colunas: dict[str, str]
    total_linhas: int
    linhas_validas: int
    linhas_erro: int
    linhas_duplicadas: int
    linhas_pendentes: int
    linhas_carregadas: int
    iniciado_em: datetime | None
    concluido_em: datetime | None
    criado_por: int | None
    aprovado_por: int | None
    criado_em: datetime
    atualizado_em: datetime
    arquivo: ImportFileResponse | None = None


class ImportSummary(EtlSchema):
    importacao_id: int
    status: ImportStatus
    total: int
    validas: int
    invalidas: int
    duplicadas: int
    pendentes: int
    carregadas: int
    avisos: int


class ImportErrorResponse(EtlSchema):
    id: int
    numero_linha: int | None
    etapa: str | None
    campo: str | None
    valor: str | None
    mensagem: str
    severidade: str
    criado_em: datetime


class DuplicateResponse(EtlSchema):
    id: int
    staging_pessoa_id: int | None
    pessoa_candidata_id: int | None
    criterio: str | None
    score: Decimal | None
    decisao: str
    detalhes: dict[str, Any]


class JobResponse(EtlSchema):
    job_id: int
    importacao_id: int
    status: str = "enfileirado"
