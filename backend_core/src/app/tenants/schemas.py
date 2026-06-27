from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid_publico: UUID
    nome: str
    slug: str
    documento: str | None
    tem_mandato: bool
    plano_assinatura_id: int | None
    data_inicio_contrato: date | None
    data_fim_contrato: date | None
    status: str
    criado_em: datetime
    atualizado_em: datetime
