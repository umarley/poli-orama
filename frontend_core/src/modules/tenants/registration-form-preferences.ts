import type { TipoContato, TipoDocumento } from '@/modules/cadastro/types';

import type {
  RegistrationContactPreferences,
  RegistrationDocumentPreferences,
  RegistrationFormPreferences,
} from './types';

export const DEFAULT_REGISTRATION_FORM_PREFERENCES: RegistrationFormPreferences = {
  nome_completo: true,
  data_nascimento: false,
  sexo: false,
  estado_civil: false,
  documento: {
    CPF: false,
    RG: false,
    CNH: false,
  },
  canal: {
    WhatsApp: false,
    Celular: false,
    Telefone: false,
    'E-mail': false,
  },
  titulo_eleitoral: false,
};

const DOCUMENT_TYPES = ['CPF', 'RG', 'CNH'] as const;
const CONTACT_CHANNELS = ['WhatsApp', 'Celular', 'Telefone', 'E-mail'] as const;

const DOCUMENT_TYPE_BY_LABEL: Record<keyof RegistrationDocumentPreferences, TipoDocumento> = {
  CPF: 'cpf',
  RG: 'rg',
  CNH: 'cnh',
};

const CONTACT_TYPE_BY_LABEL: Record<keyof RegistrationContactPreferences, TipoContato> = {
  WhatsApp: 'whatsapp',
  Celular: 'celular',
  Telefone: 'telefone',
  'E-mail': 'email',
};

function asBoolean(value: unknown, fallback = false): boolean {
  return typeof value === 'boolean' ? value : fallback;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

export function getRegistrationFormPreferences(
  configuration?: { preferencias?: Record<string, unknown> } | null,
): RegistrationFormPreferences {
  const stored = asRecord(configuration?.preferencias?.formulario_cadastro);
  const documento = asRecord(stored.documento);
  const canal = asRecord(stored.canal);

  return {
    nome_completo: true,
    data_nascimento: asBoolean(stored.data_nascimento),
    sexo: asBoolean(stored.sexo),
    estado_civil: asBoolean(stored.estado_civil),
    documento: {
      CPF: asBoolean(documento.CPF),
      RG: asBoolean(documento.RG),
      CNH: asBoolean(documento.CNH),
    },
    canal: {
      WhatsApp: asBoolean(canal.WhatsApp),
      Celular: asBoolean(canal.Celular),
      Telefone: asBoolean(canal.Telefone),
      'E-mail': asBoolean(canal['E-mail']),
    },
    titulo_eleitoral: asBoolean(stored.titulo_eleitoral),
  };
}

export function normalizeRegistrationFormPreferences(
  value?: Partial<RegistrationFormPreferences> | null,
): RegistrationFormPreferences {
  return getRegistrationFormPreferences({
    preferencias: { formulario_cadastro: value ?? DEFAULT_REGISTRATION_FORM_PREFERENCES },
  });
}

export function requiredDocumentTypes(
  preferences: RegistrationFormPreferences,
): TipoDocumento[] {
  return DOCUMENT_TYPES.filter((label) => preferences.documento[label]).map(
    (label) => DOCUMENT_TYPE_BY_LABEL[label],
  );
}

export function requiredContactTypes(preferences: RegistrationFormPreferences): TipoContato[] {
  return CONTACT_CHANNELS.filter((label) => preferences.canal[label]).map(
    (label) => CONTACT_TYPE_BY_LABEL[label],
  );
}

export function isRequiredDocumentType(
  type: TipoDocumento | undefined,
  preferences: RegistrationFormPreferences,
): boolean {
  return Boolean(type && requiredDocumentTypes(preferences).includes(type));
}

export function isRequiredContactType(
  type: TipoContato | undefined,
  preferences: RegistrationFormPreferences,
): boolean {
  return Boolean(type && requiredContactTypes(preferences).includes(type));
}

export function initialDocumentRows(preferences: RegistrationFormPreferences) {
  const rows = requiredDocumentTypes(preferences).map((tipo_documento) => ({ tipo_documento }));
  return rows.length ? rows : [{ tipo_documento: 'cpf' as TipoDocumento }];
}

export function initialContactRows(preferences: RegistrationFormPreferences) {
  const rows = requiredContactTypes(preferences).map((tipo_contato) => ({ tipo_contato }));
  return rows.length ? rows : [{ tipo_contato: 'whatsapp' as TipoContato }];
}

export function missingRequiredDocumentLabel(
  documents: Array<{ tipo_documento?: TipoDocumento; numero?: string } | undefined> | undefined,
  preferences: RegistrationFormPreferences,
): string | null {
  for (const label of DOCUMENT_TYPES) {
    if (!preferences.documento[label]) continue;
    const type = DOCUMENT_TYPE_BY_LABEL[label];
    const found = (documents ?? []).some(
      (document) => document?.tipo_documento === type && Boolean(document.numero?.trim()),
    );
    if (!found) return label;
  }
  return null;
}

export function missingRequiredContactLabel(
  contacts: Array<{ tipo_contato?: TipoContato; valor?: string } | undefined> | undefined,
  preferences: RegistrationFormPreferences,
): string | null {
  for (const label of CONTACT_CHANNELS) {
    if (!preferences.canal[label]) continue;
    const type = CONTACT_TYPE_BY_LABEL[label];
    const found = (contacts ?? []).some(
      (contact) => contact?.tipo_contato === type && Boolean(contact.valor?.trim()),
    );
    if (!found) return label;
  }
  return null;
}
