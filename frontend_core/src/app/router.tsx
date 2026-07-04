import { createBrowserRouter } from 'react-router-dom';

import { HomeRedirect } from '@/app/HomeRedirect';
import { PermissionRoute } from '@/app/PermissionRoute';
import { ProtectedRoute } from '@/app/ProtectedRoute';
import { SaasAdminRoute } from '@/app/SaasAdminRoute';
import { AuthenticatedLayout } from '@/layouts/AuthenticatedLayout';
import { AccessHistoryPage } from '@/pages/auth/AccessHistoryPage';
import { LoginPage } from '@/pages/auth/LoginPage';
import { AgendaPage } from '@/pages/agenda/AgendaPage';
import { EventDetailPage } from '@/pages/agenda/EventDetailPage';
import { CadastroPage } from '@/pages/cadastro/CadastroPage';
import { IndicacoesGraphPage } from '@/pages/cadastro/IndicacoesGraphPage';
import { LiderancasPage } from '@/pages/cadastro/LiderancasPage';
import { PessoaDetailPage } from '@/pages/cadastro/PessoaDetailPage';
import { SegmentacaoPage } from '@/pages/cadastro/SegmentacaoPage';
import { ValidacoesPage } from '@/pages/cadastro/ValidacoesPage';
import { DashboardPage } from '@/pages/dashboard/DashboardPage';
import { DemandasPage } from '@/pages/demandas/DemandasPage';
import { DemandDetailPage } from '@/pages/demandas/DemandDetailPage';
import { ImportDetailPage } from '@/pages/etl/ImportDetailPage';
import { ImportsPage } from '@/pages/etl/ImportsPage';
import { GoalDetailPage } from '@/pages/metas/GoalDetailPage';
import { GoalsPage } from '@/pages/metas/GoalsPage';
import { NotFoundPage } from '@/pages/shared/NotFoundPage';
import { AdminTenantsPage } from '@/pages/tenants/AdminTenantsPage';
import { SubscriptionPage } from '@/pages/tenants/SubscriptionPage';
import { TenantSettingsPage } from '@/pages/tenants/TenantSettingsPage';
import { TerritoriosPage } from '@/pages/territorios/TerritoriosPage';
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
        path: 'cadastro/pessoas/:id',
        element: withPermission('cadastro.visualizar', <PessoaDetailPage />),
      },
      {
        path: 'cadastro/segmentacao',
        element: withPermission('cadastro.visualizar', <SegmentacaoPage />),
      },
      {
        path: 'cadastro/validacoes',
        element: withPermission('cadastro.visualizar', <ValidacoesPage />),
      },
      {
        path: 'cadastro/indicacoes',
        element: withPermission('cadastro.visualizar', <IndicacoesGraphPage />),
      },
      {
        path: 'liderancas',
        element: withPermission('cadastro.visualizar', <LiderancasPage />),
      },
      {
        path: 'territorios',
        element: withPermission('territorio.visualizar', <TerritoriosPage />),
      },
      {
        path: 'metas',
        element: withPermission('metas.visualizar', <GoalsPage />),
      },
      {
        path: 'metas/:id',
        element: withPermission('metas.visualizar', <GoalDetailPage />),
      },
      {
        path: 'importacoes',
        element: withPermission('etl.visualizar', <ImportsPage />),
      },
      {
        path: 'importacoes/:id',
        element: withPermission('etl.visualizar', <ImportDetailPage />),
      },
      {
        path: 'agenda',
        element: withPermission('agenda.visualizar', <AgendaPage />),
      },
      {
        path: 'agenda/eventos/:id',
        element: withPermission('agenda.visualizar', <EventDetailPage />),
      },
      {
        path: 'demandas',
        element: withPermission('demandas.visualizar', <DemandasPage />),
      },
      {
        path: 'demandas/:id',
        element: withPermission('demandas.visualizar', <DemandDetailPage />),
      },
      /* legacy placeholder retained only for modules not implemented
          <ModulePlaceholderPage
            title="Demandas"
            description="Registre e acompanhe atendimentos e solicitações da população."
          />,
        ), */
      { path: 'minha-conta/acessos', element: <AccessHistoryPage /> },
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
