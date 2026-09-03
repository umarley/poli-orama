from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GestaoEleitoralSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ResultadoFilters(GestaoEleitoralSchema):
    eleicao_chaves: list[str] = Field(default_factory=list)
    nm_votaveis: list[str] = Field(default_factory=list)
    sg_uf: list[str] = Field(default_factory=list)
    cd_municipio: list[int] = Field(default_factory=list)
    ds_cargo: list[str] = Field(default_factory=list)
    nr_zona: list[int] = Field(default_factory=list)
    nr_local_votacao: list[int] = Field(default_factory=list)
    nr_secao: list[int] = Field(default_factory=list)

    @property
    def votaveis(self) -> list[str]:
        return [name.strip() for name in self.nm_votaveis if name and name.strip()]

    @property
    def ufs(self) -> list[str]:
        return [uf.strip().upper() for uf in self.sg_uf if uf and uf.strip()]

    @property
    def cargos(self) -> list[str]:
        return [cargo.strip() for cargo in self.ds_cargo if cargo and cargo.strip()]


class ElectionOption(GestaoEleitoralSchema):
    aa_eleicao: int | None
    cd_eleicao: int | None
    nr_turno: int | None
    ds_eleicao: str | None
    nm_tipo_eleicao: str | None
    dt_eleicao: str | None
    chave: str


class CandidateOption(GestaoEleitoralSchema):
    nm_votavel: str
    nr_votavel: int | None
    ds_cargo: str | None


class NamedOption(GestaoEleitoralSchema):
    valor: str
    rotulo: str


class NumericOption(GestaoEleitoralSchema):
    valor: int
    rotulo: str


class RankingItem(GestaoEleitoralSchema):
    posicao: int
    nm_votavel: str
    nr_votavel: int | None = None
    partido: str | None = None
    votos: int
    percentual: float
    diferenca_votos: int | None = None


class DistributionItem(GestaoEleitoralSchema):
    chave: str
    rotulo: str
    municipio: str | None = None
    zona: int | None = None
    local_votacao: str | None = None
    secao: int | None = None
    candidato: str | None = None
    votos: int
    percentual: float


class IndicatorSummary(GestaoEleitoralSchema):
    total_votos: int
    candidatos: int
    municipios: int
    zonas: int
    locais: int
    secoes: int


class PanelResponse(GestaoEleitoralSchema):
    indicadores: IndicatorSummary
    ranking: list[RankingItem]
    comparativo: list[RankingItem]
    por_municipio: list[DistributionItem]
    por_zona: list[DistributionItem]
    por_local: list[DistributionItem]
    por_secao: list[DistributionItem]


class MapPoint(GestaoEleitoralSchema):
    latitude: float
    longitude: float
    zona: int | None = None
    secao: int | None = None
    local_votacao: str | None = None
    municipio: str | None = None
    votos: int
    percentual: float
    candidato: str | None = None
    candidatos: list[str]


class MapResponse(GestaoEleitoralSchema):
    modo: Literal["secao", "zona"]
    pontos: list[MapPoint]
    truncado: bool


class PaginatedDistribution(GestaoEleitoralSchema):
    items: list[DistributionItem]
    total: int
    page: int
    page_size: int


DistributionDimension = Literal["municipio", "zona", "local", "secao"]
MapMode = Literal["secao", "zona"]
