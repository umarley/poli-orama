import { httpClient } from '@/services/api/http-client';
import type { ElectoralZoneMesh, MapBounds } from '@/components/maps/ElectoralZoneMeshes';

import type {
  CandidateOption,
  DistributionDimension,
  ElectionOption,
  ElectoralFilters,
  ElectoralMap,
  ElectoralPanel,
  ElectoralZoneResult,
  MapMode,
  NamedOption,
  NumericOption,
  PaginatedDistribution,
} from './types';

const base = '/api/v1/gestao-eleitoral';
const slowRequest = { timeout: 60_000 };

export function omitElectoralFilters(
  filters: ElectoralFilters,
  ...keys: Array<keyof ElectoralFilters>
): ElectoralFilters {
  const next = { ...filters };
  keys.forEach((key) => {
    delete next[key];
  });
  return next;
}

export function serializeElectoralParams(
  filters: ElectoralFilters,
  extra: Record<string, unknown> = {},
) {
  const params: Record<string, unknown> = { ...extra };
  (
    Object.entries(filters) as Array<
      [keyof ElectoralFilters, ElectoralFilters[keyof ElectoralFilters]]
    >
  ).forEach(([key, value]) => {
    if (!Array.isArray(value) || value.length === 0) return;
    params[key] = value;
  });
  return {
    params,
    paramsSerializer: {
      serialize(input: Record<string, unknown>) {
        const search = new URLSearchParams();
        Object.entries(input).forEach(([key, value]) => {
          if (Array.isArray(value)) {
            value.forEach((item) => {
              if (item !== undefined && item !== null && item !== '') {
                search.append(key, String(item));
              }
            });
            return;
          }
          if (value !== undefined && value !== null && value !== '') {
            search.append(key, String(value));
          }
        });
        return search.toString();
      },
    },
  };
}

export async function listElectoralElections() {
  const { data } = await httpClient.get<ElectionOption[]>(`${base}/filtros/eleicoes`, slowRequest);
  return data;
}

export async function searchElectoralCandidates(filters: ElectoralFilters, q: string) {
  const { data } = await httpClient.get<CandidateOption[]>(`${base}/filtros/candidatos`, {
    ...serializeElectoralParams(filters, { q }),
  });
  return data;
}

export async function listElectoralStates(filters: ElectoralFilters) {
  const { data } = await httpClient.get<NamedOption[]>(
    `${base}/filtros/estados`,
    serializeElectoralParams(filters),
  );
  return data;
}

export async function listElectoralMunicipalities(filters: ElectoralFilters) {
  const { data } = await httpClient.get<NumericOption[]>(
    `${base}/filtros/municipios`,
    serializeElectoralParams(filters),
  );
  return data;
}

export async function listElectoralOffices(filters: ElectoralFilters) {
  const { data } = await httpClient.get<NamedOption[]>(
    `${base}/filtros/cargos`,
    serializeElectoralParams(filters),
  );
  return data;
}

export async function listElectoralZones(filters: ElectoralFilters) {
  const { data } = await httpClient.get<NumericOption[]>(
    `${base}/filtros/zonas`,
    serializeElectoralParams(filters),
  );
  return data;
}

export async function listElectoralPollingPlaces(filters: ElectoralFilters) {
  const { data } = await httpClient.get<NumericOption[]>(
    `${base}/filtros/locais`,
    serializeElectoralParams(filters),
  );
  return data;
}

export async function listElectoralSections(filters: ElectoralFilters) {
  const { data } = await httpClient.get<NumericOption[]>(
    `${base}/filtros/secoes`,
    serializeElectoralParams(filters),
  );
  return data;
}

export async function getElectoralPanel(filters: ElectoralFilters) {
  const { data } = await httpClient.get<ElectoralPanel>(`${base}/painel`, {
    ...serializeElectoralParams(filters),
    ...slowRequest,
  });
  return data;
}

export async function getElectoralMap(filters: ElectoralFilters, modo: MapMode) {
  const { data } = await httpClient.get<ElectoralMap>(`${base}/mapa`, {
    ...serializeElectoralParams(filters, { modo }),
    ...slowRequest,
  });
  return data;
}

export async function exportElectoralMap(
  filters: ElectoralFilters,
  modo: MapMode,
  formato: 'csv' | 'xlsx',
) {
  const response = await httpClient.post<Blob>(
    `${base}/mapa/exportacoes`,
    { formato, modo, filtros: filters },
    { responseType: 'blob', ...slowRequest },
  );
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `analise-eleitoral-mapa-${new Date().toISOString().slice(0, 10)}.${formato}`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function getElectoralZoneMeshes(filters: ElectoralFilters, bounds: MapBounds) {
  const { data } = await httpClient.get<ElectoralZoneMesh[]>(
    `${base}/mapa/zonas-eleitorais/malhas`,
    {
      ...serializeElectoralParams(filters, {
        sul: bounds.south,
        oeste: bounds.west,
        norte: bounds.north,
        leste: bounds.east,
      }),
      ...slowRequest,
    },
  );
  return data;
}

export async function getElectoralZoneResults(filters: ElectoralFilters) {
  const { data } = await httpClient.get<ElectoralZoneResult[]>(
    `${base}/mapa/zonas-eleitorais/resultados`,
    {
      ...serializeElectoralParams(filters),
      ...slowRequest,
    },
  );
  return data;
}

export async function getElectoralDistribution(
  dimension: DistributionDimension,
  filters: ElectoralFilters,
  page: number,
  pageSize: number,
) {
  const { data } = await httpClient.get<PaginatedDistribution>(
    `${base}/distribuicao/${dimension}`,
    {
      ...serializeElectoralParams(filters, { page, page_size: pageSize }),
      ...slowRequest,
    },
  );
  return data;
}
