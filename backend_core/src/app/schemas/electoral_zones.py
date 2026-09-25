"""Contratos compartilhados para malhas de zonas eleitorais."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class ElectoralZoneSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ElectoralZoneGeometry(ElectoralZoneSchema):
    type: Literal["Polygon"]
    coordinates: list[object]


class ElectoralZoneMapItem(ElectoralZoneSchema):
    id: int
    numero_zona: int
    municipio: str | None
    quantidade_locais: int
    geometry: ElectoralZoneGeometry
