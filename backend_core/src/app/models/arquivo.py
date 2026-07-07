"""Modelos de arquivos, anexos e documentos extraidos."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.tenants.models import Base


class TipoAnexo(Base):
    __tablename__ = "tipo_anexo"
    __table_args__ = {"schema": "arquivo"}

    id: Mapped[int] = mapped_column(SmallInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE")
    )
    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    nome: Mapped[str] = mapped_column(String(60), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Arquivo(Base):
    __tablename__ = "arquivo"
    __table_args__ = {"schema": "arquivo"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    uuid_publico: Mapped[Any] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    nome_original: Mapped[str] = mapped_column(String(255), nullable=False)
    nome_armazenado: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str | None] = mapped_column(String(120))
    extensao: Mapped[str | None] = mapped_column(String(20))
    tamanho_bytes: Mapped[int | None] = mapped_column(BigInteger)
    hash_sha256: Mapped[str | None] = mapped_column(String(64))
    provedor_storage: Mapped[str] = mapped_column(String(40), nullable=False)
    bucket: Mapped[str | None] = mapped_column(String(120))
    caminho: Mapped[str] = mapped_column(Text, nullable=False)
    url_publica: Mapped[str | None] = mapped_column(Text)
    criado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    excluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Anexo(Base):
    __tablename__ = "anexo"
    __table_args__ = {"schema": "arquivo"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    arquivo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("arquivo.arquivo.id", ondelete="CASCADE"), nullable=False
    )
    tipo_anexo_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("arquivo.tipo_anexo.id")
    )
    entidade_tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    entidade_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255))
    criado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    excluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentoExtraido(Base):
    __tablename__ = "documento_extraido"
    __table_args__ = {"schema": "arquivo"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    arquivo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("arquivo.arquivo.id", ondelete="CASCADE"), nullable=False
    )
    texto_extraido: Mapped[str | None] = mapped_column(Text)
    metadados: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    metodo_extracao: Mapped[str | None] = mapped_column(String(40))
    idioma: Mapped[str | None] = mapped_column(String(10))
    processado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
