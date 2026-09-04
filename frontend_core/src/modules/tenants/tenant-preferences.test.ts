import { describe, expect, it } from 'vitest';

import {
  getCommunityTerminology,
  getCommunityTerminologyLabels,
  getLeadershipTerminology,
  getLeadershipTerminologyLabels,
  getMaxSimultaneousAttendances,
} from './tenant-preferences';

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
      singularTitle: 'Frente',
      plural: 'Frentes',
      pluralLower: 'frentes',
    });
  });

  it('mantém o padrão diante de um valor antigo ou inválido', () => {
    const configuration = { preferencias: { nomenclatura_comunidades: 'grupos' } };

    expect(getCommunityTerminology(configuration)).toBe('comunidades');
  });

  it('usa Lideranças como padrão quando a preferência não está configurada', () => {
    expect(getLeadershipTerminology()).toBe('liderancas');
    expect(getLeadershipTerminologyLabels(null)).toMatchObject({
      menu: 'Lideranças',
      registeredTitle: 'Lideranças cadastradas',
      columnTitle: 'Liderança',
      eventColumnTitle: 'Liderança',
      activeTitle: 'Lideranças ativas',
    });
  });

  it('aplica a nomenclatura de Coordenadores', () => {
    const configuration = {
      preferencias: { nomenclatura_liderancas: 'coordenadores' },
    } as const;

    expect(getLeadershipTerminology(configuration)).toBe('coordenadores');
    expect(getLeadershipTerminologyLabels(configuration)).toMatchObject({
      menu: 'Coordenadores',
      registeredTitle: 'Coordenadores cadastrados',
      columnTitle: 'Coordenador',
      eventColumnTitle: 'Coordenação',
      activeTitle: 'Coordenações ativas',
    });
  });

  it('mantém Lideranças diante de uma nomenclatura inválida', () => {
    const configuration = { preferencias: { nomenclatura_liderancas: 'chefes' } };

    expect(getLeadershipTerminology(configuration)).toBe('liderancas');
  });

  it('usa 10 atendimentos simultâneos quando a preferência não está configurada', () => {
    expect(getMaxSimultaneousAttendances()).toBe(10);
    expect(getMaxSimultaneousAttendances({ preferencias: {} })).toBe(10);
  });

  it('respeita o limite configurado pelo tenant', () => {
    expect(
      getMaxSimultaneousAttendances({ preferencias: { maximo_atendimentos_simultaneos: 6 } }),
    ).toBe(6);
  });
});
