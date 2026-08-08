import { beforeEach, describe, expect, it, vi } from 'vitest';

const { get, post, put, patch, remove } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  patch: vi.fn(),
  remove: vi.fn(),
}));

vi.mock('@/services/api/http-client', () => ({
  httpClient: { get, post, put, patch, delete: remove },
}));

import {
  atualizarContato,
  atualizarRedeSocial,
  criarContato,
  criarDocumento,
  criarPessoa,
  criarRedeSocial,
  definirEleitor,
  definirLideranca,
  listarHierarquia,
  listarDuplicidades,
  listarLiderancas,
  listarPessoas,
  listarReligioes,
  obterGrafoIndicacoes,
  obterPreviewMerge,
  obterResumoDuplicidades,
  mesclarDuplicidade,
  resolverDuplicidade,
  resolverValidacao,
  substituirTiposPessoa,
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

  it('substitui os tipos vinculados à pessoa', async () => {
    put.mockResolvedValueOnce({ data: [] });

    await substituirTiposPessoa(10, [1, 3]);

    expect(put).toHaveBeenCalledWith('/api/v1/cadastro/pessoas/10/tipos', {
      tipo_ids: [1, 3],
    });
  });

  it('lista o catálogo de religiões', async () => {
    get.mockResolvedValueOnce({ data: [] });

    await listarReligioes();

    expect(get).toHaveBeenCalledWith('/api/v1/cadastro/religioes');
  });

  it('adiciona e atualiza uma rede social da pessoa', async () => {
    const payload = {
      rede: 'instagram' as const,
      usuario_perfil: '@pessoa',
      url: 'https://instagram.com/pessoa',
      seguidores: 120,
    };
    post.mockResolvedValueOnce({ data: { id: 1, ...payload } });
    patch.mockResolvedValueOnce({ data: { id: 1, ...payload } });

    await criarRedeSocial(10, payload);
    await atualizarRedeSocial(10, 1, payload);

    expect(post).toHaveBeenCalledWith('/api/v1/cadastro/pessoas/10/redes-sociais', payload);
    expect(patch).toHaveBeenCalledWith('/api/v1/cadastro/pessoas/10/redes-sociais/1', payload);
  });

  it('envia os filtros da tabela de lideranças para a API', async () => {
    get.mockResolvedValueOnce({ data: [] });

    await listarLiderancas({ query: 'Fabio', coordenador_id: 2, territorio_id: 3 });

    expect(get).toHaveBeenCalledWith('/api/v1/cadastro/liderancas', {
      params: { query: 'Fabio', coordenador_id: 2, territorio_id: 3 },
    });
  });

  it('envia o tipo de liderança usado no seletor de responsável', async () => {
    get.mockResolvedValueOnce({ data: [] });

    await listarLiderancas({ tipo_lideranca: 'lider' });

    expect(get).toHaveBeenCalledWith('/api/v1/cadastro/liderancas', {
      params: { tipo_lideranca: 'lider' },
    });
  });

  it('carrega o resumo das ocorrências de duplicidade', async () => {
    get.mockResolvedValueOnce({
      data: { pendentes: 10, confirmadas: 4, descartadas: 3, mescladas: 2 },
    });

    await obterResumoDuplicidades();

    expect(get).toHaveBeenCalledWith('/api/v1/cadastro/duplicidades/resumo');
  });

  it('envia os filtros da hierarquia para a API', async () => {
    get.mockResolvedValueOnce({ data: [] });

    await listarHierarquia({
      pessoa_query: 'Simone',
      lideranca_superior_id: 292,
      papel_subordinado: 'apoiador',
    });

    expect(get).toHaveBeenCalledWith('/api/v1/cadastro/hierarquia', {
      params: {
        pessoa_query: 'Simone',
        lideranca_superior_id: 292,
        papel_subordinado: 'apoiador',
      },
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

  it('usa a rota de criacao de contato da pessoa', async () => {
    const payload = {
      tipo_contato: 'whatsapp' as const,
      valor: '(11) 99999-9999',
      principal: false,
      observacao: null,
    };
    post.mockResolvedValueOnce({ data: { id: 30, ...payload } });

    await criarContato(10, payload);

    expect(post).toHaveBeenCalledWith('/api/v1/cadastro/pessoas/10/contatos', payload);
  });

  it('usa a rota de criacao de documento da pessoa', async () => {
    const payload = {
      tipo_documento: 'rg' as const,
      numero: '1234567',
      orgao_emissor: 'SSP',
      uf_emissor: 'SP',
    };
    post.mockResolvedValueOnce({ data: { id: 40, ...payload } });

    await criarDocumento(10, payload);

    expect(post).toHaveBeenCalledWith('/api/v1/cadastro/pessoas/10/documentos', payload);
  });

  it('usa a rota de definicao de eleitor da pessoa', async () => {
    const payload = {
      titulo_eleitor: '123456789012',
      codigo_municipio_ibge: 5201405,
      zona_eleitoral_id: 1,
      secao_eleitoral_id: 2,
      local_votacao_id: 3,
      situacao_titulo: 'regular' as const,
    };
    put.mockResolvedValueOnce({ data: { id: 50, ...payload } });

    await definirEleitor(10, payload);

    expect(put).toHaveBeenCalledWith('/api/v1/cadastro/pessoas/10/eleitor', payload);
  });

  it('usa a rota de definicao de lideranca da pessoa', async () => {
    const payload = {
      tipo_lideranca: 'coordenador_geral' as const,
      coordenador_id: null,
      apelido_campanha: 'Coordenação geral',
      ativo: true,
    };
    put.mockResolvedValueOnce({ data: { id: 60, pessoa_id: 10, ...payload } });

    await definirLideranca(10, payload);

    expect(put).toHaveBeenCalledWith('/api/v1/cadastro/pessoas/10/lideranca', payload);
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

  it('lista suspeitas de duplicidade por situação', async () => {
    get.mockResolvedValueOnce({ data: [] });

    await listarDuplicidades('pendente');

    expect(get).toHaveBeenCalledWith('/api/v1/cadastro/duplicidades', {
      params: { status: 'pendente' },
    });
  });

  it('consulta o preview do merge assistido', async () => {
    get.mockResolvedValueOnce({ data: { suspeita_id: 8, conflitos: [] } });

    await obterPreviewMerge(8);

    expect(get).toHaveBeenCalledWith('/api/v1/cadastro/duplicidades/8/merge-preview');
  });

  it('confirma ou descarta uma suspeita', async () => {
    patch.mockResolvedValueOnce({ data: { id: 8, status: 'descartada' } });

    await resolverDuplicidade(8, 'falso_positivo');

    expect(patch).toHaveBeenCalledWith('/api/v1/cadastro/duplicidades/8', {
      decisao: 'falso_positivo',
    });
  });

  it('envia a escolha de principal e campos para o merge', async () => {
    post.mockResolvedValueOnce({ data: { merge_id: 3 } });
    const payload = {
      pessoa_principal_id: 10,
      campos_origem: ['apelido'] as ['apelido'],
      confirmar: true as const,
    };

    await mesclarDuplicidade(8, payload);

    expect(post).toHaveBeenCalledWith('/api/v1/cadastro/duplicidades/8/merge', payload);
  });
});
