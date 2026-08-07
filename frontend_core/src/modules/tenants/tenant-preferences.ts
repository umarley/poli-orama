import type { CommunityTerminology } from './types';

export const DEFAULT_COMMUNITY_TERMINOLOGY: CommunityTerminology = 'comunidades';

export interface CommunityTerminologyLabels {
  value: CommunityTerminology;
  singular: string;
  singularTitle: string;
  plural: string;
  pluralLower: string;
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
