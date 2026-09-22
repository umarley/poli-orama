"""Modelos de materiais, rotas e movimentacoes do modulo Anuncios."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.tenants.models import Base


class MaterialComunicacao(Base):
    __tablename__ = "material_comunicacao"
    __table_args__ = {"schema": "anuncio"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    uuid_publico: Mapped[Any] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    nome: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean)
    criado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RotaComunicacao(Base):
    __tablename__ = "rota_comunicacao"
    __table_args__ = {"schema": "anuncio"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    uuid_publico: Mapped[Any] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    nome: Mapped[str] = mapped_column(String(180))
    descricao: Mapped[str | None] = mapped_column(Text)
    territorio_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("territorio.territorio.id")
    )
    ativo: Mapped[bool] = mapped_column(Boolean)
    criado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    atualizado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RotaComunicacaoPonto(Base):
    __tablename__ = "rota_comunicacao_ponto"
    __table_args__ = {"schema": "anuncio"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    uuid_publico: Mapped[Any] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    rota_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("anuncio.rota_comunicacao.id"))
    ordem: Mapped[int] = mapped_column(Integer)
    descricao_local: Mapped[str] = mapped_column(String(180))
    endereco: Mapped[str | None] = mapped_column(Text)
    latitude_planejada: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude_planejada: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    observacao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RotaComunicacaoPontoMaterial(Base):
    __tablename__ = "rota_comunicacao_ponto_material"
    __table_args__ = {"schema": "anuncio"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    ponto_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("anuncio.rota_comunicacao_ponto.id")
    )
    material_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("anuncio.material_comunicacao.id")
    )
    quantidade_planejada: Mapped[int] = mapped_column(Integer)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RotaComunicacaoPlanejamento(Base):
    __tablename__ = "rota_comunicacao_planejamento"
    __table_args__ = {"schema": "anuncio"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    uuid_publico: Mapped[Any] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    rota_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("anuncio.rota_comunicacao.id"))
    rota_nome: Mapped[str] = mapped_column(String(180))
    rota_descricao: Mapped[str | None] = mapped_column(Text)
    territorio_id: Mapped[int | None] = mapped_column(BigInteger)
    territorio_nome: Mapped[str | None] = mapped_column(String(180))
    equipe_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cadastro.equipe.id"))
    usuario_responsavel_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("auth.usuario.id")
    )
    data_execucao: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))
    observacao: Mapped[str | None] = mapped_column(Text)
    criado_por: Mapped[int] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    atualizado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RotaComunicacaoPlanejamentoPonto(Base):
    __tablename__ = "rota_comunicacao_planejamento_ponto"
    __table_args__ = {"schema": "anuncio"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    uuid_publico: Mapped[Any] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    planejamento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("anuncio.rota_comunicacao_planejamento.id")
    )
    rota_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("anuncio.rota_comunicacao.id"))
    rota_ponto_origem_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("anuncio.rota_comunicacao_ponto.id")
    )
    ordem: Mapped[int] = mapped_column(Integer)
    descricao_local: Mapped[str] = mapped_column(String(180))
    endereco: Mapped[str | None] = mapped_column(Text)
    latitude_planejada: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude_planejada: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    observacao: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RotaComunicacaoPlanejamentoPontoMaterial(Base):
    __tablename__ = "rota_comunicacao_planejamento_ponto_material"
    __table_args__ = {"schema": "anuncio"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    ponto_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("anuncio.rota_comunicacao_planejamento_ponto.id")
    )
    material_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("anuncio.material_comunicacao.id")
    )
    quantidade_planejada: Mapped[int] = mapped_column(Integer)
    quantidade_instalada: Mapped[int] = mapped_column(Integer)
    quantidade_recolhida: Mapped[int] = mapped_column(Integer)
    quantidade_extraviada: Mapped[int] = mapped_column(Integer)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RotaComunicacaoExecucao(Base):
    __tablename__ = "rota_comunicacao_execucao"
    __table_args__ = {"schema": "anuncio"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    uuid_publico: Mapped[Any] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    planejamento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("anuncio.rota_comunicacao_planejamento.id")
    )
    rota_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("anuncio.rota_comunicacao.id"))
    ponto_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("anuncio.rota_comunicacao_planejamento_ponto.id")
    )
    usuario_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    tipo_operacao: Mapped[str] = mapped_column(String(20))
    chave_idempotencia: Mapped[str] = mapped_column(String(64))
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7))
    precisao: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    observacao: Mapped[str | None] = mapped_column(Text)
    executado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RotaComunicacaoMaterialMovimentacao(Base):
    __tablename__ = "rota_comunicacao_material_movimentacao"
    __table_args__ = {"schema": "anuncio"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    uuid_publico: Mapped[Any] = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    execucao_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("anuncio.rota_comunicacao_execucao.id")
    )
    planejamento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("anuncio.rota_comunicacao_planejamento.id")
    )
    rota_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("anuncio.rota_comunicacao.id"))
    ponto_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("anuncio.rota_comunicacao_planejamento_ponto.id")
    )
    material_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("anuncio.material_comunicacao.id")
    )
    usuario_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    tipo_movimentacao: Mapped[str] = mapped_column(String(20))
    quantidade: Mapped[int] = mapped_column(Integer)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7))
    observacao: Mapped[str | None] = mapped_column(Text)
    registrado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
