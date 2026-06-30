import { Navigate } from 'react-router-dom';

import { getDefaultRoute } from '@/app/navigation';
import { useSessionStore } from '@/stores/session-store';

export function HomeRedirect() {
  const user = useSessionStore((state) => state.user);
  return <Navigate to={getDefaultRoute(user?.permissions ?? [], user?.profiles ?? [])} replace />;
}
