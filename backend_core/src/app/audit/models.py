from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.tenants.models import Base


class AuditLog(Base):
    __tablename__ = "log_auditoria"
    __table_args__ = {"schema": "auditoria"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    usuario_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    acao: Mapped[str] = mapped_column(String(20))
    schema_nome: Mapped[str | None] = mapped_column(String(40))
    tabela: Mapped[str | None] = mapped_column(String(80))
    registro_id: Mapped[int | None] = mapped_column(BigInteger)
    dados_anteriores: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    dados_novos: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ip_origem: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExportLog(Base):
    __tablename__ = "log_exportacao"
    __table_args__ = {"schema": "auditoria"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    usuario_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    entidade: Mapped[str | None] = mapped_column(String(80))
    filtros: Mapped[dict[str, Any]] = mapped_column(JSONB)
    volume_registros: Mapped[int | None] = mapped_column(Integer)
    formato: Mapped[str | None] = mapped_column(String(20))
    finalidade: Mapped[str | None] = mapped_column(String(255))
    arquivo_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("arquivo.arquivo.id"))
    ip_origem: Mapped[str | None] = mapped_column(INET)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
