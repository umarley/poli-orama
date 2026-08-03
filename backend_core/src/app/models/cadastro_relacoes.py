"""Modelos de classificacao, vinculos e qualidade do cadastro."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.tenants.models import Base


class PessoaRedeSocial(Base):
    __tablename__ = "pessoa_rede_social"
    __table_args__ = (
        CheckConstraint(
            "rede IN ('instagram','facebook','tiktok','x','youtube','linkedin','outro')",
            name="ck_pessoa_rede_social_rede",
        ),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    pessoa_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"), nullable=False
    )
    rede: Mapped[str] = mapped_column(String(30), nullable=False)
    usuario_perfil: Mapped[str | None] = mapped_column(String(120))
    url: Mapped[str | None] = mapped_column(Text)
    seguidores: Mapped[int | None] = mapped_column(Integer)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PessoaTipo(Base):
    __tablename__ = "pessoa_tipo"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_pessoa_tipo_codigo"),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(SmallInteger, Identity(always=True), primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255))


class PessoaPessoaTipo(Base):
    __tablename__ = "pessoa_pessoa_tipo"
    __table_args__ = {"schema": "cadastro"}

    pessoa_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"),
        primary_key=True,
    )
    pessoa_tipo_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("cadastro.pessoa_tipo.id"), primary_key=True
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class HierarquiaLideranca(Base):
    __tablename__ = "hierarquia_lideranca"
    __table_args__ = (
        CheckConstraint(
            "papel_subordinado IN ('lider','liderado','apoiador','eleitor')",
            name="ck_hierarquia_papel",
        ),
        UniqueConstraint(
            "lideranca_superior_id",
            "pessoa_subordinada_id",
            "data_inicio",
            name="uq_hierarquia_lideranca",
        ),
        Index("ix_hierarquia_pessoa_sub", "pessoa_subordinada_id"),
        Index(
            "ix_hierarquia_campanha_lideranca",
            "tenant_id",
            "campanha_eleicao_id",
            "lideranca_superior_id",
        ),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    campanha_eleicao_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("eleicao.campanha_eleicao.id", ondelete="RESTRICT"),
    )
    lideranca_superior_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cadastro.lideranca.id", ondelete="CASCADE"), nullable=False
    )
    pessoa_subordinada_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"), nullable=False
    )
    papel_subordinado: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="liderado"
    )
    data_inicio: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    data_fim: Mapped[date | None] = mapped_column(Date)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    origem: Mapped[str] = mapped_column(String(30), nullable=False, server_default="manual")
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Indicacao(Base):
    __tablename__ = "indicacao"
    __table_args__ = {"schema": "cadastro"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    pessoa_indicada_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"), nullable=False
    )
    pessoa_indicante_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id", ondelete="SET NULL")
    )
    origem: Mapped[str | None] = mapped_column(String(60))
    contexto: Mapped[str | None] = mapped_column(String(255))
    data_indicacao: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class RelacionamentoPessoa(Base):
    __tablename__ = "relacionamento_pessoa"
    __table_args__ = (
        CheckConstraint(
            "tipo_relacao IN "
            "('familiar','lideranca','amizade','apoio_politico',"
            "'contato_institucional','comunitario','outro')",
            name="ck_relacionamento_tipo",
        ),
        CheckConstraint("pessoa_origem_id <> pessoa_destino_id", name="ck_relacionamento_distinto"),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    pessoa_origem_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"), nullable=False
    )
    pessoa_destino_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"), nullable=False
    )
    tipo_relacao: Mapped[str] = mapped_column(String(40), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class NucleoFamiliar(Base):
    __tablename__ = "nucleo_familiar"
    __table_args__ = {"schema": "cadastro"}

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    nome: Mapped[str | None] = mapped_column(String(150))
    pessoa_referencia_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id", ondelete="SET NULL")
    )
    endereco_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("cadastro.endereco.id"))
    quantidade_membros: Mapped[int | None] = mapped_column(SmallInteger)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PessoaNucleoFamiliar(Base):
    __tablename__ = "pessoa_nucleo_familiar"
    __table_args__ = (
        UniqueConstraint("pessoa_id", "nucleo_familiar_id", name="uq_pessoa_nucleo"),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    pessoa_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"), nullable=False
    )
    nucleo_familiar_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cadastro.nucleo_familiar.id", ondelete="CASCADE"),
        nullable=False,
    )
    parentesco: Mapped[str | None] = mapped_column(String(40))
    responsavel: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    observacao: Mapped[str | None] = mapped_column(String(255))


class Comunidade(Base):
    __tablename__ = "comunidade"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('religiosa','profissional','territorial','politica','social',"
            "'esportiva','cultural','outra')",
            name="ck_comunidade_tipo",
        ),
        UniqueConstraint("tenant_id", "nome", name="uq_comunidade_nome"),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    tipo: Mapped[str | None] = mapped_column(String(40))
    descricao: Mapped[str | None] = mapped_column(Text)
    lider_responsavel_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cadastro.lideranca.id")
    )
    codigo_municipio_ibge: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("global.municipio.codigo_ibge"),
    )
    territorio_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("territorio.territorio.id", ondelete="SET NULL")
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PessoaComunidade(Base):
    __tablename__ = "pessoa_comunidade"
    __table_args__ = {"schema": "cadastro"}

    pessoa_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"),
        primary_key=True,
    )
    comunidade_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cadastro.comunidade.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    papel: Mapped[str | None] = mapped_column(String(40))
    desde: Mapped[date | None] = mapped_column(Date, server_default=func.current_date())


class Tag(Base):
    __tablename__ = "tag"
    __table_args__ = (
        UniqueConstraint("tenant_id", "nome", name="uq_tag_nome"),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    nome: Mapped[str] = mapped_column(String(80), nullable=False)
    cor: Mapped[str | None] = mapped_column(String(9))
    categoria: Mapped[str | None] = mapped_column(String(40))
    descricao: Mapped[str | None] = mapped_column(String(255))
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PessoaTag(Base):
    __tablename__ = "pessoa_tag"
    __table_args__ = {"schema": "cadastro"}

    pessoa_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cadastro.tag.id", ondelete="CASCADE"), primary_key=True
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    atribuido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PessoaComplementoPolitico(Base):
    __tablename__ = "pessoa_complemento_politico"
    __table_args__ = (
        CheckConstraint(
            "nivel_engajamento BETWEEN 0 AND 10",
            name="ck_complemento_nivel_engajamento",
        ),
        UniqueConstraint("pessoa_id", name="uq_complemento_politico_pessoa"),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    pessoa_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"), nullable=False
    )
    vinculo_politico: Mapped[str | None] = mapped_column(String(120))
    partido_id: Mapped[int | None] = mapped_column(SmallInteger, ForeignKey("cadastro.partido.id"))
    cargo_funcao: Mapped[str | None] = mapped_column(String(120))
    temas_interesse: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default="[]")
    nivel_engajamento: Mapped[int | None] = mapped_column(SmallInteger)
    observacoes: Mapped[str | None] = mapped_column(Text)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ValidacaoCadastro(Base):
    __tablename__ = "validacao_cadastro"
    __table_args__ = (
        CheckConstraint(
            "motivo IN "
            "('incompleto','duplicado','sem_lider','dados_invalidos',"
            "'revisao_periodica','outro')",
            name="ck_validacao_motivo",
        ),
        CheckConstraint(
            "status IN ('pendente','aprovado','rejeitado','em_revisao')",
            name="ck_validacao_status",
        ),
        Index("ix_validacao_cadastro_status", "tenant_id", "status"),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    pessoa_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"), nullable=False
    )
    motivo: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pendente")
    observacao: Mapped[str | None] = mapped_column(Text)
    revisado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    revisado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SuspeitaDuplicidade(Base):
    __tablename__ = "suspeita_duplicidade"
    __table_args__ = (
        CheckConstraint(
            "criterio IN "
            "('cpf','telefone','email','titulo_eleitor','nome_data_nascimento','fuzzy')",
            name="ck_suspeita_criterio",
        ),
        CheckConstraint(
            "score_similaridade BETWEEN 0 AND 100",
            name="ck_suspeita_score",
        ),
        CheckConstraint(
            "status IN ('pendente','confirmada','descartada','mesclada')",
            name="ck_suspeita_status",
        ),
        CheckConstraint("pessoa_id <> pessoa_duplicada_id", name="ck_duplicidade_distinta"),
        Index("ix_suspeita_duplicidade_status", "tenant_id", "status"),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    pessoa_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"), nullable=False
    )
    pessoa_duplicada_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id", ondelete="CASCADE"), nullable=False
    )
    criterio: Mapped[str] = mapped_column(String(40), nullable=False)
    score_similaridade: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pendente")
    resolvido_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    resolvido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PessoaMerge(Base):
    __tablename__ = "pessoa_merge"
    __table_args__ = (
        CheckConstraint(
            "pessoa_principal_id <> pessoa_origem_id",
            name="ck_pessoa_merge_distinta",
        ),
        UniqueConstraint("tenant_id", "pessoa_origem_id", name="uq_pessoa_merge_origem"),
        Index(
            "ix_pessoa_merge_principal",
            "tenant_id",
            "pessoa_principal_id",
            "executado_em",
        ),
        {"schema": "cadastro"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("public.tenant.id", ondelete="CASCADE"), nullable=False
    )
    pessoa_principal_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id"), nullable=False
    )
    pessoa_origem_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cadastro.pessoa.id"), nullable=False
    )
    suspeita_duplicidade_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cadastro.suspeita_duplicidade.id")
    )
    campos_origem: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    snapshot_principal: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    snapshot_origem: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    resumo_operacao: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    executado_por: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("auth.usuario.id"))
    executado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
