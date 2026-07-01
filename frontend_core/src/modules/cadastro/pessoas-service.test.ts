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
  atualizarContato,
  criarPessoa,
  listarPessoas,
  obterGrafoIndicacoes,
  resolverValidacao,
} from './pessoas-service';

describe('serviços de cadastro', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('envia filtros e paginação para a listagem', async () => {
    get.mockResolvedValueOnce({ data: { items: [], total: 0, page: 2, page_size: 20 } });

    await listarPessoas({ page: 2, page_size: 20, query: 'Maria', tag_id: 4 });

    expect(get).toHaveBeenCalledWith('/api/v1/cadastro/pessoas', {
      params: { page: 2, page_size: 20, query: 'Maria', tag_id: 4 },
    });
  });

  it('envia o cadastro completo para o backend', async () => {
    post.mockResolvedValueOnce({ data: { id: 9 } });
    const payload = {
      nome_completo: 'Maria da Silva',
      documentos: [],
      contatos: [],
      enderecos: [],
      redes_sociais: [],
      tipo_ids: [],
    };

    await criarPessoa(payload);

    expect(post).toHaveBeenCalledWith('/api/v1/cadastro/pessoas', payload);
  });

  it('usa a rota de edição de contato da pessoa', async () => {
    patch.mockResolvedValueOnce({ data: {} });

    await atualizarContato(10, 20, { valor: '11999999999' });

    expect(patch).toHaveBeenCalledWith('/api/v1/cadastro/pessoas/10/contatos/20', {
      valor: '11999999999',
    });
  });

  it('resolve a validação com decisão e observação', async () => {
    patch.mockResolvedValueOnce({ data: { id: 7 } });

    await resolverValidacao(7, 'aprovado', 'Conferido');

    expect(patch).toHaveBeenCalledWith('/api/v1/cadastro/validacoes/7', {
      status: 'aprovado',
      observacao: 'Conferido',
    });
  });

  it('consulta o grafo com filtros de pessoa e profundidade', async () => {
    get.mockResolvedValueOnce({
      data: { nodes: [], edges: [], total_edges: 0, truncated: false },
    });

    await obterGrafoIndicacoes({ pessoa_id: 10, profundidade: 4 });

    expect(get).toHaveBeenCalledWith('/api/v1/cadastro/indicacoes/grafo', {
      params: { pessoa_id: 10, profundidade: 4, limite: 300 },
    });
  });
});
