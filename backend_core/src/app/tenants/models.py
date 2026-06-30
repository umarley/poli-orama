from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class PlanoAssinatura(Base):
    __tablename__ = "plano_assinatura"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uuid_publico: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), unique=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    nome: Mapped[str] = mapped_column(String(120), unique=True)
    descricao: Mapped[str | None] = mapped_column(Text)
    preco_mensal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    moeda: Mapped[str] = mapped_column(String(3))
    limite_usuarios: Mapped[int | None] = mapped_column(Integer)
    limite_pessoas: Mapped[int | None] = mapped_column(Integer)
    limite_armazenamento_mb: Mapped[int | None] = mapped_column(Integer)
    recursos: Mapped[dict[str, Any]] = mapped_column(JSONB)
    ordem_comercial: Mapped[int] = mapped_column(Integer)
    ativo: Mapped[bool] = mapped_column(Boolean)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Tenant(Base):
    __tablename__ = "tenant"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uuid_publico: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), unique=True)
    nome: Mapped[str] = mapped_column(String(180))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    documento: Mapped[str | None] = mapped_column(String(20))
    tem_mandato: Mapped[bool] = mapped_column(Boolean)
    plano_assinatura_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("public.plano_assinatura.id")
    )
    data_inicio_contrato: Mapped[date | None] = mapped_column(Date)
    data_fim_contrato: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    excluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    plano: Mapped[PlanoAssinatura | None] = relationship(lazy="joined")
    configuracao: Mapped["TenantConfiguracao | None"] = relationship(
        back_populates="tenant", uselist=False, lazy="selectin"
    )


class TenantConfiguracao(Base):
    __tablename__ = "tenant_configuracao"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), unique=True
    )
    nome_publico: Mapped[str | None] = mapped_column(String(180))
    cor_primaria: Mapped[str | None] = mapped_column(String(9))
    logo_url: Mapped[str | None] = mapped_column(Text)
    fuso_horario: Mapped[str] = mapped_column(String(60))
    percentual_alerta_meta: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    integracoes: Mapped[dict[str, Any]] = mapped_column(JSONB)
    preferencias: Mapped[dict[str, Any]] = mapped_column(JSONB)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    tenant: Mapped[Tenant] = relationship(back_populates="configuracao")


class LeadComercial(Base):
    __tablename__ = "lead_comercial"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uuid_publico: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), unique=True)
    nome: Mapped[str] = mapped_column(String(180))
    email: Mapped[str] = mapped_column(String(254))
    telefone: Mapped[str | None] = mapped_column(String(20))
    organizacao: Mapped[str | None] = mapped_column(String(180))
    mensagem: Mapped[str | None] = mapped_column(Text)
    consentimento: Mapped[bool] = mapped_column(Boolean)
    consentido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    origem: Mapped[dict[str, Any]] = mapped_column(JSONB)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Contratacao(Base):
    __tablename__ = "contratacao"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uuid_publico: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), unique=True)
    plano_assinatura_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.plano_assinatura.id")
    )
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    nome: Mapped[str] = mapped_column(String(180))
    email: Mapped[str] = mapped_column(String(254))
    telefone: Mapped[str | None] = mapped_column(String(20))
    documento: Mapped[str | None] = mapped_column(String(20))
    nome_campanha: Mapped[str] = mapped_column(String(180))
    slug_solicitado: Mapped[str] = mapped_column(String(80))
    consentimento: Mapped[bool] = mapped_column(Boolean)
    origem: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20))
    chave_idempotencia: Mapped[str] = mapped_column(String(64), unique=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    plano: Mapped[PlanoAssinatura] = relationship(lazy="joined")


class CheckoutSession(Base):
    __tablename__ = "checkout_session"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uuid_publico: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), unique=True)
    contratacao_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.contratacao.id", ondelete="CASCADE")
    )
    provedor: Mapped[str] = mapped_column(String(40))
    referencia_externa: Mapped[str | None] = mapped_column(String(180), unique=True)
    status: Mapped[str] = mapped_column(String(20))
    url_checkout: Mapped[str | None] = mapped_column(Text)
    chave_idempotencia: Mapped[str] = mapped_column(String(64), unique=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EventoOperacional(Base):
    __tablename__ = "evento_operacional"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(60))
    entidade: Mapped[str] = mapped_column(String(60))
    entidade_id: Mapped[int] = mapped_column(BigInteger)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
