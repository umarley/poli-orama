import {
  BellOutlined,
  DownOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuOutlined,
  MenuUnfoldOutlined,
  SearchOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
} from '@ant-design/icons';
import {
  Avatar,
  Button,
  Drawer,
  Dropdown,
  Flex,
  Grid,
  Input,
  Layout,
  Menu,
  Modal,
  Select,
  Space,
  Tooltip,
  Typography,
} from 'antd';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Outlet, useLocation, useNavigate, useSearchParams } from 'react-router-dom';

import { canViewNavigationItem, getNavigationItems, getNavigationLabel } from '@/app/navigation';
import { Brand } from '@/components/brand/Brand';
import { ToastBridge } from '@/components/feedback/ToastBridge';
import { AppToast } from '@/components/feedback/AppToast';
import { getCurrentUser, logout, switchTenant } from '@/modules/auth/auth-service';
import { getCurrentCampaign } from '@/modules/eleicoes/eleicoes-service';
import { getTenantConfiguration, listTenants } from '@/modules/tenants/tenant-service';
import { normalizeApiError } from '@/services/api/api-error';
import { mapAuthUser, useSessionStore } from '@/stores/session-store';

import styles from './AuthenticatedLayout.module.css';

const { Header, Sider, Content, Footer } = Layout;

