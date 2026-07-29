import { Result } from 'antd';
import type { PropsWithChildren } from 'react';

import { useSessionStore } from '@/stores/session-store';

interface ProfileRouteProps extends PropsWithChildren {
  profiles: string[];
  permission?: string;
}

export function ProfileRoute({ profiles: allowed, permission, children }: ProfileRouteProps) {
  const user = useSessionStore((state) => state.user);
  const hasProfile = allowed.some((profile) => user?.profiles.includes(profile));
  const hasPermission = permission ? user?.permissions.includes(permission) : false;
  if (!hasProfile && !hasPermission) {
    return (
      <Result
        status="403"
        title="Acesso restrito"
        subTitle="Seu perfil não permite acessar esta configuração."
      />
    );
  }
  return children;
}
