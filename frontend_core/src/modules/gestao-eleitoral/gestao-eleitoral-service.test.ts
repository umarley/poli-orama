import { beforeEach, describe, expect, it, vi } from 'vitest';

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));

vi.mock('@/services/api/http-client', () => ({
  httpClient: { get, post },
}));

import {
  exportElectoralMap,
  getElectoralZoneMeshes,
  getElectoralZoneResults,
  getElectoralPanel,
  omitElectoralFilters,
  searchElectoralCandidates,
  serializeElectoralParams,
} from './gestao-eleitoral-service';

describe('gestao-eleitoral-service', () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
  });

  it('omite o próprio recorte para o dropdown continuar listando as demais opções', () => {
    expect(
      omitElectoralFilters(
        { eleicao_chaves: ['2024:1:1'], ds_cargo: ['Prefeito'], nm_votaveis: ['Ana'] },
        'ds_cargo',
        'nm_votaveis',
      ),
    ).toEqual({ eleicao_chaves: ['2024:1:1'] });
  });

  it('serializa candidatos como parâmetros repetidos, sem colchetes', () => {
    const { paramsSerializer } = serializeElectoralParams(
      { eleicao_chaves: ['2024:1:1'], nm_votaveis: ['FÁBIO TOKARSKI', 'FABIO TOKARSKI'] },
      { q: 'fab' },
    );

    expect(
      paramsSerializer.serialize({
        eleicao_chaves: ['2024:1:1'],
        nm_votaveis: ['FÁBIO TOKARSKI', 'FABIO TOKARSKI'],
        q: 'fab',
      }),
    ).toBe(
      'eleicao_chaves=2024%3A1%3A1&nm_votaveis=F%C3%81BIO+TOKARSKI&nm_votaveis=FABIO+TOKARSKI&q=fab',
    );
  });

  it('pesquisa candidatos com o recorte atual', async () => {
    get.mockResolvedValueOnce({
      data: [{ nm_votavel: 'Ana', nr_votavel: 10, ds_cargo: 'Prefeito' }],
    });

    await searchElectoralCandidates(
      { eleicao_chaves: ['2024:1:1'], ds_cargo: ['Prefeito'] },
      'ana',
    );

    expect(get).toHaveBeenCalledWith(
      '/api/v1/gestao-eleitoral/filtros/candidatos',
      expect.objectContaining({
        params: expect.objectContaining({
          q: 'ana',
          eleicao_chaves: ['2024:1:1'],
          ds_cargo: ['Prefeito'],
        }),
      }),
    );
  });

  it('carrega o painel agregado com timeout estendido', async () => {
    get.mockResolvedValueOnce({
      data: {
        indicadores: {
          total_votos: 1,
          candidatos: 1,
          municipios: 1,
          zonas: 1,
          locais: 1,
          secoes: 1,
        },
        ranking: [],
        comparativo: [],
        por_municipio: [],
        por_zona: [],
        por_local: [],
        por_secao: [],
      },
    });

    await getElectoralPanel({ eleicao_chaves: ['2024:1:1'] });

    expect(get).toHaveBeenCalledWith(
      '/api/v1/gestao-eleitoral/painel',
      expect.objectContaining({ timeout: 60_000 }),
    );
  });

  it('carrega malhas pela área visível sem acoplar os filtros de candidato', async () => {
    get.mockResolvedValueOnce({ data: [] });

    await getElectoralZoneMeshes(
      { cd_municipio: [9373], nr_zona: [133] },
      { south: -17, west: -50, north: -16, east: -49 },
    );

    expect(get).toHaveBeenCalledWith(
      '/api/v1/gestao-eleitoral/mapa/zonas-eleitorais/malhas',
      expect.objectContaining({
        params: expect.objectContaining({
          cd_municipio: [9373],
          nr_zona: [133],
          sul: -17,
          oeste: -50,
          norte: -16,
          leste: -49,
        }),
        timeout: 60_000,
      }),
    );
  });

  it('envia todos os filtros para a agregação de votos por zona', async () => {
    get.mockResolvedValueOnce({ data: [] });
    const filters = {
      eleicao_chaves: ['2024:1:1'],
      ds_cargo: ['Prefeito'],
      nm_votaveis: ['Ana', 'Bia'],
      nr_zona: [133],
    };

    await getElectoralZoneResults(filters);

    expect(get).toHaveBeenCalledWith(
      '/api/v1/gestao-eleitoral/mapa/zonas-eleitorais/resultados',
      expect.objectContaining({ params: filters, timeout: 60_000 }),
    );
  });

  it('exporta o recorte atual no formato e nível de agregação selecionados', async () => {
    const blob = new Blob(['arquivo']);
    const click = vi.fn();
    const createElement = vi.spyOn(document, 'createElement').mockReturnValue({
      click,
      href: '',
      download: '',
    } as unknown as HTMLAnchorElement);
    const createObjectURL = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:exportacao');
    const revokeObjectURL = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);
    post.mockResolvedValueOnce({ data: blob });
    const filters = {
      eleicao_chaves: ['2024:1:1'],
      nm_votaveis: ['Ana', 'Bia'],
      nr_zona: [133],
    };

    await exportElectoralMap(filters, 'zona', 'xlsx');

    expect(post).toHaveBeenCalledWith(
      '/api/v1/gestao-eleitoral/mapa/exportacoes',
      { formato: 'xlsx', modo: 'zona', filtros: filters },
      { responseType: 'blob', timeout: 60_000 },
    );
    expect(createObjectURL).toHaveBeenCalledWith(blob);
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:exportacao');
    createElement.mockRestore();
    createObjectURL.mockRestore();
    revokeObjectURL.mockRestore();
  });
});
