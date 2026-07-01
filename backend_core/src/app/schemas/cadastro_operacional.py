"""Contratos operacionais para vinculos, segmentacao e qualidade cadastral."""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from app.schemas.cadastro import (
    CadastroSchema,
    EleitorCreate,
    LiderancaCreate,
    LiderancaResponse,
    PessoaBase,
    PessoaContatoCreate,
    PessoaDocumentoCreate,
    PessoaEnderecoCreate,
    PessoaResponse,
)

RedeSocial = Literal["instagram", "facebook", "tiktok", "x", "youtube", "linkedin", "outro"]
PapelSubordinado = Literal["lider", "liderado", "apoiador", "eleitor"]
TipoRelacao = Literal[
    "familiar",
    "lideranca",
    "amizade",
    "apoio_politico",
    "contato_institucional",
    "comunitario",
    "outro",
]
TipoComunidade = Literal[
    "religiosa",
    "profissional",
    "territorial",
    "politica",
    "social",
    "esportiva",
    "cultural",
    "outra",
]
MotivoValidacao = Literal[
    "incompleto", "duplicado", "sem_lider", "dados_invalidos", "revisao_periodica", "outro"
]
StatusValidacao = Literal["pendente", "aprovado", "rejeitado", "em_revisao"]
CriterioDuplicidade = Literal[
    "cpf", "telefone", "email", "titulo_eleitor", "nome_data_nascimento", "fuzzy"
]
StatusDuplicidade = Literal["pendente", "confirmada", "descartada", "mesclada"]


class PessoaRedeSocialInput(CadastroSchema):
    rede: RedeSocial
    usuario_perfil: str | None = Field(default=None, max_length=120)
    url: str | None = Field(default=None, max_length=2048)
    seguidores: int | None = Field(default=None, ge=0)


class PessoaRedeSocialResponse(PessoaRedeSocialInput):
    id: int
    tenant_id: int
    pessoa_id: int
    criado_em: datetime


class PessoaTipoResponse(CadastroSchema):
    id: int
    codigo: str
    nome: str
    descricao: str | None


class LiderancaOperacionalResponse(LiderancaResponse):
    territorio_ids: list[int] = Field(default_factory=list)


class IndicacaoInput(CadastroSchema):
    pessoa_indicante_id: int | None = Field(default=None, ge=1)
    origem: str | None = Field(default=None, max_length=60)
    contexto: str | None = Field(default=None, max_length=255)
    data_indicacao: date = Field(default_factory=date.today)


class IndicacaoResponse(IndicacaoInput):
    id: int
    tenant_id: int
    pessoa_indicada_id: int
    criado_em: datetime


class ComplementoPoliticoInput(CadastroSchema):
    vinculo_politico: str | None = Field(default=None, max_length=120)
    partido_id: int | None = Field(default=None, ge=1)
    cargo_funcao: str | None = Field(default=None, max_length=120)
    temas_interesse: list[str] = Field(default_factory=list, max_length=100)
    nivel_engajamento: int | None = Field(default=None, ge=0, le=10)
    observacoes: str | None = None


class ComplementoPoliticoResponse(ComplementoPoliticoInput):
    id: int
    tenant_id: int
    pessoa_id: int
    atualizado_em: datetime


class PessoaCadastroCreate(PessoaBase):
    documentos: list[PessoaDocumentoCreate] = Field(default_factory=list, max_length=20)
    contatos: list[PessoaContatoCreate] = Field(default_factory=list, max_length=50)
    enderecos: list[PessoaEnderecoCreate] = Field(default_factory=list, max_length=20)
    redes_sociais: list[PessoaRedeSocialInput] = Field(default_factory=list, max_length=20)
    tipo_ids: list[int] = Field(default_factory=list, max_length=20)
    eleitor: EleitorCreate | None = None
    lideranca: LiderancaCreate | None = None
    lideranca_superior_id: int | None = Field(default=None, ge=1)
    papel_subordinado: PapelSubordinado = "liderado"
    indicacao: IndicacaoInput | None = None
    complemento_politico: ComplementoPoliticoInput | None = None

    @model_validator(mode="after")
    def validate_unique_collections(self) -> "PessoaCadastroCreate":
        document_keys = [(item.tipo_documento, item.numero) for item in self.documentos]
        if len(document_keys) != len(set(document_keys)):
            raise ValueError("A lista contem documentos duplicados.")
        if len(self.tipo_ids) != len(set(self.tipo_ids)):
            raise ValueError("A lista contem tipos de pessoa duplicados.")
        return self


