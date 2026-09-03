export interface ElectoralFilters {
  eleicao_chaves?: string[];
  nm_votaveis?: string[];
  sg_uf?: string[];
  cd_municipio?: number[];
  ds_cargo?: string[];
  nr_zona?: number[];
  nr_local_votacao?: number[];
  nr_secao?: number[];
}

export interface ElectionOption {
  aa_eleicao: number | null;
  cd_eleicao: number | null;
  nr_turno: number | null;
  ds_eleicao: string | null;
  nm_tipo_eleicao: string | null;
  dt_eleicao: string | null;
  chave: string;
}

export interface CandidateOption {
  nm_votavel: string;
  nr_votavel: number | null;
  ds_cargo: string | null;
}

export interface NamedOption {
  valor: string;
  rotulo: string;
}

export interface NumericOption {
  valor: number;
  rotulo: string;
}

export interface RankingItem {
  posicao: number;
  nm_votavel: string;
  nr_votavel: number | null;
  partido: string | null;
  votos: number;
  percentual: number;
  diferenca_votos: number | null;
}

export interface DistributionItem {
  chave: string;
  rotulo: string;
  municipio: string | null;
  zona: number | null;
  local_votacao: string | null;
  secao: number | null;
  candidato: string | null;
  votos: number;
  percentual: number;
}

export interface ElectoralPanel {
  indicadores: {
    total_votos: number;
    candidatos: number;
    municipios: number;
    zonas: number;
    locais: number;
    secoes: number;
  };
  ranking: RankingItem[];
  comparativo: RankingItem[];
  por_municipio: DistributionItem[];
  por_zona: DistributionItem[];
  por_local: DistributionItem[];
  por_secao: DistributionItem[];
}

export interface MapPoint {
  latitude: number;
  longitude: number;
  zona: number | null;
  secao: number | null;
  local_votacao: string | null;
  municipio: string | null;
  votos: number;
  percentual: number;
  candidato: string | null;
  candidatos: string[];
}

export interface ElectoralMap {
  modo: 'secao' | 'zona';
  pontos: MapPoint[];
  truncado: boolean;
}

export interface PaginatedDistribution {
  items: DistributionItem[];
  total: number;
  page: number;
  page_size: number;
}

export type DistributionDimension = 'municipio' | 'zona' | 'local' | 'secao';
export type MapMode = 'secao' | 'zona';
export type MapView = 'calor' | 'secao';
