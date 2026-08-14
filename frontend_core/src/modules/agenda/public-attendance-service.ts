import axios from 'axios';

import { env } from '@/config/env';
import type {
  PublicAttendanceEvent,
  PublicAttendanceInput,
  PublicAttendanceResult,
} from '@/modules/agenda/types';
import { normalizeApiError } from '@/services/api/api-error';

function attendanceEndpoint(publicId: string) {
  const apiOrigin = env.apiUrl.replace(/\/api\/v1\/?$/, '').replace(/\/$/, '');
  return `${apiOrigin}/api/v1/agenda/publico/eventos/${encodeURIComponent(publicId)}/presenca`;
}

export async function getPublicAttendanceEvent(publicId: string) {
  try {
    const { data } = await axios.get<PublicAttendanceEvent>(attendanceEndpoint(publicId), {
      timeout: 15_000,
    });
    return data;
  } catch (error) {
    throw normalizeApiError(error);
  }
}

export async function confirmPublicAttendance(publicId: string, payload: PublicAttendanceInput) {
  try {
    const { data } = await axios.post<PublicAttendanceResult>(
      attendanceEndpoint(publicId),
      payload,
      {
        timeout: 15_000,
        headers: { 'Content-Type': 'application/json' },
      },
    );
    return data;
  } catch (error) {
    throw normalizeApiError(error);
  }
}
