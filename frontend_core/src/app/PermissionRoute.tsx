import { Result } from 'antd';
import type { PropsWithChildren } from 'react';

import { useSessionStore } from '@/stores/session-store';

interface PermissionRouteProps extends PropsWithChildren {
  permission: string;
}

export function PermissionRoute({ permission, children }: PermissionRouteProps) {
  const permissions = useSessionStore((state) => state.user?.permissions ?? []);
  if (!permissions.includes(permission)) {
    return (
      <Result
        status="403"
        title="Acesso restrito"
        subTitle={`Permissão necessária: ${permission}.`}
      />
    );
  }
  return children;
}
