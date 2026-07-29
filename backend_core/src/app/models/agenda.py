"""Modelos de agenda, eventos, presenca, lembretes e insights."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.tenants.models import Base


class TipoEvento(Base):
    __tablename__ = "tipo_evento"
    __table_args__ = {"schema": "agenda"}

    id: Mapped[int] = mapped_column(SmallInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    codigo: Mapped[str] = mapped_column(String(40))
    nome: Mapped[str] = mapped_column(String(80))
    descricao: Mapped[str | None] = mapped_column(String(255))
    ativo: Mapped[bool] = mapped_column(Boolean)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StatusEvento(Base):
    __tablename__ = "status_evento"
    __table_args__ = {"schema": "agenda"}

    id: Mapped[int] = mapped_column(SmallInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    codigo: Mapped[str] = mapped_column(String(30))
    nome: Mapped[str] = mapped_column(String(60))
    descricao: Mapped[str | None] = mapped_column(String(255))
    ativo: Mapped[bool] = mapped_column(Boolean)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Evento(Base):
    __tablename__ = "evento"
    __table_args__ = {"schema": "agenda"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    uuid_publico: Mapped[Any] = mapped_column(UUID(as_uuid=True))
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    contexto: Mapped[str] = mapped_column(String(20))
    campanha_eleicao_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("eleicao.campanha_eleicao.id")
    )
    tipo_evento_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("agenda.tipo_evento.id")
    )
    status_evento_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("agenda.status_evento.id")
    )
    titulo: Mapped[str] = mapped_column(String(180))
    descricao: Mapped[str | None] = mapped_column(Text)
    data_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data_fim: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    local_nome: Mapped[str | None] = mapped_column(String(180))
    endereco_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cadastro.endereco.id")
    )
    codigo_municipio_ibge: Mapped[int | None] = mapped_column(Integer)
    bairro_id: Mapped[int | None] = mapped_column(Integer)
    zona_eleitoral_id: Mapped[int | None] = mapped_column(Integer)
    territorio_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("territorio.territorio.id")
    )
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    responsavel_pessoa_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id")
    )
    motivo_cancelamento: Mapped[str | None] = mapped_column(Text)
    cancelado_por: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("auth.usuario.id")
    )
    cancelado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    excluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EventoParticipante(Base):
    __tablename__ = "evento_participante"
    __table_args__ = {"schema": "agenda"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    evento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agenda.evento.id", ondelete="CASCADE")
    )
    pessoa_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id", ondelete="CASCADE")
    )
    papel: Mapped[str | None] = mapped_column(String(40))
    presente: Mapped[bool | None] = mapped_column(Boolean)
    observacao: Mapped[str | None] = mapped_column(String(255))


class EventoLideranca(Base):
    __tablename__ = "evento_lideranca"
    __table_args__ = {"schema": "agenda"}

    evento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agenda.evento.id", ondelete="CASCADE"), primary_key=True
    )
    lideranca_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cadastro.lideranca.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    papel: Mapped[str | None] = mapped_column(String(40))


class Convite(Base):
    __tablename__ = "convite"
    __table_args__ = {"schema": "agenda"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    evento_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agenda.evento.id", ondelete="CASCADE")
    )
    direcao: Mapped[str] = mapped_column(String(20))
    origem: Mapped[str | None] = mapped_column(String(120))
    pessoa_indicou_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id")
    )
    arquivo_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("arquivo.arquivo.id")
    )
    status: Mapped[str] = mapped_column(String(20))
    descricao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PautaEvento(Base):
    __tablename__ = "pauta_evento"
    __table_args__ = {"schema": "agenda"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    evento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agenda.evento.id", ondelete="CASCADE")
    )
    titulo: Mapped[str] = mapped_column(String(180))
    descricao: Mapped[str | None] = mapped_column(Text)
    encaminhamento: Mapped[str | None] = mapped_column(Text)
    ordem: Mapped[int | None] = mapped_column(SmallInteger)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PresencaEvento(Base):
    __tablename__ = "presenca_evento"
    __table_args__ = {"schema": "agenda"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    evento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agenda.evento.id", ondelete="CASCADE")
    )
    presenca_parlamentar: Mapped[bool] = mapped_column(Boolean)
    presenca_representante: Mapped[bool] = mapped_column(Boolean)
    nome_representante: Mapped[str | None] = mapped_column(String(180))
    numero_lideres_presentes: Mapped[int | None] = mapped_column(Integer)
    numero_convidados: Mapped[int | None] = mapped_column(Integer)
    numero_estimado_presentes: Mapped[int | None] = mapped_column(Integer)
    observacao: Mapped[str | None] = mapped_column(Text)
    registrado_por: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("auth.usuario.id")
    )
    registrado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LembreteEvento(Base):
    __tablename__ = "lembrete_evento"
    __table_args__ = {"schema": "agenda"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    evento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agenda.evento.id", ondelete="CASCADE")
    )
    usuario_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("auth.usuario.id", ondelete="CASCADE")
    )
    tipo: Mapped[str] = mapped_column(String(30))
    mensagem: Mapped[str] = mapped_column(String(255))
    agendado_para: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20))
    gerado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InsightEvento(Base):
    __tablename__ = "insight_evento"
    __table_args__ = {"schema": "agenda"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    evento_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agenda.evento.id", ondelete="CASCADE")
    )
    tipo: Mapped[str] = mapped_column(String(30))
    tema: Mapped[str] = mapped_column(String(120))
    frequencia: Mapped[int] = mapped_column(Integer)
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    detalhes: Mapped[dict[str, Any]] = mapped_column(JSONB)
    gerado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
