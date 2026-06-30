import { Result } from 'antd';
import type { PropsWithChildren } from 'react';

import { useSessionStore } from '@/stores/session-store';

export function SaasAdminRoute({ children }: PropsWithChildren) {
  const role = useSessionStore((state) => state.user?.role);
  if (!['gestor_saas', 'admin'].includes(role ?? '')) {
    return (
      <Result status="403" title="Acesso restrito" subTitle="Permissão de gestor SaaS exigida." />
    );
  }
  return children;
}
