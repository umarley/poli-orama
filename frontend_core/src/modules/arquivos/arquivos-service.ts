import { httpClient } from '@/services/api/http-client';

import type { Attachment, AttachmentEntity, AttachmentType } from './types';

const base = '/api/v1/arquivos';

export async function listAttachmentTypes() {
  return (await httpClient.get<AttachmentType[]>(`${base}/tipos`)).data;
}

export async function listAttachments(entity: AttachmentEntity, entityId: number) {
  return (await httpClient.get<Attachment[]>(`${base}/entidades/${entity}/${entityId}/anexos`))
    .data;
}

export async function uploadAttachment(payload: {
  entity: AttachmentEntity;
  entityId: number;
  typeId: number;
  description?: string;
  file: File;
}) {
  const body = new FormData();
  body.append('arquivo', payload.file);
  body.append('entidade_tipo', payload.entity);
  body.append('entidade_id', String(payload.entityId));
  body.append('tipo_anexo_id', String(payload.typeId));
  if (payload.description) body.append('descricao', payload.description);
  return (
    await httpClient.post<Attachment>(`${base}/anexos`, body, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  ).data;
}

export async function uploadPersonPhoto(personId: number, file: File) {
  const body = new FormData();
  body.append('arquivo', file);
  return (
    await httpClient.post<Attachment>(`${base}/pessoas/${personId}/foto`, body, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  ).data;
}

export async function removePersonPhoto(personId: number) {
  await httpClient.delete(`${base}/pessoas/${personId}/foto`);
}

export async function removeAttachment(id: number) {
  await httpClient.delete(`${base}/anexos/${id}`);
}

export async function getAttachmentBlob(id: number, preview = false) {
  return (
    await httpClient.get<Blob>(`${base}/anexos/${id}/${preview ? 'preview' : 'download'}`, {
      responseType: 'blob',
    })
  ).data;
}

export async function downloadAttachment(item: Attachment) {
  const blob = await getAttachmentBlob(item.id);
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = item.arquivo.nome_original;
  anchor.click();
  URL.revokeObjectURL(url);
}