export function AuthenticatedLayout() {
  const queryClient = useQueryClient();
  const screens = Grid.useBreakpoint();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [tenantModalOpen, setTenantModalOpen] = useState(false);
  const [selectedTenantId, setSelectedTenantId] = useState<number>();
  const [switchingTenant, setSwitchingTenant] = useState(false);
  const user = useSessionStore((state) => state.user);
  const tenant = useSessionStore((state) => state.tenant);
  const currentCampaign = useSessionStore((state) => state.currentCampaign);
  const setCurrentCampaign = useSessionStore((state) => state.setCurrentCampaign);
  const clearSession = useSessionStore((state) => state.clearSession);
  const setSession = useSessionStore((state) => state.setSession);
  const updateUser = useSessionStore((state) => state.updateUser);
  const isSaasManager = user?.profiles.includes('gestor_saas') ?? false;
  const isMobile = screens.md === false;
  const compactWindow = searchParams.get('janela') === '1';
  const currentCampaignQuery = useQuery({
    queryKey: ['current-campaign'],
    queryFn: getCurrentCampaign,
  });
  const currentUserQuery = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: getCurrentUser,
  });
  const tenantConfigurationQuery = useQuery({
    queryKey: ['tenant-configuration'],
    queryFn: getTenantConfiguration,
  });
  const tenantsQuery = useQuery({
    queryKey: ['tenants', 'switcher'],
    queryFn: () => listTenants({}),
    enabled: isSaasManager && tenantModalOpen,
  });

  useEffect(() => {
    if (currentUserQuery.isSuccess) updateUser(currentUserQuery.data);
  }, [currentUserQuery.data, currentUserQuery.isSuccess, updateUser]);

  useEffect(() => {
    if (currentCampaignQuery.isSuccess) {
      const campaign = currentCampaignQuery.data;
      setCurrentCampaign(
        campaign
          ? {
              id: campaign.uuid_publico,
              name: campaign.nome,
              office: campaign.cargo_pleiteado,
              active: campaign.ativa,
              election: {
                id: String(campaign.eleicao_id),
                year: campaign.eleicao_ano,
                type: campaign.eleicao_tipo,
                round: campaign.eleicao_turno,
                date: campaign.eleicao_data,
              },
            }
          : null,
      );
    }
  }, [currentCampaignQuery.data, currentCampaignQuery.isSuccess, setCurrentCampaign]);
  const visibleMenuItems = getNavigationItems(tenantConfigurationQuery.data)
    .filter((item) => canViewNavigationItem(item, user?.permissions ?? [], user?.profiles ?? []))
    .map((item) => ({ ...item }));

  const currentRoute =
    visibleMenuItems
      ?.map((item) => String(item?.key))
      .sort((left, right) => right.length - left.length)
      .find((key) => location.pathname.startsWith(key)) ?? '/dashboard';

  const handleNavigate = ({ key }: { key: string }) => {
    navigate(key);
    setDrawerOpen(false);
  };

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      clearSession();
      navigate('/login', { replace: true });
    }
  };

  const handleCloseAttendanceWindow = () => {
    window.close();
    navigate('/comunicacao');
  };

  const isAttendanceWindow = location.pathname.startsWith('/comunicacao/atendimento');
  const profileMenuItems = isAttendanceWindow
    ? [
        {
          key: 'close',
          label: 'Sair',
          icon: <LogoutOutlined />,
          danger: true,
          onClick: handleCloseAttendanceWindow,
        },
      ]
    : [
        ...(isSaasManager
          ? [
              {
                key: 'tenant',
                label: 'Selecionar tenant',
                icon: <SafetyCertificateOutlined />,
                onClick: () => setTenantModalOpen(true),
              },
            ]
          : []),
        {
          key: 'profile',
          label: 'Meu perfil',
          icon: <UserOutlined />,
          onClick: () => navigate('/minha-conta/perfil'),
        },
        {
          key: 'security',
          label: 'Segurança e acessos',
          icon: <SafetyCertificateOutlined />,
          onClick: () => navigate('/minha-conta/acessos'),
        },
        {
          key: 'logout',
          label: 'Sair',
          icon: <LogoutOutlined />,
          danger: true,
          onClick: () => void handleLogout(),
        },
      ];

  const handleTenantSwitch = async () => {
    if (!selectedTenantId) return;
    setSwitchingTenant(true);
    try {
      const authentication = await switchTenant({
        tenant_id: selectedTenantId,
        dispositivo: window.navigator.userAgent.slice(0, 180),
      });
      const selectedTenant = authentication.usuario.tenant;
      await queryClient.cancelQueries();
      setSession(
        mapAuthUser(authentication.usuario),
        {
          id: selectedTenant.id,
          name: selectedTenant.nome,
          slug: selectedTenant.slug,
          status: selectedTenant.status,
        },
        null,
        authentication.access_token,
        authentication.refresh_token,
        authentication.expires_in,
      );
      queryClient.clear();
      setTenantModalOpen(false);
      setSelectedTenantId(undefined);
      AppToast.success(`Tenant alterado para ${selectedTenant.nome}.`);
      navigate('/dashboard', { replace: true });
    } catch (error) {
      AppToast.error(normalizeApiError(error).message);
    } finally {
      setSwitchingTenant(false);
    }
  };

  const navigation = (
    <>
      <div className={styles.tenant}>
        <span className={styles.tenantLabel}>Campanha atual</span>
        <strong>{currentCampaign?.name ?? 'Nenhuma campanha selecionada'}</strong>
        <span>
          {currentCampaign
            ? `${currentCampaign.office} · Eleições ${currentCampaign.election.year}`
            : 'Selecione uma campanha para continuar'}
        </span>
      </div>
      <Menu
        theme="dark"
        mode="inline"
        items={visibleMenuItems}
        selectedKeys={[currentRoute]}
        onClick={handleNavigate}
        aria-label="Navegação principal"
      />
    </>
  );

  return (
    <Layout className={styles.root}>
      <ToastBridge />
      {!isMobile && !compactWindow && (
        <Sider
          width={256}
          collapsedWidth={72}
          collapsed={collapsed}
          className={styles.sider}
          trigger={null}
        >
          <div className={styles.brandSlot}>
            <Brand compact={collapsed} inverted />
          </div>
          {navigation}
        </Sider>
      )}

      <Drawer
        placement="left"
        width={280}
        open={isMobile && !compactWindow && drawerOpen}
        onClose={() => setDrawerOpen(false)}
        closable={false}
        styles={{ body: { padding: 0, background: '#001d66' } }}
      >
        <div className={styles.brandSlot}>
          <Brand inverted />
        </div>
        {navigation}
      </Drawer>

      <Layout className={`${styles.main} ${compactWindow ? styles.compactMain : ''}`}>
        <Header className={styles.header}>
          <Flex align="center" justify="space-between" gap={12}>
            <Flex align="center" gap={8} className={styles.headerStart}>
              {!compactWindow && (
                <Button
                  type="text"
                  className={styles.headerIcon}
                  icon={
                    isMobile ? (
                      <MenuOutlined />
                    ) : collapsed ? (
                      <MenuUnfoldOutlined />
                    ) : (
                      <MenuFoldOutlined />
                    )
                  }
                  aria-label={isMobile ? 'Abrir menu' : 'Alternar menu'}
                  onClick={() => (isMobile ? setDrawerOpen(true) : setCollapsed((value) => !value))}
                />
              )}
              {!compactWindow && (
                <div className={styles.desktopSearch}>
                  <Input
                    variant="borderless"
                    prefix={<SearchOutlined />}
                    placeholder="Buscar pessoas, demandas e locais"
                    aria-label="Busca global"
                  />
                </div>
              )}
              <Typography.Text className={compactWindow ? styles.compactTitle : styles.mobileTitle}>
                {getNavigationLabel(location.pathname, tenantConfigurationQuery.data)}
              </Typography.Text>
            </Flex>

            <Space size={4}>
              <Tooltip title="Notificações">
                <Button
                  type="text"
                  className={styles.headerIcon}
                  icon={<BellOutlined />}
                  aria-label="Notificações"
                />
              </Tooltip>
              <Dropdown
                trigger={['click']}
                menu={{
                  items: profileMenuItems,
                }}
              >
                <Button type="text" className={styles.profileButton}>
                  <Avatar size={28} className={styles.avatar}>
                    {user?.initials ?? 'VU'}
                  </Avatar>
                  <span className={styles.profileText}>
                    <strong>{user?.name ?? 'Usuário'}</strong>
                    <small>{tenant?.name ?? 'Tenant não identificado'}</small>
                  </span>
                  <DownOutlined className={styles.chevron} />
                </Button>
              </Dropdown>
            </Space>
          </Flex>
        </Header>

        <Content className={`${styles.content} ${compactWindow ? styles.compactContent : ''}`}>
          <Outlet />
        </Content>

        {!compactWindow && (
          <Footer className={styles.footer}>
            Poliorama · Plataforma de inteligência para campanhas
          </Footer>
        )}
      </Layout>
      <Modal
        open={tenantModalOpen}
        title="Selecionar tenant para suporte"
        okText="Acessar tenant"
        cancelText="Cancelar"
        okButtonProps={{ disabled: !selectedTenantId }}
        confirmLoading={switchingTenant}
        onOk={() => void handleTenantSwitch()}
        onCancel={() => setTenantModalOpen(false)}
      >
        <Typography.Paragraph type="secondary">
          A nova sessão será aberta no contexto do cliente escolhido, mantendo seu perfil de Gestor
          SaaS.
        </Typography.Paragraph>
        <Select
          showSearch
          style={{ width: '100%' }}
          placeholder="Selecione um tenant"
          loading={tenantsQuery.isPending}
          value={selectedTenantId}
          optionFilterProp="label"
          onChange={setSelectedTenantId}
          options={(tenantsQuery.data?.items ?? []).map((item) => ({
            value: item.id,
            label: `${item.nome} (${item.slug})`,
          }))}
        />
      </Modal>
    </Layout>
  );
}
