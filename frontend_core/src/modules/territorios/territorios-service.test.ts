import { beforeEach, describe, expect, it, vi } from 'vitest';

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));

vi.mock('@/services/api/http-client', () => ({
  httpClient: { get, post },
}));

import {
  listarTerritorios,
  obterShapesMunicipios,
  obterPreviaOrganizacaoHierarquia,
  organizarHierarquia,
} from '@/modules/territorios/territorios-service';

describe('territorios-service', () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
  });

  it('envia o termo de pesquisa ao listar territórios', async () => {
    get.mockResolvedValueOnce({ data: [] });

    await expect(listarTerritorios(false, 'Norte')).resolves.toEqual([]);
    expect(get).toHaveBeenCalledWith('/api/v1/territorios', {
      params: { incluir_inativos: false, query: 'Norte' },
    });
  });

  it('carrega a prévia e confirma as alterações da hierarquia', async () => {
    const preview = {
      hierarquia_atual: [],
      hierarquia_proposta: [],
      alteracoes: [],
      pendencias: [],
    };
    get.mockResolvedValueOnce({ data: preview });

    await expect(obterPreviaOrganizacaoHierarquia()).resolves.toEqual(preview);
    expect(get).toHaveBeenCalledWith('/api/v1/territorios/hierarquia/organizacao');

    post.mockResolvedValueOnce({ data: { atualizados: 1 } });
    const changes = [{ territorio_id: 3, territorio_pai_id: 2 }];
    await expect(organizarHierarquia(changes)).resolves.toEqual({ atualizados: 1 });
    expect(post).toHaveBeenCalledWith('/api/v1/territorios/hierarquia/organizacao', {
      alteracoes: changes,
    });
  });

  it('carrega os shapes municipais pelo backend da aplicação', async () => {
    const shapes = [
      {
        territorio_id: 10,
        codigo_municipio_ibge: 5208707,
        nome: 'Goiânia',
        cor: '#12AB34',
        quantidade_eleitores: 99999,
        quantidade_pessoas: 125,
        geometry: { type: 'MultiPolygon', coordinates: [] },
      },
    ];
    get.mockResolvedValueOnce({ data: shapes });

    await expect(obterShapesMunicipios()).resolves.toEqual(shapes);
    expect(get).toHaveBeenCalledWith('/api/v1/territorios/mapa/malhas', {
      params: { tipo: 'municipio', territorio_id: undefined },
    });
  });

  it('filtra os shapes municipais por território selecionado', async () => {
    get.mockResolvedValueOnce({ data: [] });

    await expect(obterShapesMunicipios(10)).resolves.toEqual([]);
    expect(get).toHaveBeenCalledWith('/api/v1/territorios/mapa/malhas', {
      params: { tipo: 'municipio', territorio_id: 10 },
    });
  });
});
