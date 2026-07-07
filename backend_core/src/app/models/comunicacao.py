"""Modelos do dominio de comunicacao e relacionamento."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.tenants.models import Base


class CanalComunicacao(Base):
    __tablename__ = "canal_comunicacao"
    __table_args__ = (
        Index("ix_canal_comunicacao_tenant_codigo", "tenant_id", "codigo"),
        {"schema": "comunicacao"},
    )

    id: Mapped[int] = mapped_column(SmallInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE")
    )
    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    nome: Mapped[str] = mapped_column(String(60), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TipoInteracao(Base):
    __tablename__ = "tipo_interacao"
    __table_args__ = (
        Index("ix_tipo_interacao_tenant_codigo", "tenant_id", "codigo"),
        {"schema": "comunicacao"},
    )

    id: Mapped[int] = mapped_column(SmallInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE")
    )
    codigo: Mapped[str] = mapped_column(String(30), nullable=False)
    nome: Mapped[str] = mapped_column(String(60), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Interacao(Base):
    __tablename__ = "interacao"
    __table_args__ = (
        Index("ix_interacao_pessoa", "pessoa_id"),
        Index("ix_interacao_tenant_data", "tenant_id", "data_interacao"),
        {"schema": "comunicacao"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    pessoa_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"), nullable=False
    )
    tipo_interacao_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("comunicacao.tipo_interacao.id")
    )
    canal_comunicacao_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("comunicacao.canal_comunicacao.id")
    )
    lideranca_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cadastro.lideranca.id")
    )
    demanda_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("demanda.demanda.id"))
    evento_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("agenda.evento.id"))
    direcao: Mapped[str] = mapped_column(String(10), nullable=False, server_default="saida")
    assunto: Mapped[str | None] = mapped_column(String(180))
    conteudo: Mapped[str | None] = mapped_column(Text)
    resultado: Mapped[str | None] = mapped_column(String(120))
    data_interacao: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    registrado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
