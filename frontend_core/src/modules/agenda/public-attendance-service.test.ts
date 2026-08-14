import { beforeEach, describe, expect, it, vi } from 'vitest';

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));

vi.mock('axios', () => ({ default: { get, post } }));

vi.mock('@/config/env', () => ({
  env: { apiUrl: 'https://api.example.test' },
}));

import { confirmPublicAttendance, getPublicAttendanceEvent } from './public-attendance-service';

describe('serviço público de presença', () => {
  beforeEach(() => vi.clearAllMocks());

  it('consulta o evento pelo UUID público sem credenciais', async () => {
    get.mockResolvedValueOnce({ data: { uuid_publico: 'evento-uuid' } });

    await getPublicAttendanceEvent('evento-uuid');

    expect(get).toHaveBeenCalledWith(
      'https://api.example.test/api/v1/agenda/publico/eventos/evento-uuid/presenca',
      { timeout: 15_000 },
    );
  });

  it('envia os dados preenchidos pelo próprio participante', async () => {
    post.mockResolvedValueOnce({ data: { status: 'confirmada', message: 'OK' } });
    const payload = { nome_completo: 'Maria Silva', celular: '(62) 99999-1234' };

    await confirmPublicAttendance('evento-uuid', payload);

    expect(post).toHaveBeenCalledWith(
      'https://api.example.test/api/v1/agenda/publico/eventos/evento-uuid/presenca',
      payload,
      { timeout: 15_000, headers: { 'Content-Type': 'application/json' } },
    );
  });
});
