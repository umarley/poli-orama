"""Contratos HTTP do modulo de arquivos."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

EntityType = Literal[
    "pessoa",
    "evento",
    "demanda",
    "interacao",
    "importacao",
    "comunidade",
    "lideranca",
    "convite",
    "tenant",
    "contrato",
]


class AttachmentTypeCreate(BaseModel):
    codigo: str = Field(min_length=2, max_length=30, pattern=r"^[a-z0-9_]+$")
    nome: str = Field(min_length=2, max_length=60)
    descricao: str | None = Field(default=None, max_length=255)


class AttachmentTypeUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=60)
    descricao: str | None = Field(default=None, max_length=255)
    ativo: bool | None = None


class AttachmentTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int | None = None
    codigo: str
    nome: str
    descricao: str | None = None
    ativo: bool = True


class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid_publico: UUID
    nome_original: str
    mime_type: str | None
    extensao: str | None
    tamanho_bytes: int | None
    hash_sha256: str | None
    provedor_storage: str
    criado_em: datetime


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entidade_tipo: EntityType
    entidade_id: int
    descricao: str | None
    criado_em: datetime
    tipo: AttachmentTypeResponse | None
    arquivo: FileResponse
    download_url: str
    preview_url: str | None = None


class ExtractedDocumentResponse(BaseModel):
    arquivo_id: int
    nome_original: str
    entidade_tipo: EntityType
    entidade_id: int
    texto_extraido: str
    metodo_extracao: str | None
    processado_em: datetime
    download_url: str
