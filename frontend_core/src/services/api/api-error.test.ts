import axios from 'axios';

import { normalizeApiError } from '@/services/api/api-error';

describe('normalizeApiError', () => {
  it('preserva o padrão de erro retornado pela API', () => {
    const error = new axios.AxiosError('Bad request', 'ERR_BAD_REQUEST', undefined, undefined, {
      data: {
        code: 'VALIDATION_ERROR',
        message: 'Dados inválidos.',
        details: { email: ['Formato inválido.'] },
      },
      status: 422,
      statusText: 'Unprocessable Entity',
      headers: {},
      config: { headers: new axios.AxiosHeaders() },
    });

    const normalized = normalizeApiError(error);

    expect(normalized.code).toBe('VALIDATION_ERROR');
    expect(normalized.message).toBe('Dados inválidos.');
    expect(normalized.status).toBe(422);
  });

  it('normaliza falhas de conexão', () => {
    const normalized = normalizeApiError(new axios.AxiosError('Network Error'));

    expect(normalized.code).toBe('HTTP_ERROR');
    expect(normalized.message).toBe('API indisponível.');
  });
});
