import type { CommunityTerminology, LeadershipTerminology } from './types';

export const DEFAULT_COMMUNITY_TERMINOLOGY: CommunityTerminology = 'comunidades';
export const DEFAULT_LEADERSHIP_TERMINOLOGY: LeadershipTerminology = 'liderancas';

export interface CommunityTerminologyLabels {
  value: CommunityTerminology;
  singular: string;
  singularTitle: string;
  plural: string;
  pluralLower: string;
}

export interface LeadershipTerminologyLabels {
  value: LeadershipTerminology;
  menu: string;
  registeredTitle: string;
  columnTitle: string;
  eventColumnTitle: string;
  activeTitle: string;
}

export function getCommunityTerminology(
  configuration?: { preferencias?: Record<string, unknown> } | null,
): CommunityTerminology {
  return configuration?.preferencias?.nomenclatura_comunidades === 'frentes'
    ? 'frentes'
    : DEFAULT_COMMUNITY_TERMINOLOGY;
}

export function getCommunityTerminologyLabels(
  configuration?: { preferencias?: Record<string, unknown> } | null,
): CommunityTerminologyLabels {
  const value = getCommunityTerminology(configuration);
  if (value === 'frentes') {
    return {
      value,
      singular: 'frente',
      singularTitle: 'Frente',
      plural: 'Frentes',
      pluralLower: 'frentes',
    };
  }
  return {
    value,
    singular: 'comunidade',
    singularTitle: 'Comunidade',
    plural: 'Comunidades',
    pluralLower: 'comunidades',
  };
}

export function getLeadershipTerminology(
  configuration?: { preferencias?: Record<string, unknown> } | null,
): LeadershipTerminology {
  return configuration?.preferencias?.nomenclatura_liderancas === 'coordenadores'
    ? 'coordenadores'
    : DEFAULT_LEADERSHIP_TERMINOLOGY;
}

export function getLeadershipTerminologyLabels(
  configuration?: { preferencias?: Record<string, unknown> } | null,
): LeadershipTerminologyLabels {
  const value = getLeadershipTerminology(configuration);
  if (value === 'coordenadores') {
    return {
      value,
      menu: 'Coordenadores',
      registeredTitle: 'Coordenadores cadastrados',
      columnTitle: 'Coordenador',
      eventColumnTitle: 'Coordenação',
      activeTitle: 'Coordenações ativas',
    };
  }
  return {
    value,
    menu: 'Lideranças',
    registeredTitle: 'Lideranças cadastradas',
    columnTitle: 'Liderança',
    eventColumnTitle: 'Liderança',
    activeTitle: 'Lideranças ativas',
  };
}
