import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

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
    intencao_voto: VoteIntention | None = None
    motivo_rejeicao_id: int | None = Field(default=None, ge=1)
    motivo_observacao: str | None = Field(default=None, max_length=2000)
    observacao: str | None = Field(default=None, max_length=5000)
    motivo_encerramento: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_required(self) -> "AttendanceClose":
        if self.situacao != "concluido":
            self.intencao_voto = None
            self.motivo_rejeicao_id = None
            self.motivo_observacao = None
        elif self.intencao_voto is None:
            raise ValueError("Informe a intencao de voto.")
        elif self.intencao_voto == "nao_votara" and self.motivo_rejeicao_id is None:
            raise ValueError("Informe o motivo da intencao negativa.")
        if self.situacao in {"interrompido", "numero_invalido"} and not (
            self.motivo_encerramento or ""
        ).strip():
            raise ValueError("Informe o motivo do encerramento.")
        return self


class AttendanceInvalidate(BaseModel):
    motivo_inativacao: str = Field(min_length=5, max_length=2000)


class AttendanceManualCreate(BaseModel):
    nome_completo: str = Field(min_length=2, max_length=180)
    telefone: str = Field(min_length=8, max_length=20)
    email: str | None = Field(default=None, max_length=180)
    data_nascimento: date | None = None
    sexo: Sexo | None = None

    @field_validator("nome_completo")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Informe o nome completo.")
        return normalized

    @field_validator("telefone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if digits.startswith("55") and len(digits) in {12, 13}:
            digits = digits[2:]
        if len(digits) not in {10, 11}:
            raise ValueError("Telefone invalido; informe DDD e numero.")
        return digits

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("E-mail invalido.")
        return normalized


class AttendanceSearchFilters(BaseModel):
    nome: str | None = Field(default=None, max_length=180)
    telefone: str | None = Field(default=None, max_length=32)

    @field_validator("nome")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None

    @field_validator("telefone")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        digits = re.sub(r"\D", "", value)
        if digits.startswith("55") and len(digits) in {12, 13}:
            digits = digits[2:]
        return digits or None

    @model_validator(mode="after")
    def require_criteria(self) -> "AttendanceSearchFilters":
        name_ok = len(self.nome or "") >= 2
        phone_ok = len(self.telefone or "") >= 8
        if not name_ok and not phone_ok:
            raise ValueError("Informe o nome ou o telefone para buscar o atendimento.")
        return self


class AttendanceSearchItem(BaseModel):
    id: int
    pessoa_id: int
    nome_completo: str
    telefone: str | None = None
    situacao: AttendanceStatus
    iniciado_em: datetime
    finalizado_em: datetime | None = None
    atendente_usuario_id: int
    atendente_nome: str | None = None
    pode_abrir: bool = False
    pode_retomar: bool = False
    bloqueio: str | None = None


class AttendanceSearchResult(BaseModel):
    itens: list[AttendanceSearchItem] = Field(default_factory=list)


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
    motivo_rejeicao_id: int | None = None
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


class AttendanceReportFilters(BaseModel):
    inicio: datetime | None = None
    fim: datetime | None = None
    atendente_usuario_id: int = Field(ge=1)
    pagina: int = Field(default=1, ge=1)
    tamanho: int = Field(default=20, ge=1, le=100)


class AttendanceReportItem(BaseModel):
    id: int
    pessoa_id: int
    nome_completo: str
    telefone: str | None = None
    email: str | None = None
    data_nascimento: date | None = None
    sexo: str | None = None
    iniciado_em: datetime
    finalizado_em: datetime | None = None
    situacao: AttendanceStatus
    resultado: str | None = None
    intencao_voto: VoteIntention | None = None
    canal_nome: str | None = None
    canal_outro: str | None = None
    observacao: str | None = None
    motivo_rejeicao_nome: str | None = None
    motivo_observacao: str | None = None
    motivo_encerramento: str | None = None
    motivo_inativacao: str | None = None
    atendente_usuario_id: int
    atendente_nome: str | None = None


class AttendanceReportSummary(BaseModel):
    total: int = 0
    concluido: int = 0
    sem_resposta: int = 0
    numero_invalido: int = 0
    interrompido: int = 0
    votara: int = 0
    nao_votara: int = 0
    indeciso: int = 0
    nao_respondeu: int = 0


class AttendanceReport(BaseModel):
    itens: list[AttendanceReportItem] = Field(default_factory=list)
    total: int = 0
    pagina: int = 1
    tamanho: int = 20
    atendente_usuario_id: int
    atendente_nome: str
    resumo: AttendanceReportSummary = Field(default_factory=AttendanceReportSummary)
    telefonistas: list[OperatorCount] = Field(default_factory=list)


class AttendanceReasonReportFilters(BaseModel):
    inicio: datetime | None = None
    fim: datetime | None = None
    motivo_rejeicao_id: int | None = Field(default=None, ge=1)
    pagina: int = Field(default=1, ge=1)
    tamanho: int = Field(default=20, ge=1, le=100)


class AttendanceReasonReport(BaseModel):
    itens: list[AttendanceReportItem] = Field(default_factory=list)
    total: int = 0
    pagina: int = 1
    tamanho: int = 20
    motivo_rejeicao_id: int | None = None
    motivo: str
    resumo: AttendanceReportSummary = Field(default_factory=AttendanceReportSummary)
    motivos: list[RejectionCount] = Field(default_factory=list)
