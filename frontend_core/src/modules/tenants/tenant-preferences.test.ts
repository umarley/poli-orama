import { describe, expect, it } from 'vitest';

import { getCommunityTerminology, getCommunityTerminologyLabels } from './tenant-preferences';

describe('preferências de nomenclatura do tenant', () => {
  it('usa Comunidades quando a preferência não está configurada', () => {
    expect(getCommunityTerminology()).toBe('comunidades');
    expect(getCommunityTerminologyLabels(null).plural).toBe('Comunidades');
  });

  it('usa Frentes apenas quando esse valor está explicitamente configurado', () => {
    const configuration = { preferencias: { nomenclatura_comunidades: 'frentes' } } as const;

    expect(getCommunityTerminology(configuration)).toBe('frentes');
    expect(getCommunityTerminologyLabels(configuration)).toMatchObject({
      singular: 'frente',
      plural: 'Frentes',
    });
  });

  it('mantém o padrão diante de um valor antigo ou inválido', () => {
    const configuration = { preferencias: { nomenclatura_comunidades: 'grupos' } };

    expect(getCommunityTerminology(configuration)).toBe('comunidades');
  });
});
