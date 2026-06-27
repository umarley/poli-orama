export interface Pessoa {
  id: string;
  nome: string;
  telefone: string;
  bairro: string;
  lideranca: string;
  status: 'ativo' | 'inativo';
  atualizadoEm: string;
}
