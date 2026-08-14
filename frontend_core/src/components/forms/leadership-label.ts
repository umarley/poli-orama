import type { Lideranca } from '@/modules/cadastro/types';

export function formatLeadershipLabel(
  leadership: Pick<Lideranca, 'id' | 'pessoa_nome_completo' | 'apelido_campanha'>,
): string {
  const name = leadership.pessoa_nome_completo?.trim() || `Liderança #${leadership.id}`;
  const nickname = leadership.apelido_campanha?.trim();
  return nickname ? `${name} (${nickname})` : name;
}
