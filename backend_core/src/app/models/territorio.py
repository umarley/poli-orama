"""Modelos de referencias geograficas e territorios operacionais."""

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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import UserDefinedType

from app.tenants.models import Base


class Geography(UserDefinedType[Any]):
    cache_ok = True

    def __init__(self, geometry_type: str) -> None:
        self.geometry_type = geometry_type

    def get_col_spec(self, **kw: Any) -> str:
        return f"geography({self.geometry_type}, 4326)"


class Estado(Base):
    __tablename__ = "estado"
    __table_args__ = {"schema": "global"}

    id: Mapped[int] = mapped_column(SmallInteger, Identity(always=True), primary_key=True)
    codigo_ibge: Mapped[int] = mapped_column(SmallInteger)
    uf: Mapped[str] = mapped_column(String(2))
    nome: Mapped[str] = mapped_column(String(60))
    regiao: Mapped[str | None] = mapped_column(String(20))


class Municipio(Base):
    __tablename__ = "municipio"
    __table_args__ = {"schema": "global"}

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    estado_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("global.estado.id"))
    codigo_ibge: Mapped[int] = mapped_column(Integer)
    codigo_tse: Mapped[int | None] = mapped_column(Integer)
    nome: Mapped[str] = mapped_column(String(120))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    geom: Mapped[Any | None] = mapped_column(Geography("Point"))


class Bairro(Base):
    __tablename__ = "bairro"
    __table_args__ = {"schema": "global"}

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    municipio_id: Mapped[int] = mapped_column(Integer, ForeignKey("global.municipio.id"))
    nome: Mapped[str] = mapped_column(String(150))
    origem: Mapped[str] = mapped_column(String(20))


class ZonaEleitoral(Base):
    __tablename__ = "zona_eleitoral"
    __table_args__ = {"schema": "global"}

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    estado_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("global.estado.id"))
    municipio_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("global.municipio.id"))
    numero_zona: Mapped[int] = mapped_column(SmallInteger)
    descricao: Mapped[str | None] = mapped_column(String(150))


class LocalVotacao(Base):
    __tablename__ = "local_votacao"
    __table_args__ = {"schema": "global"}

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    municipio_id: Mapped[int] = mapped_column(Integer, ForeignKey("global.municipio.id"))
    zona_eleitoral_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("global.zona_eleitoral.id")
    )
    bairro_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("global.bairro.id"))
    codigo_local: Mapped[int | None] = mapped_column(Integer)
    nome: Mapped[str] = mapped_column(String(180))
    logradouro: Mapped[str | None] = mapped_column(String(180))
    numero: Mapped[str | None] = mapped_column(String(20))
    complemento: Mapped[str | None] = mapped_column(String(120))
    cep: Mapped[str | None] = mapped_column(String(9))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    geom: Mapped[Any | None] = mapped_column(Geography("Point"))
    situacao: Mapped[str] = mapped_column(String(20))


class SecaoEleitoral(Base):
    __tablename__ = "secao_eleitoral"
    __table_args__ = {"schema": "global"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    zona_eleitoral_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("global.zona_eleitoral.id")
    )
    local_votacao_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("global.local_votacao.id")
    )
    numero_secao: Mapped[int] = mapped_column(SmallInteger)
    agregada_em: Mapped[int | None] = mapped_column(SmallInteger)


class TipoTerritorio(Base):
    __tablename__ = "tipo_territorio"
    __table_args__ = {"schema": "territorio"}

    id: Mapped[int] = mapped_column(SmallInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE")
    )
    codigo: Mapped[str] = mapped_column(String(40))
    nome: Mapped[str] = mapped_column(String(80))
    descricao: Mapped[str | None] = mapped_column(String(255))
    ativo: Mapped[bool] = mapped_column(Boolean)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Territorio(Base):
    __tablename__ = "territorio"
    __table_args__ = {"schema": "territorio"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE")
    )
    tipo_territorio_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("territorio.tipo_territorio.id")
    )
    nome: Mapped[str] = mapped_column(String(150))
    estado_id: Mapped[int | None] = mapped_column(SmallInteger, ForeignKey("global.estado.id"))
    municipio_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("global.municipio.id"))
    bairro_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("global.bairro.id"))
    zona_eleitoral_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("global.zona_eleitoral.id")
    )
    secao_eleitoral_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("global.secao_eleitoral.id")
    )
    geom: Mapped[Any | None] = mapped_column(Geography("MultiPolygon"))
    ativo: Mapped[bool] = mapped_column(Boolean)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TerritorioHierarquia(Base):
    __tablename__ = "territorio_hierarquia"
    __table_args__ = (
        UniqueConstraint("territorio_pai_id", "territorio_filho_id"),
        {"schema": "territorio"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    territorio_pai_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("territorio.territorio.id", ondelete="CASCADE")
    )
    territorio_filho_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("territorio.territorio.id", ondelete="CASCADE")
    )


class PessoaTerritorio(Base):
    __tablename__ = "pessoa_territorio"
    __table_args__ = {"schema": "territorio"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    pessoa_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cadastro.pessoa.id"))
    territorio_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("territorio.territorio.id"))
    vinculo: Mapped[str] = mapped_column(String(20))


class LiderancaTerritorio(Base):
    __tablename__ = "lideranca_territorio"
    __table_args__ = {"schema": "territorio"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    lideranca_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cadastro.lideranca.id"))
    territorio_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("territorio.territorio.id"))
    responsabilidade: Mapped[str] = mapped_column(String(20))


class Geocodificacao(Base):
    __tablename__ = "geocodificacao"
    __table_args__ = {"schema": "territorio"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    entidade_tipo: Mapped[str] = mapped_column(String(30))
    entidade_id: Mapped[int] = mapped_column(BigInteger)
    endereco_texto: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    geom: Mapped[Any | None] = mapped_column(Geography("Point"))
    precisao: Mapped[str | None] = mapped_column(String(30))
    provedor: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))
    processado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
