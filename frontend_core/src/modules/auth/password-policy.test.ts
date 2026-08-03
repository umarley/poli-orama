import { describe, expect, it } from 'vitest';

import { evaluatePasswordStrength } from '@/modules/auth/password-policy';

describe('evaluatePasswordStrength', () => {
  it('retorna vazio quando a senha nao foi informada', () => {
    expect(evaluatePasswordStrength('')).toMatchObject({ level: 'empty', score: 0 });
  });

  it('classifica senha fraca quando poucos requisitos sao atendidos', () => {
    const result = evaluatePasswordStrength('abc');
    expect(result.level).toBe('weak');
    expect(result.label).toBe('Fraca');
  });

  it('classifica senha forte quando todos os requisitos sao atendidos', () => {
    const result = evaluatePasswordStrength('Senha123!');
    expect(result.level).toBe('strong');
    expect(result.label).toBe('Forte');
    expect(result.checks).toMatchObject({
      minLength: true,
      lowercase: true,
      uppercase: true,
      number: true,
      special: true,
    });
  });

  it('classifica senha muito forte quando excede o minimo', () => {
    const result = evaluatePasswordStrength('Senha-Forte-2026!');
    expect(result.level).toBe('very-strong');
    expect(result.label).toBe('Muito forte');
  });
});
