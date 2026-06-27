from datetime import date, datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, Date, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenant"
    __table_args__ = {"schema": "public"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uuid_publico: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), unique=True)
    nome: Mapped[str] = mapped_column(String(180))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    documento: Mapped[str | None] = mapped_column(String(20))
    tem_mandato: Mapped[bool] = mapped_column(Boolean)
    plano_assinatura_id: Mapped[int | None] = mapped_column(BigInteger)
    data_inicio_contrato: Mapped[date | None] = mapped_column(Date)
    data_fim_contrato: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    excluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
