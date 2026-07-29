import { httpClient } from '@/services/api/http-client';

import type {
  Birthdays,
  CommemorativeDate,
  DashboardConfiguration,
  DashboardFilters,
  DashboardOverview,
  ReportRow,
  ReportType,
} from './types';

const base = '/api/v1/dashboard';

export async function getDashboardOverview(filters: DashboardFilters) {
  const { data } = await httpClient.get<DashboardOverview>(`${base}/visao-geral`, {
    params: filters,
  });
  return data;
}

export async function getBirthdays(filters: DashboardFilters) {
  const { data } = await httpClient.get<Birthdays>(`${base}/aniversariantes`, {
    params: filters,
  });
  return data;
}

export async function getCommemorativeDates(filters: DashboardFilters) {
  const { data } = await httpClient.get<CommemorativeDate[]>(`${base}/datas-comemorativas`, {
    params: filters,
  });
  return data;
}

export async function getDashboardConfiguration() {
  const { data } = await httpClient.get<DashboardConfiguration>(`${base}/configuracao`);
  return data;
}

export async function getReport(type: ReportType, filters: DashboardFilters) {
  const { data } = await httpClient.get<ReportRow[]>(`${base}/relatorios/${type}`, {
    params: filters,
  });
  return data;
}

export async function exportReport(
  type: ReportType,
  format: 'csv' | 'xlsx',
  purpose: string,
  filters: DashboardFilters,
) {
  const response = await httpClient.post<Blob>(
    `${base}/exportacoes`,
    { relatorio: type, formato: format, finalidade: purpose, filtros: filters },
    { responseType: 'blob' },
  );
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `relatorio-${type}.${format}`;
  anchor.click();
  URL.revokeObjectURL(url);
}
