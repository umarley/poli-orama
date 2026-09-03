import { beforeEach, describe, expect, it, vi } from 'vitest';

const { get } = vi.hoisted(() => ({ get: vi.fn() }));

vi.mock('@/services/api/http-client', () => ({
  httpClient: { get },
}));

import {
  getElectoralPanel,
  omitElectoralFilters,
  searchElectoralCandidates,
  serializeElectoralParams,
} from './gestao-eleitoral-service';

describe('gestao-eleitoral-service', () => {
  beforeEach(() => {
    get.mockReset();
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

    expect(paramsSerializer.serialize({
      eleicao_chaves: ['2024:1:1'],
      nm_votaveis: ['FÁBIO TOKARSKI', 'FABIO TOKARSKI'],
      q: 'fab',
    })).toBe(
      'eleicao_chaves=2024%3A1%3A1&nm_votaveis=F%C3%81BIO+TOKARSKI&nm_votaveis=FABIO+TOKARSKI&q=fab',
    );
  });

  it('pesquisa candidatos com o recorte atual', async () => {
    get.mockResolvedValueOnce({ data: [{ nm_votavel: 'Ana', nr_votavel: 10, ds_cargo: 'Prefeito' }] });

    await searchElectoralCandidates({ eleicao_chaves: ['2024:1:1'], ds_cargo: ['Prefeito'] }, 'ana');

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
        indicadores: { total_votos: 1, candidatos: 1, municipios: 1, zonas: 1, locais: 1, secoes: 1 },
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
});
