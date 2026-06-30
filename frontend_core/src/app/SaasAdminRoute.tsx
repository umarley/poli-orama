import { Result } from 'antd';
import type { PropsWithChildren } from 'react';

import { useSessionStore } from '@/stores/session-store';

export function SaasAdminRoute({ children }: PropsWithChildren) {
  const profiles = useSessionStore((state) => state.user?.profiles ?? []);
  if (!profiles.includes('gestor_saas')) {
    return (
      <Result status="403" title="Acesso restrito" subTitle="Permissão de gestor SaaS exigida." />
    );
  }
  return children;
}
