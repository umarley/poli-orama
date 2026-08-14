import { describe, expect, it } from 'vitest';

import {
  DEFAULT_REGISTRATION_FORM_PREFERENCES,
  getRegistrationFormPreferences,
  initialContactRows,
  initialDocumentRows,
  isRequiredContactType,
  isRequiredDocumentType,
  missingRequiredContactLabel,
  missingRequiredDocumentLabel,
  normalizeRegistrationFormPreferences,
} from './registration-form-preferences';

describe('preferências do formulário de cadastro', () => {
  it('mantém nome completo obrigatório e o restante opcional por padrão', () => {
    expect(getRegistrationFormPreferences()).toEqual(DEFAULT_REGISTRATION_FORM_PREFERENCES);
    expect(getRegistrationFormPreferences({ preferencias: {} }).nome_completo).toBe(true);
  });

  it('ignora tentativas de tornar o nome completo opcional', () => {
    const preferences = getRegistrationFormPreferences({
      preferencias: {
        formulario_cadastro: {
          nome_completo: false,
          sexo: true,
          documento: { CPF: true, RG: false, CNH: false },
          canal: { WhatsApp: true, Celular: false, Telefone: false, 'E-mail': false },
        },
      },
    });

    expect(preferences.nome_completo).toBe(true);
    expect(preferences.sexo).toBe(true);
    expect(preferences.documento.CPF).toBe(true);
    expect(preferences.canal.WhatsApp).toBe(true);
  });

  it('não interpreta strings como booleanos', () => {
    const preferences = getRegistrationFormPreferences({
      preferencias: {
        formulario_cadastro: {
          data_nascimento: 'true',
          documento: { CPF: 'true' },
        },
      },
    });

    expect(preferences.data_nascimento).toBe(false);
    expect(preferences.documento.CPF).toBe(false);
  });

  it('normaliza o payload salvo com nome completo sempre verdadeiro', () => {
    const normalized = normalizeRegistrationFormPreferences({
      nome_completo: false,
      titulo_eleitoral: true,
    });

    expect(normalized.nome_completo).toBe(true);
    expect(normalized.titulo_eleitoral).toBe(true);
    expect(normalized.documento).toEqual({ CPF: false, RG: false, CNH: false });
  });

  it('identifica documentos e canais obrigatórios no formulário', () => {
    const preferences = normalizeRegistrationFormPreferences({
      documento: { CPF: true, RG: true, CNH: false },
      canal: { WhatsApp: false, Celular: true, Telefone: false, 'E-mail': true },
    });

    expect(isRequiredDocumentType('cpf', preferences)).toBe(true);
    expect(isRequiredDocumentType('cnh', preferences)).toBe(false);
    expect(isRequiredContactType('celular', preferences)).toBe(true);
    expect(isRequiredContactType('whatsapp', preferences)).toBe(false);
    expect(initialDocumentRows(preferences)).toEqual([
      { tipo_documento: 'cpf' },
      { tipo_documento: 'rg' },
    ]);
    expect(initialContactRows(preferences)).toEqual([
      { tipo_contato: 'celular' },
      { tipo_contato: 'email' },
    ]);
    expect(
      missingRequiredDocumentLabel([{ tipo_documento: 'cpf', numero: '52998224725' }], preferences),
    ).toBe('RG');
    expect(
      missingRequiredContactLabel([{ tipo_contato: 'celular', valor: '11999999999' }], preferences),
    ).toBe('E-mail');
  });
});
