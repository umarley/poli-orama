import { beforeEach, describe, expect, it, vi } from 'vitest';

const { get, post, patch, remove } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  remove: vi.fn(),
}));

vi.mock('@/services/api/http-client', () => ({
  httpClient: { get, post, patch, delete: remove },
}));

import {
  createContract,
  deleteContract,
  listContracts,
  searchContractPeople,
  updateContract,
} from './contratos-service';

describe('serviço de contratos', () => {
  beforeEach(() => vi.clearAllMocks());

  it('lista contratos com filtros e pesquisa pessoas do cadastro existente', async () => {
    get.mockResolvedValue({ data: [] });

    await listContracts({ tipo_contratado: 'pf', situacao: 'ativo' });
    await searchContractPeople('Maria');

    expect(get).toHaveBeenNthCalledWith(1, '/api/v1/contratos', {
      params: { tipo_contratado: 'pf', situacao: 'ativo' },
    });
    expect(get).toHaveBeenNthCalledWith(2, '/api/v1/contratos/pessoas', {
      params: { q: 'Maria' },
    });
  });

  it('cria, atualiza e exclui pelo endpoint protegido', async () => {
    const payload = {
      tipo_contratado: 'pf' as const,
      pessoa_id: 10,
      funcao_cargo: 'Coordenador',
      valor_parcela: 2000,
      quantidade_parcelas: 2 as const,
      data_inicio: '2026-08-01',
      data_termino: '2026-08-31',
      status: 'ativo' as const,
    };
    post.mockResolvedValue({ data: {} });
    patch.mockResolvedValue({ data: {} });
    remove.mockResolvedValue({});

    await createContract(payload);
    await updateContract(7, { valor_parcela: 2500 });
    await deleteContract(7);

    expect(post).toHaveBeenCalledWith('/api/v1/contratos', payload);
    expect(patch).toHaveBeenCalledWith('/api/v1/contratos/7', { valor_parcela: 2500 });
    expect(remove).toHaveBeenCalledWith('/api/v1/contratos/7');
  });
});
