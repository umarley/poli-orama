"""Contratos HTTP do dominio de territorio."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TerritorySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class TerritorioMalhaGeom(TerritorySchema):
    type: Literal["Polygon", "MultiPolygon"]
    coordinates: list[object]

    @model_validator(mode="after")
    def validate_coordinates(self) -> TerritorioMalhaGeom:
        if self.type == "Polygon":
            if not isinstance(self.coordinates, list) or len(self.coordinates) < 1:
                raise ValueError("Polygon exige ao menos um anel de coordenadas.")
        elif not isinstance(self.coordinates, list) or len(self.coordinates) < 1:
            raise ValueError("MultiPolygon exige ao menos um poligono.")
        return self


class EstadoResponse(TerritorySchema):
    codigo_ibge: int
    uf: str
    nome: str
    regiao: str | None = None


class MunicipioResponse(TerritorySchema):
    codigo_ibge: int
    codigo_uf_ibge: int
    codigo_tse: int | None = None
    nome: str
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    habitantes: int | None = Field(default=None, ge=0)


class BairroResponse(TerritorySchema):
    id: int
    codigo_municipio_ibge: int
    nome: str
    origem: str


class BairroCreate(TerritorySchema):
    codigo_municipio_ibge: int = Field(ge=1)
    nome: str = Field(min_length=1, max_length=150)

    @field_validator("nome")
    @classmethod
    def validate_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Nome do bairro nao pode ser vazio.")
        return name


class ZonaEleitoralResponse(TerritorySchema):
    id: int
    codigo_uf_ibge: int
    codigo_municipio_ibge: int | None = None
    numero_zona: int
    descricao: str | None = None


class LocalVotacaoResponse(TerritorySchema):
    id: int
    codigo_municipio_ibge: int
    zona_eleitoral_id: int | None = None
    bairro_id: int | None = None
    codigo_local: int | None = None
    nome: str
    logradouro: str | None = None
    numero: str | None = None
    complemento: str | None = None
    cep: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    situacao: str


class SecaoEleitoralResponse(TerritorySchema):
    id: int
    zona_eleitoral_id: int
    local_votacao_id: int | None = None
    numero_secao: int
    agregada_em: int | None = None


class TipoTerritorioCreate(TerritorySchema):
    codigo: str = Field(min_length=2, max_length=40, pattern=r"^[a-z0-9_]+$")
    nome: str = Field(min_length=2, max_length=80)
    descricao: str | None = Field(default=None, max_length=255)


class TipoTerritorioUpdate(TerritorySchema):
    nome: str | None = Field(default=None, min_length=2, max_length=80)
    descricao: str | None = Field(default=None, max_length=255)
    ativo: bool | None = None


class TipoTerritorioResponse(TerritorySchema):
    id: int
    tenant_id: int | None
    codigo: str
    nome: str
    descricao: str | None = None
    ativo: bool


class TerritorioCreate(TerritorySchema):
    tipo_territorio_id: int = Field(ge=1)
    nome: str = Field(min_length=2, max_length=150)
    codigo_uf_ibge: int | None = Field(default=None, ge=1)
    codigo_municipio_ibge: int | None = Field(default=None, ge=1)
    bairro_id: int | None = Field(default=None, ge=1)
    zona_eleitoral_id: int | None = Field(default=None, ge=1)
    secao_eleitoral_id: int | None = Field(default=None, ge=1)
    territorio_pai_id: int | None = Field(default=None, ge=1)
    cor: str = Field(default="#1677FF", pattern=r"^#[0-9A-Fa-f]{6}$")
    malha_geom: TerritorioMalhaGeom | None = None


class TerritorioUpdate(TerritorySchema):
    tipo_territorio_id: int | None = Field(default=None, ge=1)
    nome: str | None = Field(default=None, min_length=2, max_length=150)
    codigo_uf_ibge: int | None = Field(default=None, ge=1)
    codigo_municipio_ibge: int | None = Field(default=None, ge=1)
    bairro_id: int | None = Field(default=None, ge=1)
    zona_eleitoral_id: int | None = Field(default=None, ge=1)
    secao_eleitoral_id: int | None = Field(default=None, ge=1)
    territorio_pai_id: int | None = Field(default=None, ge=1)
    cor: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    ativo: bool | None = None
    malha_geom: TerritorioMalhaGeom | None = None


class TerritorioResponse(TerritorySchema):
    id: int
    tenant_id: int
    tipo_territorio_id: int
    tipo_codigo: str
    tipo_nome: str
    nome: str
    codigo_uf_ibge: int | None = None
    codigo_municipio_ibge: int | None = None
    bairro_id: int | None = None
    zona_eleitoral_id: int | None = None
    secao_eleitoral_id: int | None = None
    territorio_pai_id: int | None = None
    cor: str
    ativo: bool
    malha_geom: dict[str, object] | None = None
    criado_em: datetime
    atualizado_em: datetime


class TerritorioTreeNode(TerritorioResponse):
    filhos: list[TerritorioTreeNode] = Field(default_factory=list)


VinculoPessoa = Literal["moradia", "atuacao", "votacao", "responsabilidade"]
ResponsabilidadeLideranca = Literal["principal", "apoio", "compartilhada"]


class PessoaTerritorioInput(TerritorySchema):
    pessoa_id: int = Field(ge=1)
    vinculo: VinculoPessoa = "moradia"


class PessoaTerritorioResponse(PessoaTerritorioInput):
    id: int
    tenant_id: int
    territorio_id: int


class PessoaTerritorioDetalhe(PessoaTerritorioResponse):
    territorio_nome: str
    tipo_nome: str
    territorio_ativo: bool


class LiderancaTerritorioInput(TerritorySchema):
    lideranca_id: int = Field(ge=1)
    responsabilidade: ResponsabilidadeLideranca = "principal"


class LiderancaTerritorioResponse(LiderancaTerritorioInput):
    id: int
    tenant_id: int
    territorio_id: int


class GeocodificacaoInput(TerritorySchema):
    entidade_tipo: Literal["endereco", "evento", "demanda", "local_votacao", "pessoa"]
    entidade_id: int = Field(ge=1)
    endereco_texto: str | None = None
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    precisao: Literal["exata", "aproximada", "centroide", "interpolada", "falha"] | None = None
    provedor: str | None = Field(default="manual", max_length=40)
    status: Literal["pendente", "sucesso", "falha", "revisar"] = "pendente"

    @model_validator(mode="after")
    def validate_coordinates(self) -> GeocodificacaoInput:
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude e longitude devem ser informadas em conjunto.")
        if self.status == "sucesso" and self.latitude is None:
            raise ValueError("Geocodificacao com sucesso exige coordenadas.")
        return self


class GeocodificacaoResponse(GeocodificacaoInput):
    id: int
    tenant_id: int
    processado_em: datetime | None = None
    criado_em: datetime


class MapMarker(TerritorySchema):
    latitude: Decimal
    longitude: Decimal
    quantidade: int = Field(ge=1)
    tipo: Literal["pessoa"] = "pessoa"


class MapPerson(TerritorySchema):
    id: int
    nome_completo: str
    apelido: str | None = None
    telefone: str | None = None
    territorio: str | None = None


class MapMunicipalityShape(TerritorySchema):
    territorio_id: int
    codigo_municipio_ibge: int
    nome: str
    cor: str
    quantidade_eleitores: int = Field(ge=0)
    quantidade_pessoas: int = Field(ge=0)
    geometry: dict[str, object]


class MapTerritoryShape(TerritorySchema):
    territorio_id: int
    tipo_codigo: str
    codigo_municipio_ibge: int | None = None
    nome: str
    cor: str
    quantidade_eleitores: int = Field(default=0, ge=0)
    quantidade_pessoas: int = Field(ge=0)
    geometry: dict[str, object]


class TerritorioPessoaVinculada(TerritorySchema):
    id: int
    nome_completo: str
    telefone: str | None = None
    email: str | None = None
    papel: str


class TerritorioDetalheResponse(TerritorySchema):
    territorio_id: int
    territorio_nome: str
    cor: str
    tipo_codigo: str
    tipo_nome: str
    codigo_municipio_ibge: int | None = None
    codigo_uf_ibge: int | None = None
    uf: str | None = None
    estado_nome: str | None = None
    municipio_nome: str | None = None
    habitantes: int | None = Field(default=None, ge=0)
    quantidade_eleitores: int = Field(ge=0)
    quantidade_pessoas: int = Field(ge=0)
    geometry: dict[str, object] | None = None
    pessoas: list[TerritorioPessoaVinculada]