class PessoaDetalheResponse(PessoaResponse):
    redes_sociais: list[PessoaRedeSocialResponse] = Field(default_factory=list)
    tipos: list[PessoaTipoResponse] = Field(default_factory=list)
    indicacoes: list[IndicacaoResponse] = Field(default_factory=list)
    complemento_politico: ComplementoPoliticoResponse | None = None
    tags: list["VinculoResumo"] = Field(default_factory=list)
    comunidades: list["VinculoResumo"] = Field(default_factory=list)
    nucleos_familiares: list["VinculoResumo"] = Field(default_factory=list)
    hierarquia: list["HierarquiaResumo"] = Field(default_factory=list)


class VinculoResumo(CadastroSchema):
    id: int
    nome: str


class HierarquiaResumo(CadastroSchema):
    id: int
    lideranca_superior_id: int
    papel_subordinado: PapelSubordinado
    ativo: bool


class PessoaListItem(CadastroSchema):
    id: int
    nome_completo: str
    nome_social: str | None
    apelido: str | None
    data_nascimento: date | None
    ativo: bool
    cpf: str | None = None
    telefone: str | None = None
    tipos: list[str] = Field(default_factory=list)
    lideranca_id: int | None = None


class PessoaFiltros(CadastroSchema):
    nome: str | None = Field(default=None, max_length=180)
    cpf: str | None = Field(default=None, max_length=14)
    telefone: str | None = Field(default=None, max_length=20)
    tipo_id: int | None = Field(default=None, ge=1)
    lideranca_id: int | None = Field(default=None, ge=1)
    territorio_id: int | None = Field(default=None, ge=1)
    tag_id: int | None = Field(default=None, ge=1)
    incluir_inativos: bool = False

    @field_validator("cpf", "telefone")
    @classmethod
    def normalize_numeric_filter(cls, value: str | None) -> str | None:
        return re.sub(r"\D", "", value) if value else value


class HierarquiaInput(CadastroSchema):
    lideranca_superior_id: int = Field(ge=1)
    pessoa_subordinada_id: int = Field(ge=1)
    papel_subordinado: PapelSubordinado = "liderado"
    data_inicio: date = Field(default_factory=date.today)
    data_fim: date | None = None
    ativo: bool = True

    @model_validator(mode="after")
    def validate_dates(self) -> "HierarquiaInput":
        if self.data_fim is not None and self.data_fim < self.data_inicio:
            raise ValueError("data_fim nao pode ser anterior a data_inicio.")
        return self


class HierarquiaResponse(HierarquiaInput):
    id: int
    tenant_id: int
    criado_em: datetime


class RelacionamentoInput(CadastroSchema):
    pessoa_destino_id: int = Field(ge=1)
    tipo_relacao: TipoRelacao
    descricao: str | None = Field(default=None, max_length=255)


class RelacionamentoResponse(RelacionamentoInput):
    id: int
    tenant_id: int
    pessoa_origem_id: int
    criado_em: datetime


class NucleoFamiliarInput(CadastroSchema):
    nome: str | None = Field(default=None, max_length=150)
    pessoa_referencia_id: int | None = Field(default=None, ge=1)
    endereco_id: int | None = Field(default=None, ge=1)


class NucleoFamiliarResponse(NucleoFamiliarInput):
    id: int
    tenant_id: int
    quantidade_membros: int | None
    criado_em: datetime
    atualizado_em: datetime


class VinculoNucleoInput(CadastroSchema):
    pessoa_id: int = Field(ge=1)
    parentesco: str | None = Field(default=None, max_length=40)
    responsavel: bool = False
    observacao: str | None = Field(default=None, max_length=255)


class VinculoNucleoResponse(VinculoNucleoInput):
    id: int
    tenant_id: int
    nucleo_familiar_id: int


