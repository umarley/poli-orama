import {
  BellOutlined,
  DownOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuOutlined,
  MenuUnfoldOutlined,
  SearchOutlined,
  SafetyCertificateOutlined,
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
  Space,
  Tooltip,
  Typography,
} from 'antd';
import { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';

import { canViewNavigationItem, getNavigationLabel, navigationItems } from '@/app/navigation';
import { Brand } from '@/components/brand/Brand';
import { ToastBridge } from '@/components/feedback/ToastBridge';
import { logout } from '@/modules/auth/auth-service';
import { useSessionStore } from '@/stores/session-store';

import styles from './AuthenticatedLayout.module.css';

const { Header, Sider, Content, Footer } = Layout;

export function AuthenticatedLayout() {
  const screens = Grid.useBreakpoint();
  const location = useLocation();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const user = useSessionStore((state) => state.user);
  const tenant = useSessionStore((state) => state.tenant);
  const currentCampaign = useSessionStore((state) => state.currentCampaign);
  const clearSession = useSessionStore((state) => state.clearSession);
  const isMobile = screens.md === false;
  const visibleMenuItems = navigationItems
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
      {!isMobile && (
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
        open={isMobile && drawerOpen}
        onClose={() => setDrawerOpen(false)}
        closable={false}
        styles={{ body: { padding: 0, background: '#001d66' } }}
      >
        <div className={styles.brandSlot}>
          <Brand inverted />
        </div>
        {navigation}
      </Drawer>

      <Layout className={styles.main}>
        <Header className={styles.header}>
          <Flex align="center" justify="space-between" gap={12}>
            <Flex align="center" gap={8} className={styles.headerStart}>
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
              <div className={styles.desktopSearch}>
                <Input
                  variant="borderless"
                  prefix={<SearchOutlined />}
                  placeholder="Buscar pessoas, demandas e locais"
                  aria-label="Busca global"
                />
              </div>
              <Typography.Text className={styles.mobileTitle}>
                {getNavigationLabel(location.pathname)}
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
                  items: [
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
                  ],
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

        <Content className={styles.content}>
          <Outlet />
        </Content>

        <Footer className={styles.footer}>
          Vurix Eleitoral · Plataforma de inteligência para campanhas
        </Footer>
      </Layout>
    </Layout>
  );
}
