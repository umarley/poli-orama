"""Contratos HTTP do modulo Anuncios."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RouteStatus = Literal["PLANEJADA", "LIBERADA", "EM_EXECUCAO", "CONCLUIDA", "CANCELADA"]
PointStatus = Literal[
    "PENDENTE",
    "EM_EXECUCAO",
    "INSTALADO",
    "RECOLHIDO",
    "RECOLHIDO_PARCIALMENTE",
    "COM_EXTRAVIO",
    "NAO_EXECUTADO",
]
MovementType = Literal["INSTALACAO", "RECOLHIMENTO", "EXTRAVIO"]


class AnuncioSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class MaterialCreate(AnuncioSchema):
    nome: str = Field(min_length=2, max_length=120)
    descricao: str | None = None

    @field_validator("nome")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())


class MaterialUpdate(AnuncioSchema):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    descricao: str | None = None
    ativo: bool | None = None

    @field_validator("nome")
    @classmethod
    def normalize_optional_name(cls, value: str | None) -> str | None:
        return " ".join(value.split()) if value is not None else None


class MaterialResponse(AnuncioSchema):
    id: int
    uuid_publico: UUID
    tenant_id: int
    nome: str
    descricao: str | None
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime


class TeamInput(AnuncioSchema):
    nome: str = Field(min_length=2, max_length=150)
    descricao: str | None = None
    lideranca_id: int | None = Field(default=None, ge=1)
    territorio_id: int | None = Field(default=None, ge=1)
    usuario_ids: list[int] = Field(default_factory=list, max_length=500)

    @field_validator("nome")
    @classmethod
    def normalize_team_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("usuario_ids")
    @classmethod
    def unique_users(cls, value: list[int]) -> list[int]:
        if any(item < 1 for item in value):
            raise ValueError("usuario_ids deve conter apenas IDs validos.")
        if len(value) != len(set(value)):
            raise ValueError("A equipe contem usuarios duplicados.")
        return value


class TeamUpdate(AnuncioSchema):
    nome: str | None = Field(default=None, min_length=2, max_length=150)
    descricao: str | None = None
    lideranca_id: int | None = Field(default=None, ge=1)
    territorio_id: int | None = Field(default=None, ge=1)
    usuario_ids: list[int] | None = Field(default=None, max_length=500)
    ativo: bool | None = None

    @field_validator("usuario_ids")
    @classmethod
    def unique_optional_users(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        return TeamInput.unique_users(value)


class TeamMemberResponse(AnuncioSchema):
    usuario_id: int
    pessoa_id: int
    nome: str
    email: str


class TeamResponse(AnuncioSchema):
    id: int
    uuid_publico: UUID
    tenant_id: int
    nome: str
    descricao: str | None
    lideranca_id: int | None
    territorio_id: int | None
    ativo: bool
    criado_em: datetime
    atualizado_em: datetime
    membros: list[TeamMemberResponse] = Field(default_factory=list)


class PointMaterialInput(AnuncioSchema):
    material_id: int = Field(ge=1)
    quantidade_planejada: int = Field(ge=1, le=100000)


class RoutePointInput(AnuncioSchema):
    uuid_publico: UUID | None = None
    ordem: int = Field(ge=1)
    descricao_local: str = Field(min_length=2, max_length=180)
    endereco: str | None = None
    latitude_planejada: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude_planejada: Decimal | None = Field(default=None, ge=-180, le=180)
    observacao: str | None = None
    materiais: list[PointMaterialInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_point(self) -> "RoutePointInput":
        if (self.latitude_planejada is None) != (self.longitude_planejada is None):
            raise ValueError("Latitude e longitude planejadas devem ser informadas em conjunto.")
        material_ids = [item.material_id for item in self.materiais]
        if len(material_ids) != len(set(material_ids)):
            raise ValueError("O ponto contem materiais duplicados.")
        return self


class RouteCreate(AnuncioSchema):
    nome: str = Field(min_length=2, max_length=180)
    descricao: str | None = None
    territorio_id: int | None = Field(default=None, ge=1)
    pontos: list[RoutePointInput] = Field(min_length=1, max_length=500)
    ativo: bool = True

    @model_validator(mode="after")
    def validate_route(self) -> "RouteCreate":
        orders = [point.ordem for point in self.pontos]
        if len(orders) != len(set(orders)):
            raise ValueError("A rota contem ordens de pontos duplicadas.")
        return self


class RouteUpdate(AnuncioSchema):
    nome: str | None = Field(default=None, min_length=2, max_length=180)
    descricao: str | None = None
    territorio_id: int | None = Field(default=None, ge=1)
    pontos: list[RoutePointInput] | None = Field(default=None, min_length=1, max_length=500)
    ativo: bool | None = None

    @model_validator(mode="after")
    def validate_points(self) -> "RouteUpdate":
        if self.pontos is not None:
            orders = [point.ordem for point in self.pontos]
            if len(orders) != len(set(orders)):
                raise ValueError("A rota contem ordens de pontos duplicadas.")
        return self


class PointMaterialResponse(AnuncioSchema):
    id: int
    material_id: int
    material_nome: str
    quantidade_planejada: int
    quantidade_instalada: int
    quantidade_recolhida: int
    quantidade_extraviada: int
    quantidade_pendente: int


class PointSummary(AnuncioSchema):
    id: int
    uuid_publico: UUID
    ordem: int
    descricao_local: str
    endereco: str | None
    latitude_planejada: Decimal | None
    longitude_planejada: Decimal | None
    observacao: str | None
    status: PointStatus
    materiais: list[PointMaterialResponse]


class ExecutionPhoto(AnuncioSchema):
    anexo_id: int
    preview_url: str
    download_url: str
    criado_em: datetime


class MovementResponse(AnuncioSchema):
    id: int
    uuid_publico: UUID
    material_id: int
    material_nome: str
    tipo_movimentacao: MovementType
    quantidade: int
    usuario_id: int
    usuario_nome: str
    latitude: Decimal
    longitude: Decimal
    observacao: str | None
    registrado_em: datetime


class ExecutionHistory(AnuncioSchema):
    id: int
    uuid_publico: UUID
    tipo_operacao: Literal["INSTALACAO", "RETIRADA"]
    usuario_id: int
    usuario_nome: str
    latitude: Decimal
    longitude: Decimal
    precisao: Decimal | None
    observacao: str | None
    executado_em: datetime
    foto: ExecutionPhoto | None = None
    movimentacoes: list[MovementResponse]


class PointDetail(PointSummary):
    historico: list[ExecutionHistory] = Field(default_factory=list)


class RouteResponse(AnuncioSchema):
    id: int
    uuid_publico: UUID
    tenant_id: int
    nome: str
    descricao: str | None
    territorio_id: int | None
    territorio_nome: str | None
    ativo: bool
    total_pontos: int
    criado_em: datetime
    atualizado_em: datetime


class RouteTemplateMaterialResponse(AnuncioSchema):
    id: int
    material_id: int
    material_nome: str
    quantidade_planejada: int


class RouteTemplatePointResponse(AnuncioSchema):
    id: int
    uuid_publico: UUID
    ordem: int
    descricao_local: str
    endereco: str | None
    latitude_planejada: Decimal | None
    longitude_planejada: Decimal | None
    observacao: str | None
    materiais: list[RouteTemplateMaterialResponse]


class RouteDetail(RouteResponse):
    pontos: list[RouteTemplatePointResponse]


class PlanningCreate(AnuncioSchema):
    rota_id: int = Field(ge=1)
    equipe_id: int | None = Field(default=None, ge=1)
    usuario_responsavel_id: int | None = Field(default=None, ge=1)
    data_execucao: date
    observacao: str | None = None

    @model_validator(mode="after")
    def validate_assignment(self) -> "PlanningCreate":
        if self.equipe_id is None and self.usuario_responsavel_id is None:
            raise ValueError("O planejamento deve ser atribuido a uma equipe ou usuario.")
        return self


class PlanningUpdate(AnuncioSchema):
    equipe_id: int | None = Field(default=None, ge=1)
    usuario_responsavel_id: int | None = Field(default=None, ge=1)
    data_execucao: date | None = None
    observacao: str | None = None
    status: RouteStatus | None = None


class PlanningResponse(AnuncioSchema):
    id: int
    uuid_publico: UUID
    tenant_id: int
    rota_id: int
    rota_uuid: UUID
    nome: str
    descricao: str | None
    data_execucao: date
    status: RouteStatus
    observacao: str | None
    equipe_id: int | None
    equipe_nome: str | None
    usuario_responsavel_id: int | None
    usuario_responsavel_nome: str | None
    territorio_id: int | None
    territorio_nome: str | None
    total_pontos: int
    pontos_concluidos: int
    pontos_pendentes: int
    criado_em: datetime
    atualizado_em: datetime


class PlanningDetail(PlanningResponse):
    pontos: list[PointDetail]


class InstallationMaterial(AnuncioSchema):
    material_id: int = Field(ge=1)
    quantidade: int = Field(ge=1, le=100000)


class InstallationInput(AnuncioSchema):
    chave_idempotencia: str = Field(min_length=8, max_length=64)
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    precisao: Decimal | None = Field(default=None, ge=0)
    capturado_em: datetime
    observacao: str | None = None
    materiais: list[InstallationMaterial] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_materials(self) -> "InstallationInput":
        ids = [item.material_id for item in self.materiais]
        if len(ids) != len(set(ids)):
            raise ValueError("A instalacao contem materiais duplicados.")
        return self


class WithdrawalMaterial(AnuncioSchema):
    material_id: int = Field(ge=1)
    quantidade_recolhida: int = Field(default=0, ge=0, le=100000)
    quantidade_extraviada: int = Field(default=0, ge=0, le=100000)

    @model_validator(mode="after")
    def validate_quantity(self) -> "WithdrawalMaterial":
        if self.quantidade_recolhida + self.quantidade_extraviada <= 0:
            raise ValueError("Informe uma quantidade recolhida ou extraviada.")
        return self


class WithdrawalInput(AnuncioSchema):
    chave_idempotencia: str = Field(min_length=8, max_length=64)
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    precisao: Decimal | None = Field(default=None, ge=0)
    capturado_em: datetime
    observacao: str | None = None
    materiais: list[WithdrawalMaterial] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_loss_reason(self) -> "WithdrawalInput":
        ids = [item.material_id for item in self.materiais]
        if len(ids) != len(set(ids)):
            raise ValueError("A retirada contem materiais duplicados.")
        if any(item.quantidade_extraviada > 0 for item in self.materiais):
            if not self.observacao or len(self.observacao.strip()) < 3:
                raise ValueError("A observacao e obrigatoria quando houver extravio.")
        return self


class OperationResponse(AnuncioSchema):
    execucao: ExecutionHistory
    ponto_status: PointStatus
    rota_status: RouteStatus
    idempotente: bool = False


class DashboardTotals(AnuncioSchema):
    rotas_programadas: int
    rotas_iniciadas: int
    rotas_concluidas: int
    pontos_planejados: int
    pontos_executados: int
    pontos_pendentes: int
    materiais_instalados: int
    materiais_recolhidos: int
    materiais_extraviados: int
    taxa_extravio: Decimal


class DashboardBreakdown(AnuncioSchema):
    chave: str
    nome: str
    instalado: int
    recolhido: int
    extraviado: int


class DashboardResponse(AnuncioSchema):
    totais: DashboardTotals
    por_material: list[DashboardBreakdown]
    pontos: list[dict[str, object]]