class ComunidadeInput(CadastroSchema):
    nome: str = Field(min_length=2, max_length=150)
    tipo: TipoComunidade | None = None
    descricao: str | None = None
    lider_responsavel_id: int | None = Field(default=None, ge=1)
    municipio_id: int | None = Field(default=None, ge=1)
    territorio_id: int | None = Field(default=None, ge=1)


class ComunidadeResponse(ComunidadeInput):
    id: int
    tenant_id: int
    criado_em: datetime
    atualizado_em: datetime


class VinculoComunidadeInput(CadastroSchema):
    pessoa_id: int = Field(ge=1)
    papel: str | None = Field(default=None, max_length=40)
    desde: date = Field(default_factory=date.today)


class TagInput(CadastroSchema):
    nome: str = Field(min_length=1, max_length=80)
    cor: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?$")
    categoria: str | None = Field(default=None, max_length=40)
    descricao: str | None = Field(default=None, max_length=255)


class TagResponse(TagInput):
    id: int
    tenant_id: int
    ativo: bool
    criado_em: datetime


class TagUpdate(CadastroSchema):
    nome: str | None = Field(default=None, min_length=1, max_length=80)
    cor: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?$")
    categoria: str | None = Field(default=None, max_length=40)
    descricao: str | None = Field(default=None, max_length=255)
    ativo: bool | None = None


class VinculoTagInput(CadastroSchema):
    pessoa_id: int = Field(ge=1)


class ValidacaoInput(CadastroSchema):
    motivo: MotivoValidacao
    observacao: str | None = None


class ValidacaoResolve(CadastroSchema):
    status: Literal["aprovado", "rejeitado", "em_revisao"]
    observacao: str | None = None


class ValidacaoResponse(ValidacaoInput):
    id: int
    tenant_id: int
    pessoa_id: int
    status: StatusValidacao
    revisado_por: int | None
    revisado_em: datetime | None
    criado_em: datetime


class SuspeitaDuplicidadeResponse(CadastroSchema):
    id: int
    tenant_id: int
    pessoa_id: int
    pessoa_duplicada_id: int
    criterio: CriterioDuplicidade
    score_similaridade: Decimal | None
    status: StatusDuplicidade
    resolvido_por: int | None
    resolvido_em: datetime | None
    criado_em: datetime


class SuspeitaDuplicidadeResolve(CadastroSchema):
    decisao: Literal["duplicado", "falso_positivo", "pendente"]


class BuscaRapidaItem(CadastroSchema):
    id: int
    nome_completo: str
    data_nascimento: date | None
    documento: str | None = None
    telefone: str | None = None


class IndicacaoGraphNode(CadastroSchema):
    id: int
    nome: str
    ativo: bool


class IndicacaoGraphEdge(CadastroSchema):
    id: int
    origem_id: int
    destino_id: int
    origem: str | None
    contexto: str | None
    data_indicacao: date


class IndicacaoGraphResponse(CadastroSchema):
    nodes: list[IndicacaoGraphNode]
    edges: list[IndicacaoGraphEdge]
    total_edges: int
    truncated: bool


MergePessoaCampo = Literal[
    "nome_completo",
    "nome_social",
    "apelido",
    "sexo",
    "data_nascimento",
    "estado_civil",
    "escolaridade_id",
    "profissao_id",
    "religiao_id",
    "observacoes",
]


class PessoaMergeConflict(CadastroSchema):
    campo: MergePessoaCampo
    valor_principal: Any
    valor_origem: Any


class PessoaMergePreview(CadastroSchema):
    suspeita_id: int
    pessoa_a: PessoaDetalheResponse
    pessoa_b: PessoaDetalheResponse
    conflitos: list[PessoaMergeConflict]


class PessoaMergeRequest(CadastroSchema):
    pessoa_principal_id: int = Field(ge=1)
    campos_origem: list[MergePessoaCampo] = Field(default_factory=list)
    confirmar: Literal[True]


class PessoaMergeResponse(CadastroSchema):
    merge_id: int
    pessoa_principal: PessoaDetalheResponse
    pessoa_origem_id: int
    resumo_operacao: dict[str, int]
