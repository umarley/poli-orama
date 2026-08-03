export const PASSWORD_MIN_LENGTH = 8;

export const PASSWORD_POLICY_HINT =
  'Mínimo de 8 caracteres, com letra maiúscula, minúscula, número e caractere especial.';

export const passwordMinLengthRule = {
  min: PASSWORD_MIN_LENGTH,
  message: `A senha deve ter pelo menos ${PASSWORD_MIN_LENGTH} caracteres.`,
};

export type PasswordStrengthLevel = 'empty' | 'weak' | 'fair' | 'good' | 'strong' | 'very-strong';

export interface PasswordStrengthChecks {
  minLength: boolean;
  lowercase: boolean;
  uppercase: boolean;
  number: boolean;
  special: boolean;
}

export interface PasswordStrengthResult {
  score: number;
  level: PasswordStrengthLevel;
  label: string;
  checks: PasswordStrengthChecks;
}

const STRENGTH_LABELS: Record<Exclude<PasswordStrengthLevel, 'empty'>, string> = {
  weak: 'Fraca',
  fair: 'Razoável',
  good: 'Boa',
  strong: 'Forte',
  'very-strong': 'Muito forte',
};

export function evaluatePasswordStrength(password: string): PasswordStrengthResult {
  const checks: PasswordStrengthChecks = {
    minLength: password.length >= PASSWORD_MIN_LENGTH,
    lowercase: /[a-z]/.test(password),
    uppercase: /[A-Z]/.test(password),
    number: /\d/.test(password),
    special: /[^A-Za-z0-9]/.test(password),
  };

  if (!password) {
    return { score: 0, level: 'empty', label: '', checks };
  }

  const metCount = Object.values(checks).filter(Boolean).length;
  let score = (metCount / 5) * 60;
  if (password.length >= 12) score += 15;
  if (password.length >= 16) score += 10;
  if (password.length >= 20) score += 5;
  score = Math.min(100, Math.round(score));

  let level: PasswordStrengthLevel;
  if (metCount <= 2) level = 'weak';
  else if (metCount === 3) level = 'fair';
  else if (metCount === 4) level = 'good';
  else if (password.length >= 16) level = 'very-strong';
  else level = 'strong';

  return {
    score,
    level,
    label: STRENGTH_LABELS[level],
    checks,
  };
}
