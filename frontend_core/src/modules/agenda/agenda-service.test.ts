import { beforeEach, describe, expect, it, vi } from 'vitest';

const { post, remove } = vi.hoisted(() => ({
  post: vi.fn(),
  remove: vi.fn(),
}));

vi.mock('@/services/api/http-client', () => ({
  httpClient: {
    get: vi.fn(),
    post,
    put: vi.fn(),
    patch: vi.fn(),
    delete: remove,
  },
}));

import { addParticipant, removeParticipant } from './agenda-service';

describe('serviços de participantes do evento', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('salva os dados individuais do participante', async () => {
    post.mockResolvedValueOnce({ data: {} });
    const payload = {
      pessoa_id: 25,
      papel: 'Convidada',
      presente: true,
      observacao: 'Chegou no horário',
    };

    await addParticipant(12, payload);

    expect(post).toHaveBeenCalledWith('/api/v1/agenda/eventos/12/participantes', payload);
  });

  it('remove a pessoa do evento', async () => {
    remove.mockResolvedValueOnce({});

    await removeParticipant(12, 25);

    expect(remove).toHaveBeenCalledWith('/api/v1/agenda/eventos/12/participantes/25');
  });
});
