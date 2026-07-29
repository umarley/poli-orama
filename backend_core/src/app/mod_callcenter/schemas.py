from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ContactChannel = Literal["ligacao", "whatsapp", "presencial", "outro"]
VoterStatus = Literal[
    "nao_contatado",
    "tentativa_sem_resposta",
    "retorno_agendado",
    "indeciso",
    "confirmado",
    "nao_apoia",
    "numero_invalido",
]
ContactResult = Literal[
    "tentativa_sem_resposta",
    "retorno_agendado",
    "indeciso",
    "confirmado",
    "nao_apoia",
    "numero_invalido",
]


class CallQueueItem(BaseModel):
    pessoa_id: int
    nome_completo: str
    lideranca_id: int
    lideranca_nome: str
    telefone: str | None
    whatsapp: str | None
    status: VoterStatus
    ultima_tentativa_em: datetime | None
    proximo_contato_em: datetime | None
    total_tentativas: int


class ContactCreate(BaseModel):
    campanha_eleicao_id: int = Field(ge=1)
    pessoa_id: int = Field(ge=1)
    canal: ContactChannel = "ligacao"
    resultado: ContactResult
    observacao: str | None = Field(default=None, max_length=5000)
    iniciado_em: datetime | None = None
    finalizado_em: datetime | None = None
    proximo_contato_em: datetime | None = None

    @model_validator(mode="after")
    def validate_return_date(self) -> "ContactCreate":
        if self.resultado == "retorno_agendado" and self.proximo_contato_em is None:
            raise ValueError("Informe a data do proximo contato.")
        return self


class ContactResponse(BaseModel):
    id: int
    tenant_id: int
    campanha_eleicao_id: int
    pessoa_id: int
    lideranca_id: int
    atendente_usuario_id: int
    canal: ContactChannel
    resultado: ContactResult
    observacao: str | None
    iniciado_em: datetime
    finalizado_em: datetime
    proximo_contato_em: datetime | None
    confirmado: bool


class ConfirmedVoteReportItem(BaseModel):
    pessoa_id: int
    nome_completo: str
    lideranca_id: int | None
    lideranca_nome: str | None
    telefone: str | None
    whatsapp: str | None
    data_confirmacao: datetime
    confirmado_por_nome: str | None
    observacao: str | None
