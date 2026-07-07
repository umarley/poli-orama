"""Modelos ORM para referencias globais usadas pela aplicacao."""

from sqlalchemy import Boolean, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.tenants.models import Base


class CategoriaDataComemorativa(Base):
    __tablename__ = "categoria_data_comemorativa"
    __table_args__ = {"schema": "global"}

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255))


class DataComemorativa(Base):
    __tablename__ = "data_comemorativa"
    __table_args__ = {"schema": "global"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    categoria_id: Mapped[int | None] = mapped_column(SmallInteger)
    nome: Mapped[str] = mapped_column(String(180), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text)
    dia: Mapped[int | None] = mapped_column(SmallInteger)
    mes: Mapped[int | None] = mapped_column(SmallInteger)
    data_movel: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    ambito: Mapped[str] = mapped_column(String(20), nullable=False, server_default="nacional")
    codigo_uf_ibge: Mapped[int | None] = mapped_column(Integer)
    codigo_municipio_ibge: Mapped[int | None] = mapped_column(Integer)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
