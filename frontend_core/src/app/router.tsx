import { createBrowserRouter } from 'react-router-dom';

import { HomeRedirect } from '@/app/HomeRedirect';
import { PermissionRoute } from '@/app/PermissionRoute';
import { ProtectedRoute } from '@/app/ProtectedRoute';
import { ProfileRoute } from '@/app/ProfileRoute';
import { SaasAdminRoute } from '@/app/SaasAdminRoute';
import { AuthenticatedLayout } from '@/layouts/AuthenticatedLayout';
import { AccessHistoryPage } from '@/pages/auth/AccessHistoryPage';
import { LoginPage } from '@/pages/auth/LoginPage';
import { MyProfilePage } from '@/pages/auth/MyProfilePage';
import { RequiredPasswordChangePage } from '@/pages/auth/RequiredPasswordChangePage';
import { AgendaPage } from '@/pages/agenda/AgendaPage';
import { EventDetailPage } from '@/pages/agenda/EventDetailPage';
import { PublicAttendancePage } from '@/pages/agenda/PublicAttendancePage';
import { CadastroPage } from '@/pages/cadastro/CadastroPage';
import { ContractsPage } from '@/pages/contratos/ContractsPage';
import { DuplicidadesPage } from '@/pages/cadastro/DuplicidadesPage';
import { IndicacoesGraphPage } from '@/pages/cadastro/IndicacoesGraphPage';
import { LiderancasPage } from '@/pages/cadastro/LiderancasPage';
import { PessoaDetailPage } from '@/pages/cadastro/PessoaDetailPage';
import { SegmentacaoPage } from '@/pages/cadastro/SegmentacaoPage';
import { ValidacoesPage } from '@/pages/cadastro/ValidacoesPage';
import { DashboardPage } from '@/pages/dashboard/DashboardPage';
import { ReportsPage } from '@/pages/dashboard/ReportsPage';
import { DemandasPage } from '@/pages/demandas/DemandasPage';
import { DemandDetailPage } from '@/pages/demandas/DemandDetailPage';
import { AdminElectionsPage } from '@/pages/eleicoes/AdminElectionsPage';
import { CampaignClosurePage } from '@/pages/eleicoes/CampaignClosurePage';
import { CampaignManagementPage } from '@/pages/eleicoes/CampaignManagementPage';
import { ImportDetailPage } from '@/pages/etl/ImportDetailPage';
import { ImportsPage } from '@/pages/etl/ImportsPage';
import { GoalDetailPage } from '@/pages/metas/GoalDetailPage';
import { GoalsPage } from '@/pages/metas/GoalsPage';
import { NotFoundPage } from '@/pages/shared/NotFoundPage';
import { AdminTenantsPage } from '@/pages/tenants/AdminTenantsPage';
import { SubscriptionPage } from '@/pages/tenants/SubscriptionPage';
import { TenantSettingsPage } from '@/pages/tenants/TenantSettingsPage';
import { TenantCadastroSettingsPage } from '@/pages/tenants/TenantCadastroSettingsPage';
import { TenantTerminologySettingsPage } from '@/pages/tenants/TenantTerminologySettingsPage';
import { TerritoriosPage } from '@/pages/territorios/TerritoriosPage';
import { TerritorioDetailPage } from '@/pages/territorios/TerritorioDetailPage';
import { UsersPage } from '@/pages/users/UsersPage';

const withPermission = (permission: string, element: React.ReactNode) => (
  <PermissionRoute permission={permission}>{element}</PermissionRoute>
);

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/presenca/:uuid', element: <PublicAttendancePage /> },
  {
    path: '/minha-conta/alterar-senha',
    element: (
      <ProtectedRoute>
        <RequiredPasswordChangePage />
      </ProtectedRoute>
    ),
  },
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
        path: 'relatorios',
        element: withPermission('dashboard.visualizar', <ReportsPage />),
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
        path: 'cadastro/duplicidades',
        element: (
          <ProfileRoute profiles={['gestor', 'gestor_saas']}>
            {withPermission('cadastro.visualizar', <DuplicidadesPage />)}
          </ProfileRoute>
        ),
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
        path: 'territorios/:id',
        element: withPermission('territorio.visualizar', <TerritorioDetailPage />),
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
      {
        path: 'contratos',
        element: (
          <ProfileRoute profiles={['tesoureiro']}>
            <ContractsPage />
          </ProfileRoute>
        ),
      },
      /* legacy placeholder retained only for modules not implemented
          <ModulePlaceholderPage
            title="Demandas"
            description="Registre e acompanhe atendimentos e solicitações da população."
          />,
        ), */
      { path: 'minha-conta/perfil', element: <MyProfilePage /> },
      { path: 'minha-conta/acessos', element: <AccessHistoryPage /> },
      {
        path: 'usuarios',
        element: withPermission('usuarios.visualizar', <UsersPage />),
      },
      {
        path: 'configuracoes',
        element: (
          <ProfileRoute
            profiles={['gestor', 'gestor_saas', 'coordenador_territorial']}
            permission="configuracoes.visualizar"
          >
            <TenantSettingsPage />
          </ProfileRoute>
        ),
      },
      {
        path: 'configuracoes/campanhas',
        element: (
          <ProfileRoute profiles={['gestor', 'gestor_saas', 'coordenador_territorial']}>
            <CampaignManagementPage />
          </ProfileRoute>
        ),
      },
      {
        path: 'configuracoes/nomenclaturas',
        element: (
          <ProfileRoute profiles={['gestor', 'gestor_saas']}>
            <TenantTerminologySettingsPage />
          </ProfileRoute>
        ),
      },
      {
        path: 'configuracoes/cadastros',
        element: (
          <ProfileRoute profiles={['gestor', 'gestor_saas']}>
            <TenantCadastroSettingsPage />
          </ProfileRoute>
        ),
      },
      {
        path: 'configuracoes/campanhas/encerramento',
        element: (
          <ProfileRoute profiles={['gestor', 'gestor_saas', 'coordenador_territorial']}>
            <CampaignClosurePage />
          </ProfileRoute>
        ),
      },
      {
        path: 'campanha/encerramento',
        element: (
          <ProfileRoute profiles={['gestor', 'gestor_saas', 'coordenador_territorial']}>
            <CampaignClosurePage />
          </ProfileRoute>
        ),
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
      {
        path: 'admin/eleicoes',
        element: (
          <SaasAdminRoute>
            <AdminElectionsPage />
          </SaasAdminRoute>
        ),
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
