import type { PropsWithChildren } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import { useSessionStore } from '@/stores/session-store';

export function ProtectedRoute({ children }: PropsWithChildren) {
  const isAuthenticated = useSessionStore((state) => state.isAuthenticated);
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return children;
}
