import { describe, expect, it } from 'vitest';

import { canRemovePersonContact } from './contact-permissions';
import type { PessoaDetalhe } from './types';

function person(
  overrides: Partial<Pick<PessoaDetalhe, 'cadastrado_por_lideranca_id' | 'hierarquia' | 'lideranca'>> = {},
): Pick<PessoaDetalhe, 'cadastrado_por_lideranca_id' | 'hierarquia' | 'lideranca'> {
  return {
    cadastrado_por_lideranca_id: null,
    hierarquia: [],
    lideranca: null,
    ...overrides,
  };
}

describe('canRemovePersonContact', () => {
  it('libera gestores independentemente do vínculo', () => {
    expect(canRemovePersonContact(['gestor'], null, person())).toBe(true);
    expect(canRemovePersonContact(['gestor_saas'], 9, person())).toBe(true);
  });

  it('bloqueia outros perfis, inclusive liderança comum', () => {
    expect(canRemovePersonContact(['lider'], 5, person({ cadastrado_por_lideranca_id: 5 }))).toBe(
      false,
    );
  });

  it('libera coordenador territorial quando a pessoa está na hierarquia', () => {
    expect(
      canRemovePersonContact(
        ['coordenador_territorial'],
        5,
        person({
          hierarquia: [
            {
              id: 1,
              lideranca_superior_id: 5,
              lideranca_superior_nome: 'Coordenador',
              papel_subordinado: 'liderado',
              ativo: true,
            },
          ],
        }),
      ),
    ).toBe(true);
  });

  it('libera coordenador territorial quando a pessoa foi cadastrada por ele', () => {
    expect(
      canRemovePersonContact(
        ['coordenador_territorial'],
        5,
        person({ cadastrado_por_lideranca_id: 5 }),
      ),
    ).toBe(true);
  });

  it('libera coordenador territorial quando a pessoa é a própria liderança ou está subordinada a ele', () => {
    expect(
      canRemovePersonContact(
        ['coordenador_territorial'],
        5,
        person({
          lideranca: {
            id: 5,
            tenant_id: 1,
            pessoa_id: 10,
            tipo_lideranca: 'coordenador_territorial',
            coordenador_id: null,
            apelido_campanha: null,
            ativo: true,
            criado_em: '2026-08-01T10:00:00Z',
            atualizado_em: '2026-08-01T10:00:00Z',
          },
        }),
      ),
    ).toBe(true);
    expect(
      canRemovePersonContact(
        ['coordenador_territorial'],
        5,
        person({
          lideranca: {
            id: 8,
            tenant_id: 1,
            pessoa_id: 11,
            tipo_lideranca: 'lider',
            coordenador_id: 5,
            apelido_campanha: null,
            ativo: true,
            criado_em: '2026-08-01T10:00:00Z',
            atualizado_em: '2026-08-01T10:00:00Z',
          },
        }),
      ),
    ).toBe(true);
  });

  it('bloqueia coordenador territorial sem vínculo com a pessoa', () => {
    expect(canRemovePersonContact(['coordenador_territorial'], 5, person())).toBe(false);
    expect(canRemovePersonContact(['coordenador_territorial'], null, person())).toBe(false);
  });
});
