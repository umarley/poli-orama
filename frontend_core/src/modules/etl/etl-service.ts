import { httpClient } from '@/services/api/http-client';

import type {
  DataImport,
  DataSource,
  ImportDuplicate,
  ImportError,
  ImportSummary,
} from './types';

const base = '/api/v1/etl';

export async function listSources() {
  const { data } = await httpClient.get<DataSource[]>(`${base}/fontes`);
  return data;
}

export async function listImports() {
  const { data } = await httpClient.get<DataImport[]>(`${base}/importacoes`);
  return data;
}

export async function getImport(id: number) {
  const { data } = await httpClient.get<DataImport>(`${base}/importacoes/${id}`);
  return data;
}

export async function getImportSummary(id: number) {
  const { data } = await httpClient.get<ImportSummary>(
    `${base}/importacoes/${id}/resumo`,
  );
  return data;
}

export async function getImportErrors(id: number) {
  const { data } = await httpClient.get<ImportError[]>(
    `${base}/importacoes/${id}/erros`,
  );
  return data;
}

export async function getImportDuplicates(id: number) {
  const { data } = await httpClient.get<ImportDuplicate[]>(
    `${base}/importacoes/${id}/duplicidades`,
  );
  return data;
}

export async function createImport(payload: {
  file: File;
  sourceId: number;
  description?: string;
  parameters?: Record<string, unknown>;
}) {
  const body = new FormData();
  body.append('arquivo', payload.file);
  body.append('fonte_dado_id', String(payload.sourceId));
  if (payload.description) body.append('descricao', payload.description);
  body.append('parametros', JSON.stringify(payload.parameters ?? {}));
  body.append('mapeamento', '{}');
  const { data } = await httpClient.post<DataImport>(`${base}/importacoes`, body, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60_000,
  });
  return data;
}

export async function updateMapping(
  id: number,
  mapping: Record<string, string>,
) {
  const { data } = await httpClient.put(`${base}/importacoes/${id}/mapeamento`, {
    mapeamento: mapping,
    parametros: {},
    reprocessar: true,
  });
  return data;
}

export async function approveImport(id: number) {
  const { data } = await httpClient.post(`${base}/importacoes/${id}/aprovar`);
  return data;
}

export async function cancelImport(id: number) {
  await httpClient.delete(`${base}/importacoes/${id}`);
}

export async function downloadErrorReport(id: number) {
  const { data } = await httpClient.get<Blob>(
    `${base}/importacoes/${id}/relatorio-erros.csv`,
    { responseType: 'blob' },
  );
  const url = URL.createObjectURL(data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `importacao-${id}-erros.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}
