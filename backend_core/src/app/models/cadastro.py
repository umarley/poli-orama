"""Modelos centrais do dominio de cadastro."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import UserDefinedType

from app.tenants.models import Base


class GeographyPoint(UserDefinedType[Any]):
    """Tipo PostGIS usado pelo schema legado sem exigir GeoAlchemy na API."""

    cache_ok = True

    def get_col_spec(self, **kw: Any) -> str:
        return "geography(Point, 4326)"


class EstadoCivil(Base):
    __tablename__ = "estado_civil"
    __table_args__ = {"schema": "cadastro"}

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    ordem: Mapped[int] = mapped_column(SmallInteger, nullable=False)


class Pessoa(Base):
    __tablename__ = "pessoa"
    __table_args__ = (
        CheckConstraint("sexo IN ('M','F','O','N')", name="ck_pessoa_sexo"),
        CheckConstraint(
            "nivel_engajamento BETWEEN 0 AND 10",
            name="ck_pessoa_nivel_engajamento",
        ),
        CheckConstraint(
            "score_confiabilidade BETWEEN 0 AND 100",
            name="ck_pessoa_score_confiabilidade",
        ),
        CheckConstraint(
            "completude_cadastral BETWEEN 0 AND 100",
            name="ck_pessoa_completude_cadastral",
        ),
        UniqueConstraint("uuid_publico", name="uq_pessoa_uuid"),
        Index("ix_pessoa_tenant", "tenant_id"),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    uuid_publico: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False, server_default=func.gen_random_uuid()
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("public.tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    nome_completo: Mapped[str] = mapped_column(String(180), nullable=False)
    nome_social: Mapped[str | None] = mapped_column(String(180))
    apelido: Mapped[str | None] = mapped_column(String(120))
    sexo: Mapped[str | None] = mapped_column(CHAR(1))
    data_nascimento: Mapped[date | None] = mapped_column(Date)
    estado_civil: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("cadastro.estado_civil.id", ondelete="SET NULL")
    )
    escolaridade_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("cadastro.escolaridade.id")
    )
    profissao_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("cadastro.profissao.id"))
    religiao_id: Mapped[int | None] = mapped_column(
        SmallInteger, ForeignKey("cadastro.religiao.id")
    )
    foto_arquivo_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("arquivo.arquivo.id", ondelete="SET NULL")
    )
    nivel_engajamento: Mapped[int | None] = mapped_column(SmallInteger)
    score_confiabilidade: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    completude_cadastral: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    fonte_dado_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("etl.fonte_dado.id", ondelete="SET NULL")
    )
    observacoes: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    criado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    atualizado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    excluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    documentos: Mapped[list["PessoaDocumento"]] = relationship(
        back_populates="pessoa", cascade="all, delete-orphan", lazy="selectin"
    )
    contatos: Mapped[list["PessoaContato"]] = relationship(
        back_populates="pessoa", cascade="all, delete-orphan", lazy="selectin"
    )
    enderecos: Mapped[list["PessoaEndereco"]] = relationship(
        back_populates="pessoa", cascade="all, delete-orphan", lazy="selectin"
    )
    eleitor: Mapped["Eleitor | None"] = relationship(
        back_populates="pessoa", cascade="all, delete-orphan", uselist=False, lazy="selectin"
    )
    lideranca: Mapped["Lideranca | None"] = relationship(
        back_populates="pessoa", cascade="all, delete-orphan", uselist=False, lazy="selectin"
    )


class PessoaDocumento(Base):
    __tablename__ = "pessoa_documento"
    __table_args__ = (
        CheckConstraint(
            "tipo_documento IN ('cpf','rg','titulo_eleitor','cnh','passaporte','outro')",
            name="ck_pessoa_documento_tipo",
        ),
        UniqueConstraint(
            "tenant_id",
            "tipo_documento",
            "numero",
            name="uq_pessoa_documento",
        ),
        Index("ix_pessoa_documento_pessoa", "pessoa_id"),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("public.tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    pessoa_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"),
        nullable=False,
    )
    tipo_documento: Mapped[str] = mapped_column(String(20), nullable=False)
    numero: Mapped[str] = mapped_column(String(40), nullable=False)
    orgao_emissor: Mapped[str | None] = mapped_column(String(40))
    uf_emissor: Mapped[str | None] = mapped_column(CHAR(2))
    data_emissao: Mapped[date | None] = mapped_column(Date)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    pessoa: Mapped[Pessoa] = relationship(back_populates="documentos")


class PessoaContato(Base):
    __tablename__ = "pessoa_contato"
    __table_args__ = (
        CheckConstraint(
            "tipo_contato IN ('telefone','celular','whatsapp','email','outro')",
            name="ck_pessoa_contato_tipo",
        ),
        Index("ix_pessoa_contato_pessoa", "pessoa_id"),
        Index("ix_pessoa_contato_valor", "tenant_id", "valor"),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("public.tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    pessoa_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"),
        nullable=False,
    )
    tipo_contato: Mapped[str] = mapped_column(String(20), nullable=False)
    valor: Mapped[str] = mapped_column(String(180), nullable=False)
    principal: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    verificado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    observacao: Mapped[str | None] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    pessoa: Mapped[Pessoa] = relationship(back_populates="contatos")


class Endereco(Base):
    __tablename__ = "endereco"
    __table_args__ = (
        Index("ix_endereco_geom", "geom", postgresql_using="gist"),
        Index("ix_endereco_municipio", "codigo_municipio_ibge"),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("public.tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    codigo_municipio_ibge: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("global.municipio.codigo_ibge")
    )
    bairro_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("global.bairro.id"))
    bairro_texto: Mapped[str | None] = mapped_column(String(150))
    logradouro: Mapped[str | None] = mapped_column(String(180))
    numero: Mapped[str | None] = mapped_column(String(20))
    complemento: Mapped[str | None] = mapped_column(String(120))
    cep: Mapped[str | None] = mapped_column(String(9))
    ponto_referencia: Mapped[str | None] = mapped_column(String(180))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    geom: Mapped[Any | None] = mapped_column(GeographyPoint())
    geocodificado: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    pessoas: Mapped[list["PessoaEndereco"]] = relationship(
        back_populates="endereco", cascade="all, delete-orphan"
    )


class PessoaEndereco(Base):
    __tablename__ = "pessoa_endereco"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('residencial','eleitoral','comercial','temporario','outro')",
            name="ck_pessoa_endereco_tipo",
        ),
        UniqueConstraint("pessoa_id", "endereco_id", "tipo", name="uq_pessoa_endereco"),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("public.tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    pessoa_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"),
        nullable=False,
    )
    endereco_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cadastro.endereco.id", ondelete="CASCADE"),
        nullable=False,
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, server_default="residencial")
    principal: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    pessoa: Mapped[Pessoa] = relationship(back_populates="enderecos")
    endereco: Mapped[Endereco] = relationship(back_populates="pessoas", lazy="joined")


class Eleitor(Base):
    __tablename__ = "eleitor"
    __table_args__ = (
        CheckConstraint(
            "situacao_titulo IN ('regular','suspenso','cancelado','desconhecido')",
            name="ck_eleitor_situacao_titulo",
        ),
        UniqueConstraint("pessoa_id", name="uq_eleitor_pessoa"),
        Index("ix_eleitor_zona_secao", "tenant_id", "zona_eleitoral_id", "secao_eleitoral_id"),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("public.tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    pessoa_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"),
        nullable=False,
    )
    titulo_eleitor: Mapped[str | None] = mapped_column(String(20))
    zona_eleitoral_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("global.zona_eleitoral.id")
    )
    secao_eleitoral_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("global.secao_eleitoral.id")
    )
    local_votacao_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("global.local_votacao.id")
    )
    codigo_municipio_ibge: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("global.municipio.codigo_ibge")
    )
    situacao_titulo: Mapped[str | None] = mapped_column(String(30), server_default="regular")
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    pessoa: Mapped[Pessoa] = relationship(back_populates="eleitor")


class Lideranca(Base):
    __tablename__ = "lideranca"
    __table_args__ = (
        CheckConstraint(
            "tipo_lideranca IN ('coordenador_geral','coordenador_territorial','lider','sublider')",
            name="ck_lideranca_tipo",
        ),
        UniqueConstraint("pessoa_id", name="uq_lideranca_pessoa"),
        Index("ix_lideranca_coordenador", "coordenador_id"),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("public.tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    pessoa_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"),
        nullable=False,
    )
    tipo_lideranca: Mapped[str] = mapped_column(String(40), nullable=False, server_default="lider")
    coordenador_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cadastro.lideranca.id")
    )
    apelido_campanha: Mapped[str | None] = mapped_column(String(120))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    pessoa: Mapped[Pessoa] = relationship(back_populates="lideranca")
    coordenador: Mapped["Lideranca | None"] = relationship(
        back_populates="liderados", remote_side="Lideranca.id"
    )
    liderados: Mapped[list["Lideranca"]] = relationship(back_populates="coordenador")
