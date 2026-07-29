"""Modelos de importacao, staging, deduplicacao e processamento."""

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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.tenants.models import Base


class FonteDado(Base):
    __tablename__ = "fonte_dado"
    __table_args__ = {"schema": "etl"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    codigo: Mapped[str] = mapped_column(String(40))
    nome: Mapped[str] = mapped_column(String(120))
    tipo: Mapped[str] = mapped_column(String(30))
    descricao: Mapped[str | None] = mapped_column(String(255))
    ativo: Mapped[bool] = mapped_column(Boolean)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Importacao(Base):
    __tablename__ = "importacao"
    __table_args__ = {"schema": "etl"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    campanha_eleicao_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("eleicao.campanha_eleicao.id")
    )
    fonte_dado_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("etl.fonte_dado.id")
    )
    descricao: Mapped[str | None] = mapped_column(String(180))
    tipo_destino: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))
    parametros: Mapped[dict[str, Any]] = mapped_column(JSONB)
    mapeamento_colunas: Mapped[dict[str, Any]] = mapped_column(JSONB)
    total_linhas: Mapped[int | None] = mapped_column(Integer)
    linhas_validas: Mapped[int | None] = mapped_column(Integer)
    linhas_erro: Mapped[int | None] = mapped_column(Integer)
    linhas_duplicadas: Mapped[int] = mapped_column(Integer)
    linhas_pendentes: Mapped[int] = mapped_column(Integer)
    linhas_carregadas: Mapped[int] = mapped_column(Integer)
    criado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    aprovado_por: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("auth.usuario.id")
    )
    iniciado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ImportacaoArquivo(Base):
    __tablename__ = "importacao_arquivo"
    __table_args__ = {"schema": "etl"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    importacao_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("etl.importacao.id", ondelete="CASCADE")
    )
    arquivo_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("arquivo.arquivo.id")
    )
    nome_arquivo: Mapped[str | None] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ImportacaoLinha(Base):
    __tablename__ = "importacao_linha"
    __table_args__ = {"schema": "etl"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    importacao_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("etl.importacao.id", ondelete="CASCADE")
    )
    numero_linha: Mapped[int | None] = mapped_column(Integer)
    conteudo_bruto: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20))
    mensagem: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ErroImportacao(Base):
    __tablename__ = "erro_importacao"
    __table_args__ = {"schema": "etl"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    importacao_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("etl.importacao.id", ondelete="CASCADE")
    )
    importacao_linha_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("etl.importacao_linha.id", ondelete="CASCADE")
    )
    etapa: Mapped[str | None] = mapped_column(String(30))
    campo: Mapped[str | None] = mapped_column(String(80))
    valor: Mapped[str | None] = mapped_column(Text)
    mensagem: Mapped[str] = mapped_column(Text)
    severidade: Mapped[str] = mapped_column(String(10))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class StagingPessoa(Base):
    __tablename__ = "staging_pessoa"
    __table_args__ = {"schema": "etl"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    importacao_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("etl.importacao.id", ondelete="CASCADE")
    )
    importacao_linha_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("etl.importacao_linha.id", ondelete="CASCADE")
    )
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    nome_completo: Mapped[str | None] = mapped_column(String(180))
    cpf: Mapped[str | None] = mapped_column(String(20))
    rg: Mapped[str | None] = mapped_column(String(40))
    titulo_eleitor: Mapped[str | None] = mapped_column(String(20))
    data_nascimento: Mapped[date | None] = mapped_column(Date)
    telefone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(180))
    endereco: Mapped[str | None] = mapped_column(Text)
    logradouro: Mapped[str | None] = mapped_column(String(180))
    numero: Mapped[str | None] = mapped_column(String(20))
    complemento: Mapped[str | None] = mapped_column(String(120))
    bairro: Mapped[str | None] = mapped_column(String(150))
    municipio: Mapped[str | None] = mapped_column(String(120))
    uf: Mapped[str | None] = mapped_column(String(2))
    cep: Mapped[str | None] = mapped_column(String(9))
    dados_extras: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20))
    pessoa_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id")
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class JobProcessamento(Base):
    __tablename__ = "job_processamento"
    __table_args__ = {"schema": "etl"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    tipo: Mapped[str] = mapped_column(String(40))
    referencia: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20))
    parametros: Mapped[dict[str, Any]] = mapped_column(JSONB)
    tentativas: Mapped[int] = mapped_column(SmallInteger)
    iniciado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    concluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LogProcessamento(Base):
    __tablename__ = "log_processamento"
    __table_args__ = {"schema": "etl"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    job_processamento_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("etl.job_processamento.id", ondelete="CASCADE")
    )
    nivel: Mapped[str] = mapped_column(String(10))
    mensagem: Mapped[str] = mapped_column(Text)
    contexto: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RegraDeduplicacao(Base):
    __tablename__ = "regra_deduplicacao"
    __table_args__ = {"schema": "etl"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    nome: Mapped[str] = mapped_column(String(120))
    criterio: Mapped[str] = mapped_column(String(40))
    limiar_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    ativa: Mapped[bool] = mapped_column(Boolean)
    configuracao: Mapped[dict[str, Any]] = mapped_column(JSONB)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ResultadoDeduplicacao(Base):
    __tablename__ = "resultado_deduplicacao"
    __table_args__ = {"schema": "etl"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("public.tenant.id"))
    regra_deduplicacao_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("etl.regra_deduplicacao.id")
    )
    importacao_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("etl.importacao.id")
    )
    staging_pessoa_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("etl.staging_pessoa.id")
    )
    pessoa_candidata_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id")
    )
    registro_origem_id: Mapped[int | None] = mapped_column(BigInteger)
    registro_duplicado_id: Mapped[int | None] = mapped_column(BigInteger)
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    decisao: Mapped[str] = mapped_column(String(20))
    detalhes: Mapped[dict[str, Any]] = mapped_column(JSONB)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
