import type { PropsWithChildren } from 'react';
import { Alert, Button, Result } from 'antd';
import { Navigate, useLocation } from 'react-router-dom';

import { useSessionStore } from '@/stores/session-store';

export function ProtectedRoute({ children }: PropsWithChildren) {
  const isAuthenticated = useSessionStore((state) => state.isAuthenticated);
  const hasSessionToken = useSessionStore((state) =>
    Boolean(state.accessToken || state.refreshToken),
  );
  const location = useLocation();
  const tenant = useSessionStore((state) => state.tenant);
  const clearSession = useSessionStore((state) => state.clearSession);

  if (!isAuthenticated || !hasSessionToken) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (tenant && !['ativo', 'trial'].includes(tenant.status)) {
    return (
      <Result
        status="warning"
        title="Acesso à campanha bloqueado"
        subTitle={`O tenant está ${tenant.status}. Procure o gestor da conta ou o suporte comercial.`}
        extra={
          <>
            <Alert
              type="info"
              showIcon
              message="Se a situação já foi regularizada, encerre a sessão e entre novamente."
            />
            <Button type="primary" onClick={clearSession} style={{ marginTop: 16 }}>
              Voltar ao login
            </Button>
          </>
        }
      />
    );
  }

  return children;
}
