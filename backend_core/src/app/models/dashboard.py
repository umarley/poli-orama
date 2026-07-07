from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.tenants.models import Base


class Indicador(Base):
    __tablename__ = "indicador"
    __table_args__ = {"schema": "dw"}

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(60), unique=True)
    nome: Mapped[str] = mapped_column(String(150))
    descricao: Mapped[str | None] = mapped_column(String(255))
    unidade: Mapped[str | None] = mapped_column(String(30))


class IndicadorValor(Base):
    __tablename__ = "indicador_valor"
    __table_args__ = {"schema": "dw"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    indicador_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("dw.indicador.id"))
    data_referencia: Mapped[date] = mapped_column(Date)
    territorio_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("territorio.territorio.id")
    )
    lideranca_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cadastro.lideranca.id")
    )
    recorte: Mapped[dict[str, Any]] = mapped_column(JSONB)
    valor: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DashboardConfiguracao(Base):
    __tablename__ = "dashboard_configuracao"
    __table_args__ = {"schema": "dw"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    nome: Mapped[str] = mapped_column(String(120))
    perfil_acesso_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("auth.perfil_acesso.id")
    )
    filtros_padrao: Mapped[dict[str, Any]] = mapped_column(JSONB)
    widgets: Mapped[list[str]] = mapped_column(JSONB)
    criado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Relatorio(Base):
    __tablename__ = "relatorio"
    __table_args__ = {"schema": "dw"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    codigo: Mapped[str] = mapped_column(String(60))
    nome: Mapped[str] = mapped_column(String(150))
    descricao: Mapped[str | None] = mapped_column(String(255))
    tipo: Mapped[str | None] = mapped_column(String(30))
    formato_saida: Mapped[str | None] = mapped_column(String(20))
    parametros_definicao: Mapped[dict[str, Any]] = mapped_column(JSONB)
    automatico: Mapped[bool] = mapped_column(Boolean)
    agendamento_cron: Mapped[str | None] = mapped_column(String(60))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RelatorioExecucao(Base):
    __tablename__ = "relatorio_execucao"
    __table_args__ = {"schema": "dw"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    relatorio_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("dw.relatorio.id"))
    parametros: Mapped[dict[str, Any]] = mapped_column(JSONB)
    arquivo_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("arquivo.arquivo.id"))
    status: Mapped[str] = mapped_column(String(20))
    solicitado_por: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("auth.usuario.id")
    )
    iniciado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
