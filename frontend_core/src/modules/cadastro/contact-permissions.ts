import type { PessoaDetalhe } from '@/modules/cadastro/types';

const MANAGER_PROFILES = new Set(['gestor', 'gestor_saas']);

export function canRemovePersonContact(
  profiles: string[],
  liderancaId: number | null | undefined,
  person: Pick<PessoaDetalhe, 'cadastrado_por_lideranca_id' | 'hierarquia' | 'lideranca'> | null,
): boolean {
  if (profiles.some((profile) => MANAGER_PROFILES.has(profile))) {
    return true;
  }
  if (!profiles.includes('coordenador_territorial') || !liderancaId || !person) {
    return false;
  }
  if (person.lideranca?.id === liderancaId || person.lideranca?.coordenador_id === liderancaId) {
    return true;
  }
  if (person.cadastrado_por_lideranca_id === liderancaId) {
    return true;
  }
  return person.hierarquia.some(
    (item) => item.ativo && item.lideranca_superior_id === liderancaId,
  );
}
