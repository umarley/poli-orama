from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.cadastro import PessoaContatoResponse

AttendanceStatus = Literal[
    "em_atendimento",
    "concluido",
    "sem_resposta",
    "numero_invalido",
    "interrompido",
]
VoteIntention = Literal["votara", "nao_votara", "indeciso", "nao_respondeu"]
AttendanceResult = Literal[
    "tentativa_sem_resposta",
    "retorno_agendado",
    "indeciso",
    "confirmado",
    "nao_apoia",
    "numero_invalido",
    "contato_invalido",
    "concluido",
    "interrompido",
]
Sexo = Literal["M", "F", "O", "N"]


class CommunicationChannel(BaseModel):
    id: int
    codigo: str
    nome: str
    descricao: str | None = None


class RejectionReason(BaseModel):
    id: int
    codigo: str
    nome: str
    descricao: str | None = None


class AttendancePersonUpdate(BaseModel):
    nome_completo: str | None = Field(default=None, min_length=2, max_length=180)
    data_nascimento: date | None = None
    sexo: Sexo | None = None
    titulo_eleitor: str | None = Field(default=None, max_length=20)
    codigo_municipio_ibge: int | None = Field(default=None, ge=1)
    zona_eleitoral_id: int | None = Field(default=None, ge=1)
    secao_eleitoral_id: int | None = Field(default=None, ge=1)
    local_votacao_id: int | None = Field(default=None, ge=1)


class AttendanceUpdate(BaseModel):
    canal: int | None = Field(default=None, ge=1)
    canal_outro: str | None = Field(default=None, max_length=80)
    observacao: str | None = Field(default=None, max_length=5000)
    intencao_voto: VoteIntention | None = None
    motivo_rejeicao_id: int | None = Field(default=None, ge=1)
    motivo_observacao: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_vote(self) -> "AttendanceUpdate":
        if self.intencao_voto == "nao_votara" and self.motivo_rejeicao_id is None:
            raise ValueError("Informe o motivo da intencao negativa.")
        return self


class AttendanceClose(BaseModel):
    situacao: Literal["concluido", "sem_resposta", "numero_invalido", "interrompido"]
    canal: int = Field(ge=1)
    canal_outro: str | None = Field(default=None, max_length=80)
    intencao_voto: VoteIntention
    motivo_rejeicao_id: int | None = Field(default=None, ge=1)
    motivo_observacao: str | None = Field(default=None, max_length=2000)
    observacao: str | None = Field(default=None, max_length=5000)
    motivo_encerramento: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_required(self) -> "AttendanceClose":
        if self.intencao_voto == "nao_votara" and self.motivo_rejeicao_id is None:
            raise ValueError("Informe o motivo da intencao negativa.")
        if self.situacao in {"interrompido", "numero_invalido"} and not (
            self.motivo_encerramento or ""
        ).strip():
            raise ValueError("Informe o motivo do encerramento.")
        return self


class AttendanceInvalidate(BaseModel):
    motivo_inativacao: str = Field(min_length=5, max_length=2000)


class AttendanceDocumentInput(BaseModel):
    tipo_documento: Literal["cpf", "rg", "titulo_eleitor", "cnh", "passaporte", "outro"]
    numero: str = Field(min_length=1, max_length=40)
    orgao_emissor: str | None = Field(default=None, max_length=40)
    uf_emissor: str | None = Field(default=None, min_length=2, max_length=2)


class AttendanceInteractionInput(BaseModel):
    assunto: str | None = Field(default=None, max_length=180)
    conteudo: str = Field(min_length=2, max_length=5000)
    resultado: str | None = Field(default=None, max_length=120)


class AttendancePerson(BaseModel):
    id: int
    nome_completo: str
    nome_social: str | None = None
    apelido: str | None = None
    sexo: str | None = None
    data_nascimento: date | None = None
    observacoes: str | None = None
    telefone: str | None = None
    email: str | None = None
    contatos: list[PessoaContatoResponse] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    frentes: list[str] = Field(default_factory=list)
    nucleos_familiares: list[str] = Field(default_factory=list)
    titulo_eleitor: str | None = None
    codigo_municipio_ibge: int | None = None
    zona_eleitoral_id: int | None = None
    zona_eleitoral: str | None = None
    secao_eleitoral_id: int | None = None
    secao_eleitoral: str | None = None
    local_votacao_id: int | None = None
    local_votacao: str | None = None


class VoteIntentionHistoryItem(BaseModel):
    id: int
    intencao_voto: VoteIntention
    motivo_rejeicao_nome: str | None = None
    motivo_observacao: str | None = None
    criado_em: datetime
    registrado_por_nome: str | None = None


class AttendanceInteraction(BaseModel):
    id: int
    assunto: str | None = None
    conteudo: str | None = None
    resultado: str | None = None
    data_interacao: datetime
    registrado_por_nome: str | None = None


class AttendanceQueueItem(BaseModel):
    id: int
    situacao: AttendanceStatus
    iniciado_em: datetime
    nome_completo: str
    whatsapp: str | None = None
    ultima_interacao_em: datetime | None = None
    ultima_mensagem: str | None = None
    ultima_direcao: Literal["entrada", "saida"] | None = None
    mensagens_nao_lidas: int = 0


class AttendanceQueue(BaseModel):
    itens: list[AttendanceQueueItem] = Field(default_factory=list)
    total: int = 0
    limite: int = 10


class AttendanceResponse(BaseModel):
    id: int
    tenant_id: int
    campanha_eleicao_id: int
    pessoa_id: int
    atendente_usuario_id: int
    atendente_nome: str | None = None
    canal: int
    canal_codigo: str | None = None
    canal_nome: str | None = None
    canal_outro: str | None = None
    situacao: AttendanceStatus
    resultado: str | None = None
    intencao_voto: VoteIntention | None = None
    motivo_rejeicao_id: int | None = None
    motivo_rejeicao_nome: str | None = None
    motivo_observacao: str | None = None
    observacao: str | None = None
    motivo_encerramento: str | None = None
    motivo_inativacao: str | None = None
    iniciado_em: datetime
    finalizado_em: datetime | None = None
    pessoa: AttendancePerson
    interacoes: list[AttendanceInteraction] = Field(default_factory=list)
    historico_intencao: list[VoteIntentionHistoryItem] = Field(default_factory=list)


class IndicatorFilters(BaseModel):
    inicio: datetime | None = None
    fim: datetime | None = None
    atendente_usuario_id: int | None = Field(default=None, ge=1)
    canal: int | None = Field(default=None, ge=1)
    situacao: AttendanceStatus | None = None
    resultado: AttendanceResult | None = None


class RejectionCount(BaseModel):
    motivo: str
    quantidade: int


class OperatorCount(BaseModel):
    atendente_usuario_id: int
    atendente_nome: str
    quantidade: int


class ChannelCount(BaseModel):
    canal_id: int
    canal: str
    quantidade: int


class PeriodCount(BaseModel):
    periodo: date
    quantidade: int


class AttendanceIndicators(BaseModel):
    total_atendimentos: int
    concluidos: int
    sem_resposta: int
    votos_confirmados: int
    indecisos: int
    respostas_negativas: int
    tempo_medio_minutos: float
    percentual_conversao: float
    por_periodo: list[PeriodCount]
    por_telefonista: list[OperatorCount]
    por_canal: list[ChannelCount]
    principais_motivos_rejeicao: list[RejectionCount]
