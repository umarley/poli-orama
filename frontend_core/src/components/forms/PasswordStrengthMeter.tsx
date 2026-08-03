import { CheckOutlined, CloseOutlined } from '@ant-design/icons';
import { Progress } from 'antd';

import {
  evaluatePasswordStrength,
  type PasswordStrengthLevel,
} from '@/modules/auth/password-policy';

import styles from './PasswordStrengthMeter.module.css';

interface PasswordStrengthMeterProps {
  password: string;
}

const PROGRESS_STATUS: Record<
  Exclude<PasswordStrengthLevel, 'empty'>,
  'exception' | 'normal' | 'active' | 'success'
> = {
  weak: 'exception',
  fair: 'normal',
  good: 'active',
  strong: 'success',
  'very-strong': 'success',
};

const LABEL_CLASS: Record<Exclude<PasswordStrengthLevel, 'empty'>, string> = {
  weak: styles.labelWeak,
  fair: styles.labelFair,
  good: styles.labelGood,
  strong: styles.labelStrong,
  'very-strong': styles.labelVeryStrong,
};

const CHECKLIST = [
  { key: 'minLength', label: 'Pelo menos 8 caracteres' },
  { key: 'lowercase', label: 'Letra minúscula' },
  { key: 'uppercase', label: 'Letra maiúscula' },
  { key: 'number', label: 'Número' },
  { key: 'special', label: 'Caractere especial' },
] as const;

export function PasswordStrengthMeter({ password }: PasswordStrengthMeterProps) {
  const strength = evaluatePasswordStrength(password);

  if (strength.level === 'empty') {
    return null;
  }

  return (
    <div className={styles.meter} aria-live="polite">
      <div className={styles.header}>
        <span>Força da senha</span>
        <span className={LABEL_CLASS[strength.level]}>{strength.label}</span>
      </div>
      <Progress
        percent={strength.score}
        showInfo={false}
        status={PROGRESS_STATUS[strength.level]}
        strokeColor={
          strength.level === 'very-strong'
            ? { from: '#52c41a', to: '#237804' }
            : undefined
        }
      />
      <ul className={styles.checklist}>
        {CHECKLIST.map((item) => {
          const met = strength.checks[item.key];
          return (
            <li
              key={item.key}
              className={`${styles.checkItem} ${met ? styles.checkItemMet : ''}`}
            >
              {met ? (
                <CheckOutlined className={styles.checkIcon} aria-hidden />
              ) : (
                <CloseOutlined className={styles.checkIcon} aria-hidden />
              )}
              {item.label}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
