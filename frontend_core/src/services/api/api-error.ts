import axios from 'axios';

import type { ApiErrorPayload } from '@/types/api';

export class ApiError extends Error {
  readonly code: string;
  readonly details?: unknown;
  readonly status?: number;

  constructor(payload: ApiErrorPayload, status?: number) {
    super(payload.message);
    this.name = 'ApiError';
    this.code = payload.code;
    this.details = payload.details;
    this.status = status;
  }
}

export function normalizeApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;

  if (axios.isAxiosError<ApiErrorPayload>(error)) {
    const payload = error.response?.data;
    return new ApiError(
      {
        code: payload?.code ?? 'HTTP_ERROR',
        message:
          payload?.message ??
          (error.response ? 'Não foi possível concluir a solicitação.' : 'API indisponível.'),
        details: payload?.details,
      },
      error.response?.status,
    );
  }

  if (error instanceof Error) {
    return new ApiError({ code: 'UNEXPECTED_ERROR', message: error.message });
  }

  return new ApiError({
    code: 'UNEXPECTED_ERROR',
    message: 'Ocorreu um erro inesperado.',
  });
}
