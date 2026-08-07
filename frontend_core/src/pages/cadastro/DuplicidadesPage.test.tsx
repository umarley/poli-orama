import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { PessoaDetalhe } from '@/modules/cadastro/types';

const { listDuplicates, getMergePreview, mergeDuplicate, resolveDuplicate } = vi.hoisted(() => ({
  listDuplicates: vi.fn(),
  getMergePreview: vi.fn(),
  mergeDuplicate: vi.fn(),
  resolveDuplicate: vi.fn(),
}));

vi.mock('@/modules/cadastro/pessoas-service', () => ({
  listarDuplicidades: listDuplicates,
  obterPreviewMerge: getMergePreview,
  mesclarDuplicidade: mergeDuplicate,
  resolverDuplicidade: resolveDuplicate,
}));

vi.mock('@/components/feedback/AppToast', () => ({
  AppToast: { success: vi.fn(), error: vi.fn() },
}));

import { DuplicidadesPage } from './DuplicidadesPage';

function person(id: number, name: string, nickname: string): PessoaDetalhe {
  return {
    id,
    uuid_publico: `person-${id}`,
    tenant_id: 1,
    nome_completo: name,
    nome_social: null,
    apelido: nickname,
    sexo: null,
    data_nascimento: '1980-05-10',
    estado_civil: null,
    escolaridade_id: null,
    profissao_id: null,
    religiao_id: null,
    observacoes: null,
    nivel_engajamento: null,
    score_confiabilidade: null,
    completude_cadastral: null,
    ativo: true,
    criado_por: 1,
    atualizado_por: null,
    criado_em: '2026-08-01T10:00:00Z',
    atualizado_em: '2026-08-01T10:00:00Z',
    excluido_em: null,
    documentos: [],
    contatos: [],
    enderecos: [],
    eleitor: null,
    lideranca: null,
    redes_sociais: [],
    tipos: [],
    indicacoes: [],
    complemento_politico: null,
    tags: [],
    comunidades: [],
    nucleos_familiares: [],
    hierarquia: [],
  };
}

describe('DuplicidadesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listDuplicates.mockResolvedValue([
      {
        id: 7,
        tenant_id: 1,
        pessoa_id: 10,
        pessoa_nome: 'Maria Principal',
        pessoa_duplicada_id: 20,
        pessoa_duplicada_nome: 'Maria Duplicada',
        criterio: 'telefone',
        score_similaridade: '100',
        status: 'pendente',
        resolvido_por: null,
        resolvido_em: null,
        criado_em: '2026-08-01T10:00:00Z',
      },
    ]);
    getMergePreview.mockResolvedValue({
      suspeita_id: 7,
      pessoa_a: person(10, 'Maria Principal', 'Mari'),
      pessoa_b: person(20, 'Maria Duplicada', 'Maria'),
      conflitos: [{ campo: 'apelido', valor_principal: 'Mari', valor_origem: 'Maria' }],
    });
    mergeDuplicate.mockResolvedValue({
      merge_id: 3,
      pessoa_principal: person(10, 'Maria Principal', 'Mari'),
      pessoa_origem_id: 20,
      resumo_operacao: {},
    });
  });

  it('abre a comparação e envia o merge confirmado', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <MemoryRouter>
        <QueryClientProvider client={client}>
          <DuplicidadesPage />
        </QueryClientProvider>
      </MemoryRouter>,
    );

    expect(await screen.findByText('Maria Principal')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /analisar merge/i }));

    expect(await screen.findByText('Resolver campos conflitantes')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: /confirmar merge/i }));

    await waitFor(() =>
      expect(mergeDuplicate).toHaveBeenCalledWith(7, {
        pessoa_principal_id: 10,
        campos_origem: [],
        confirmar: true,
      }),
    );
  }, 15_000);
});
