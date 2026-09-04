import type { PessoaContato, TipoContato } from '@/modules/cadastro/types';
import { httpClient } from '@/services/api/http-client';

import type {
  Attendance,
  AttendanceClosePayload,
  AttendanceIndicators,
  AttendancePersonUpdate,
  AttendanceQueue,
  AttendanceUpdate,
  CommunicationChannel,
  RejectionReason,
} from './atendimento-types';

const base = '/api/v1/comunicacao';

export async function listAttendanceChannels() {
  const { data } = await httpClient.get<CommunicationChannel[]>(`${base}/atendimento/canais`);
  return data;
}

export async function listRejectionReasons() {
  const { data } = await httpClient.get<RejectionReason[]>(`${base}/atendimento/motivos-rejeicao`);
  return data;
}

export async function getCurrentAttendance() {
  const { data } = await httpClient.get<Attendance | null>(`${base}/atendimento/atual`);
  return data;
}

export async function listOpenAttendances() {
  const { data } = await httpClient.get<AttendanceQueue>(`${base}/atendimento/abertos`);
  return data;
}

export async function getAttendance(id: number) {
  const { data } = await httpClient.get<Attendance>(`${base}/atendimento/${id}`);
  return data;
}

export async function startAttendance() {
  const { data } = await httpClient.post<Attendance>(`${base}/atendimento/iniciar`);
  return data;
}

export async function updateAttendance(id: number, payload: AttendanceUpdate) {
  const { data } = await httpClient.patch<Attendance>(`${base}/atendimento/${id}`, payload);
  return data;
}

export async function updateAttendancePerson(id: number, payload: AttendancePersonUpdate) {
  const { data } = await httpClient.patch<Attendance>(`${base}/atendimento/${id}/pessoa`, payload);
  return data;
}

export async function addAttendanceDocument(
  id: number,
  payload: { tipo_documento: string; numero: string; orgao_emissor?: string; uf_emissor?: string },
) {
  const { data } = await httpClient.post<Attendance>(`${base}/atendimento/${id}/documentos`, payload);
  return data;
}

export async function addAttendanceContact(
  id: number,
  payload: {
    tipo_contato: TipoContato;
    valor: string;
    principal?: boolean;
    observacao?: string | null;
  },
) {
  const { data } = await httpClient.post<Attendance>(`${base}/atendimento/${id}/contatos`, payload);
  return data;
}

export async function updateAttendanceContact(
  id: number,
  contactId: number,
  payload: Partial<Pick<PessoaContato, 'valor' | 'principal' | 'observacao' | 'verificado'>>,
) {
  const { data } = await httpClient.patch<Attendance>(
    `${base}/atendimento/${id}/contatos/${contactId}`,
    payload,
  );
  return data;
}

export async function deleteAttendanceContact(id: number, contactId: number) {
  const { data } = await httpClient.delete<Attendance>(
    `${base}/atendimento/${id}/contatos/${contactId}`,
  );
  return data;
}

export async function addAttendanceInteraction(
  id: number,
  payload: { assunto?: string; conteudo: string; resultado?: string },
) {
  const { data } = await httpClient.post<Attendance>(`${base}/atendimento/${id}/interacoes`, payload);
  return data;
}

export async function closeAttendance(id: number, payload: AttendanceClosePayload) {
  const { data } = await httpClient.post<Attendance>(`${base}/atendimento/${id}/encerrar`, payload);
  return data;
}

export async function invalidateAttendance(id: number, motivo_inativacao: string) {
  const { data } = await httpClient.post<Attendance>(`${base}/atendimento/${id}/invalidar`, {
    motivo_inativacao,
  });
  return data;
}

export async function getAttendanceIndicators(params: {
  inicio?: string;
  fim?: string;
  atendente_usuario_id?: number;
  canal?: number;
  situacao?: string;
  resultado?: string;
}) {
  const cleaned = Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== ''),
  );
  const { data } = await httpClient.get<AttendanceIndicators>(`${base}/indicadores`, {
    params: cleaned,
  });
  return data;
}
