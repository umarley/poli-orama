import { env } from '@/config/env';

import styles from './Brand.module.css';

interface BrandProps {
  compact?: boolean;
  inverted?: boolean;
}

export function Brand({ compact = false, inverted = false }: BrandProps) {
  return (
    <div className={`${styles.brand} ${inverted ? styles.inverted : ''}`} aria-label={env.appName}>
      <span className={styles.mark} aria-hidden="true">
        V
      </span>
      {!compact && (
        <span className={styles.name}>
          Vurix <strong>Eleitoral</strong>
        </span>
      )}
    </div>
  );
}
