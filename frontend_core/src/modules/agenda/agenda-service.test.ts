import { beforeEach, describe, expect, it, vi } from 'vitest';

const { get, post, remove } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  remove: vi.fn(),
}));

vi.mock('@/services/api/http-client', () => ({
  httpClient: {
    get,
    post,
    put: vi.fn(),
    patch: vi.fn(),
    delete: remove,
  },
}));

import { addParticipant, getEvent, removeParticipant } from './agenda-service';

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

  it.each([12, 'd9428888-122b-4c92-a30c-8625cc9466a4'])(
    'consulta diretamente o evento por ID ou UUID: %s',
    async (identifier) => {
      get.mockResolvedValueOnce({ data: {} });

      await getEvent(identifier);

      expect(get).toHaveBeenCalledWith(`/api/v1/agenda/eventos/${identifier}`);
    },
  );
});
