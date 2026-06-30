import { Navigate, createBrowserRouter } from 'react-router-dom';

import { ProtectedRoute } from '@/app/ProtectedRoute';
import { SaasAdminRoute } from '@/app/SaasAdminRoute';
import { AuthenticatedLayout } from '@/layouts/AuthenticatedLayout';
import { LoginPage } from '@/pages/auth/LoginPage';
import { CadastroPage } from '@/pages/cadastro/CadastroPage';
import { DashboardPage } from '@/pages/dashboard/DashboardPage';
import { ModulePlaceholderPage } from '@/pages/shared/ModulePlaceholderPage';
import { NotFoundPage } from '@/pages/shared/NotFoundPage';
import { AdminTenantsPage } from '@/pages/tenants/AdminTenantsPage';
import { SubscriptionPage } from '@/pages/tenants/SubscriptionPage';
import { TenantSettingsPage } from '@/pages/tenants/TenantSettingsPage';

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AuthenticatedLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'cadastro', element: <CadastroPage /> },
      {
        path: 'liderancas',
        element: (
          <ModulePlaceholderPage
            title="Lideranças"
            description="Organize lideranças, áreas de influência e vínculos com a campanha."
          />
        ),
      },
      {
        path: 'metas',
        element: (
          <ModulePlaceholderPage
            title="Metas e votos"
            description="Acompanhe metas eleitorais e evolução por território."
          />
        ),
      },
      {
        path: 'agenda',
        element: (
          <ModulePlaceholderPage
            title="Agenda"
            description="Planeje compromissos, eventos e atividades de campo."
          />
        ),
      },
      {
        path: 'demandas',
        element: (
          <ModulePlaceholderPage
            title="Demandas"
            description="Registre e acompanhe atendimentos e solicitações da população."
          />
        ),
      },
      { path: 'configuracoes', element: <TenantSettingsPage /> },
      { path: 'assinatura', element: <SubscriptionPage /> },
      {
        path: 'admin/tenants',
        element: (
          <SaasAdminRoute>
            <AdminTenantsPage />
          </SaasAdminRoute>
        ),
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
