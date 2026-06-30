import {
  BankOutlined,
  CalendarOutlined,
  CreditCardOutlined,
  DashboardOutlined,
  FlagOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  SolutionOutlined,
  TeamOutlined,
  UnorderedListOutlined,
  UserOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';

export interface NavigationItem {
  key: string;
  label: string;
  icon: React.ReactNode;
  permission?: string;
  profiles?: string[];
}

export const navigationItems: NavigationItem[] = [
  {
    key: '/dashboard',
    label: 'Painel de controle',
    icon: <DashboardOutlined />,
    permission: 'dashboard.visualizar',
  },
  {
    key: '/cadastro',
    label: 'Pessoas e eleitores',
    icon: <TeamOutlined />,
    permission: 'cadastro.visualizar',
  },
  {
    key: '/liderancas',
    label: 'Lideranças',
    icon: <SolutionOutlined />,
    permission: 'cadastro.visualizar',
  },
  {
    key: '/metas',
    label: 'Metas e votos',
    icon: <FlagOutlined />,
    permission: 'metas.visualizar',
  },
  {
    key: '/agenda',
    label: 'Agenda',
    icon: <CalendarOutlined />,
    permission: 'agenda.visualizar',
  },
  {
    key: '/demandas',
    label: 'Demandas',
    icon: <UnorderedListOutlined />,
    permission: 'demandas.visualizar',
  },
  {
    key: '/usuarios',
    label: 'Usuários e perfis',
    icon: <UserOutlined />,
    permission: 'usuarios.visualizar',
  },
  {
    key: '/minha-conta/acessos',
    label: 'Segurança e acessos',
    icon: <SafetyCertificateOutlined />,
  },
  {
    key: '/configuracoes',
    label: 'Configurações',
    icon: <SettingOutlined />,
    permission: 'configuracoes.visualizar',
  },
  {
    key: '/assinatura',
    label: 'Assinatura',
    icon: <CreditCardOutlined />,
    permission: 'configuracoes.visualizar',
  },
  {
    key: '/admin/tenants',
    label: 'Tenants',
    icon: <BankOutlined />,
    profiles: ['gestor_saas'],
  },
];

export const menuItems: MenuProps['items'] = navigationItems.map((item) => ({ ...item }));

export function canViewNavigationItem(
  item: NavigationItem,
  permissions: string[],
  profiles: string[],
) {
  if (item.permission && !permissions.includes(item.permission)) return false;
  if (item.profiles && !item.profiles.some((profile) => profiles.includes(profile))) return false;
  return true;
}

export function getDefaultRoute(permissions: string[], profiles: string[]) {
  return (
    navigationItems.find((item) => canViewNavigationItem(item, permissions, profiles))?.key ??
    '/login'
  );
}

export function getNavigationLabel(pathname: string) {
  return navigationItems.find((item) => pathname.startsWith(item.key))?.label ?? 'Página';
}
