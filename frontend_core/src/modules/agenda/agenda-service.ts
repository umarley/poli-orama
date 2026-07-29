import { httpClient } from '@/services/api/http-client';

import type {
  AgendaCatalog,
  AgendaEvent,
  AgendaEventDetail,
  AgendaFilters,
  EventAgendaItem,
  EventAttendance,
  EventDemand,
  EventInput,
  EventInvitation,
  EventLeadership,
  EventParticipant,
} from './types';

const base = '/api/v1/agenda';

export async function listEventTypes() {
  const { data } = await httpClient.get<AgendaCatalog[]>(`${base}/tipos`);
  return data;
}

export async function listEventStatuses() {
  const { data } = await httpClient.get<AgendaCatalog[]>(`${base}/status`);
  return data;
}

export async function listEvents(filters: AgendaFilters) {
  const { data } = await httpClient.get<AgendaEvent[]>(`${base}/eventos`, {
    params: filters,
  });
  return data;
}

export async function getEvent(id: number) {
  const { data } = await httpClient.get<AgendaEventDetail>(`${base}/eventos/${id}`);
  return data;
}

export async function createEvent(payload: EventInput) {
  const { data } = await httpClient.post<AgendaEvent>(`${base}/eventos`, payload);
  return data;
}

export async function updateEvent(id: number, payload: Partial<EventInput>) {
  const { data } = await httpClient.patch<AgendaEvent>(`${base}/eventos/${id}`, payload);
  return data;
}

export async function cancelEvent(id: number, motivo: string) {
  const { data } = await httpClient.post<AgendaEvent>(`${base}/eventos/${id}/cancelar`, {
    motivo,
  });
  return data;
}

export async function addParticipant(
  id: number,
  payload: { pessoa_id: number; papel?: string; presente?: boolean; observacao?: string },
) {
  const { data } = await httpClient.post<EventParticipant>(
    `${base}/eventos/${id}/participantes`,
    payload,
  );
  return data;
}

export async function addLeadership(id: number, payload: { lideranca_id: number; papel?: string }) {
  const { data } = await httpClient.post<EventLeadership>(
    `${base}/eventos/${id}/liderancas`,
    payload,
  );
  return data;
}

export async function addInvitation(
  id: number,
  payload: {
    direcao: 'recebido' | 'emitido';
    origem?: string;
    pessoa_indicou_id?: number;
    status: 'pendente' | 'aceito' | 'recusado' | 'confirmado';
    descricao?: string;
  },
) {
  const { data } = await httpClient.post<EventInvitation>(
    `${base}/eventos/${id}/convites`,
    payload,
  );
  return data;
}

export async function addAgendaItem(
  id: number,
  payload: { titulo: string; descricao?: string; encaminhamento?: string; ordem?: number },
) {
  const { data } = await httpClient.post<EventAgendaItem>(`${base}/eventos/${id}/pautas`, payload);
  return data;
}

export async function recordAttendance(
  id: number,
  payload: Omit<EventAttendance, 'id' | 'registrado_por' | 'registrado_em'>,
) {
  const { data } = await httpClient.put<EventAttendance>(`${base}/eventos/${id}/presenca`, payload);
  return data;
}

export async function createDemand(
  id: number,
  payload: {
    titulo: string;
    descricao: string;
    pessoa_solicitante_id?: number;
    territorio_id?: number;
    categoria_demanda_id?: number;
    prioridade_demanda_id?: number;
    prazo?: string;
  },
) {
  const { data } = await httpClient.post<EventDemand>(`${base}/eventos/${id}/demandas`, payload);
  return data;
}

export async function downloadAgenda(filters: AgendaFilters) {
  const { data } = await httpClient.get<Blob>(`${base}/exportar.csv`, {
    params: filters,
    responseType: 'blob',
  });
  const url = URL.createObjectURL(data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = 'agenda.csv';
  anchor.click();
  URL.revokeObjectURL(url);
}
