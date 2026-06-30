import { createBrowserRouter } from 'react-router-dom';

import { HomeRedirect } from '@/app/HomeRedirect';
import { PermissionRoute } from '@/app/PermissionRoute';
import { ProtectedRoute } from '@/app/ProtectedRoute';
import { SaasAdminRoute } from '@/app/SaasAdminRoute';
import { AuthenticatedLayout } from '@/layouts/AuthenticatedLayout';
import { LoginPage } from '@/pages/auth/LoginPage';
import { AccessHistoryPage } from '@/pages/auth/AccessHistoryPage';
import { CadastroPage } from '@/pages/cadastro/CadastroPage';
import { DashboardPage } from '@/pages/dashboard/DashboardPage';
import { ModulePlaceholderPage } from '@/pages/shared/ModulePlaceholderPage';
import { NotFoundPage } from '@/pages/shared/NotFoundPage';
import { AdminTenantsPage } from '@/pages/tenants/AdminTenantsPage';
import { SubscriptionPage } from '@/pages/tenants/SubscriptionPage';
import { TenantSettingsPage } from '@/pages/tenants/TenantSettingsPage';
import { UsersPage } from '@/pages/users/UsersPage';

const withPermission = (permission: string, element: React.ReactNode) => (
  <PermissionRoute permission={permission}>{element}</PermissionRoute>
);

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
      { index: true, element: <HomeRedirect /> },
      {
        path: 'dashboard',
        element: withPermission('dashboard.visualizar', <DashboardPage />),
      },
      {
        path: 'cadastro',
        element: withPermission('cadastro.visualizar', <CadastroPage />),
      },
      {
        path: 'liderancas',
        element: withPermission(
          'cadastro.visualizar',
          <ModulePlaceholderPage
            title="Lideranças"
            description="Organize lideranças, áreas de influência e vínculos com a campanha."
          />,
        ),
      },
      {
        path: 'metas',
        element: withPermission(
          'metas.visualizar',
          <ModulePlaceholderPage
            title="Metas e votos"
            description="Acompanhe metas eleitorais e evolução por território."
          />,
        ),
      },
      {
        path: 'agenda',
        element: withPermission(
          'agenda.visualizar',
          <ModulePlaceholderPage
            title="Agenda"
            description="Planeje compromissos, eventos e atividades de campo."
          />,
        ),
      },
      {
        path: 'demandas',
        element: withPermission(
          'demandas.visualizar',
          <ModulePlaceholderPage
            title="Demandas"
            description="Registre e acompanhe atendimentos e solicitações da população."
          />,
        ),
      },
      {
        path: 'minha-conta/acessos',
        element: <AccessHistoryPage />,
      },
      {
        path: 'usuarios',
        element: withPermission('usuarios.visualizar', <UsersPage />),
      },
      {
        path: 'configuracoes',
        element: withPermission('configuracoes.visualizar', <TenantSettingsPage />),
      },
      {
        path: 'assinatura',
        element: withPermission('configuracoes.visualizar', <SubscriptionPage />),
      },
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
