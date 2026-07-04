"""Modelos do dominio de metas, acompanhamentos, alertas e rankings."""

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
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.tenants.models import Base


class TipoMetaVoto(Base):
    __tablename__ = "tipo_meta_voto"
    __table_args__ = {"schema": "meta"}

    id: Mapped[int] = mapped_column(SmallInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    codigo: Mapped[str] = mapped_column(String(30))
    nome: Mapped[str] = mapped_column(String(60))
    descricao: Mapped[str | None] = mapped_column(String(255))
    ativo: Mapped[bool] = mapped_column(Boolean)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PeriodoMeta(Base):
    __tablename__ = "periodo_meta"
    __table_args__ = {"schema": "meta"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    nome: Mapped[str] = mapped_column(String(120))
    data_inicio: Mapped[date] = mapped_column(Date)
    data_fim: Mapped[date] = mapped_column(Date)
    ciclo: Mapped[str | None] = mapped_column(String(30))
    eleicao_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("eleicao.eleicao.id"))
    ativo: Mapped[bool] = mapped_column(Boolean)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MetaVoto(Base):
    __tablename__ = "meta_voto"
    __table_args__ = {"schema": "meta"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    tipo_meta_voto_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("meta.tipo_meta_voto.id")
    )
    periodo_meta_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("meta.periodo_meta.id")
    )
    titulo: Mapped[str | None] = mapped_column(String(150))
    quantidade_meta: Mapped[int] = mapped_column(Integer)
    lideranca_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cadastro.lideranca.id")
    )
    coordenador_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cadastro.lideranca.id")
    )
    territorio_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("territorio.territorio.id")
    )
    municipio_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("global.municipio.id"))
    bairro_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("global.bairro.id"))
    zona_eleitoral_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("global.zona_eleitoral.id")
    )
    secao_eleitoral_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("global.secao_eleitoral.id")
    )
    comunidade_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cadastro.comunidade.id")
    )
    nucleo_familiar_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cadastro.nucleo_familiar.id")
    )
    status: Mapped[str] = mapped_column(String(20))
    criado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    score_risco: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    fatores_risco: Mapped[dict[str, Any]] = mapped_column(JSONB)
    risco_calculado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MetaVotoAlvo(Base):
    __tablename__ = "meta_voto_alvo"
    __table_args__ = {"schema": "meta"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    meta_voto_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("meta.meta_voto.id"))
    tipo_alvo: Mapped[str] = mapped_column(String(30))
    alvo_id: Mapped[int] = mapped_column(BigInteger)
    quantidade_atribuida: Mapped[int | None] = mapped_column(Integer)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AcompanhamentoMeta(Base):
    __tablename__ = "acompanhamento_meta"
    __table_args__ = {"schema": "meta"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    meta_voto_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("meta.meta_voto.id"))
    data_referencia: Mapped[date] = mapped_column(Date)
    quantidade_projetada: Mapped[int | None] = mapped_column(Integer)
    quantidade_confirmada: Mapped[int | None] = mapped_column(Integer)
    quantidade_eleitores_vinculados: Mapped[int | None] = mapped_column(Integer)
    percentual_atingido: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    situacao_risco: Mapped[str] = mapped_column(String(20))
    observacao: Mapped[str | None] = mapped_column(Text)
    criado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AlertaMeta(Base):
    __tablename__ = "alerta_meta"
    __table_args__ = {"schema": "meta"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    meta_voto_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("meta.meta_voto.id"))
    tipo_alerta: Mapped[str] = mapped_column(String(30))
    percentual_referencia: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    mensagem: Mapped[str | None] = mapped_column(String(255))
    severidade: Mapped[str] = mapped_column(String(20))
    resolvido: Mapped[bool] = mapped_column(Boolean)
    gerado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolvido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RankingLideranca(Base):
    __tablename__ = "ranking_lideranca"
    __table_args__ = {"schema": "meta"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    lideranca_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cadastro.lideranca.id"))
    data_referencia: Mapped[date] = mapped_column(Date)
    posicao: Mapped[int | None] = mapped_column(Integer)
    total_cadastros: Mapped[int] = mapped_column(Integer)
    total_confirmacoes: Mapped[int] = mapped_column(Integer)
    total_eventos: Mapped[int] = mapped_column(Integer)
    total_demandas: Mapped[int] = mapped_column(Integer)
    percentual_meta: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    pontuacao: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
