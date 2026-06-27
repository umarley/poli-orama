import type { FilterValues } from '@/components/form/BaseFilterBar';
import type { Pessoa } from '@/modules/cadastro/types';
import type { PaginatedResponse } from '@/types/api';

const pessoas: Pessoa[] = [
  {
    id: '1',
    nome: 'Ana Beatriz Souza',
    telefone: '(11) 98842-1120',
    bairro: 'Jardim Aurora',
    lideranca: 'Carlos Mendes',
    status: 'ativo',
    atualizadoEm: 'Hoje, 09:42',
  },
  {
    id: '2',
    nome: 'Rafael Oliveira',
    telefone: '(11) 97441-0288',
    bairro: 'Vila Esperança',
    lideranca: 'Juliana Rocha',
    status: 'ativo',
    atualizadoEm: 'Ontem, 17:30',
  },
  {
    id: '3',
    nome: 'Marcos Vinícius Lima',
    telefone: '(11) 95618-4472',
    bairro: 'Centro',
    lideranca: 'Carlos Mendes',
    status: 'inativo',
    atualizadoEm: '24 jun, 15:12',
  },
  {
    id: '4',
    nome: 'Luciana Alves',
    telefone: '(11) 99310-6635',
    bairro: 'Parque das Flores',
    lideranca: 'Fernanda Reis',
    status: 'ativo',
    atualizadoEm: '23 jun, 11:08',
  },
  {
    id: '5',
    nome: 'João Pedro Nascimento',
    telefone: '(11) 98002-3417',
    bairro: 'Jardim Primavera',
    lideranca: 'Juliana Rocha',
    status: 'ativo',
    atualizadoEm: '22 jun, 16:45',
  },
];

export async function listarPessoas(filters: FilterValues): Promise<PaginatedResponse<Pessoa>> {
  await new Promise((resolve) => window.setTimeout(resolve, 450));

  const search = filters.search?.trim().toLocaleLowerCase('pt-BR');
  const filtered = pessoas.filter((pessoa) => {
    const matchesSearch =
      !search ||
      [pessoa.nome, pessoa.bairro, pessoa.lideranca].some((value) =>
        value.toLocaleLowerCase('pt-BR').includes(search),
      );
    const matchesStatus = !filters.status || pessoa.status === filters.status;
    return matchesSearch && matchesStatus;
  });

  return {
    items: filtered,
    total: filtered.length,
    page: 1,
    page_size: 10,
  };
}
