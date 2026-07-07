from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class DashboardFilters(BaseModel):
    data_inicio: date
    data_fim: date
    territorio_id: int | None = Field(default=None, ge=1)
    lideranca_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_period(self) -> "DashboardFilters":
        if self.data_inicio > self.data_fim:
            raise ValueError("data_inicio deve ser anterior ou igual a data_fim.")
        if (self.data_fim - self.data_inicio).days > 730:
            raise ValueError("O periodo maximo para consulta e de 730 dias.")
        return self


class CadastroKpi(BaseModel):
    total: int
    novos_periodo: int
    incompletos_pendentes: int
    duplicidades_abertas: int
    completude_media: float


class LiderancaKpi(BaseModel):
    total_lideres: int
    total_liderados: int
    media_liderados: float


class MetaKpi(BaseModel):
    metas_ativas: int
    atingidas: int
    em_risco: int
    percentual_medio: float


class DemandaKpi(BaseModel):
    total: int
    pendentes: int
    em_andamento: int
    concluidas: int
    vencidas: int


class EventoKpi(BaseModel):
    total_periodo: int
    realizados: int
    cancelados: int
    presencas_registradas: int


class DashboardOverview(BaseModel):
    filtros: DashboardFilters
    cadastros: CadastroKpi
    liderancas: LiderancaKpi
    metas: MetaKpi
    demandas: DemandaKpi
    eventos: EventoKpi
    gerado_em: datetime


class BirthdayItem(BaseModel):
    pessoa_id: int
    nome: str
    data_nascimento: date
    idade: int | None
    territorio: str | None


class Birthdays(BaseModel):
    hoje: list[BirthdayItem]
    mes: list[BirthdayItem]


class CommemorativeDate(BaseModel):
    id: int
    nome: str
    categoria: str | None
    data: date
    ambito: str


class GoalLeaderRow(BaseModel):
    lideranca_id: int
    lider: str
    meta: int
    atual: int
    percentual: float
    risco: str


class DemandReportRow(BaseModel):
    status: str
    categoria: str
    responsavel: str
    prazo: date | None
    total: int
    vencidas: int


class AgendaReportRow(BaseModel):
    evento_id: int
    titulo: str
    data_inicio: datetime
    data_fim: datetime | None
    status: str
    territorio: str | None
    responsavel: str | None
    convites: int
    pautas: int


class RegistrationEvolutionRow(BaseModel):
    data: date
    origem: str
    total: int


class LeaderRankingRow(BaseModel):
    posicao: int
    lideranca_id: int
    lider: str
    liderados: int
    meta: int
    atual: int
    percentual: float


ReportType = Literal["metas", "demandas", "agenda", "cadastros", "lideres"]
ExportFormat = Literal["csv", "xlsx"]


class ExportRequest(BaseModel):
    relatorio: ReportType
    formato: ExportFormat = "csv"
    finalidade: str = Field(min_length=3, max_length=255)
    filtros: DashboardFilters


class DashboardConfiguration(BaseModel):
    id: int | None = None
    nome: str = "Dashboard principal"
    perfil: str
    filtros_padrao: dict[str, Any] = Field(default_factory=dict)
    widgets: list[str]


class DashboardConfigurationUpdate(BaseModel):
    perfil: str = Field(min_length=2, max_length=60)
    nome: str = Field(default="Dashboard principal", min_length=2, max_length=120)
    filtros_padrao: dict[str, Any] = Field(default_factory=dict)
    widgets: list[str] = Field(min_length=1, max_length=30)


class ReportDefinition(BaseModel):
    id: int
    codigo: str
    nome: str
    descricao: str | None
    tipo: str | None
    automatico: bool
    agendamento_cron: str | None


class ReportExecution(BaseModel):
    id: int
    relatorio_id: int
    relatorio: str
    parametros: dict[str, Any]
    status: str
    iniciado_em: datetime
    concluido_em: datetime | None
