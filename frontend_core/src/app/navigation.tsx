import {
  BankOutlined,
  CalendarOutlined,
  CreditCardOutlined,
  DashboardOutlined,
  FlagOutlined,
  IdcardOutlined,
  SettingOutlined,
  SolutionOutlined,
  TeamOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';

export interface NavigationItem {
  key: string;
  label: string;
  icon: React.ReactNode;
}

export const navigationItems: NavigationItem[] = [
  { key: '/dashboard', label: 'Painel de controle', icon: <DashboardOutlined /> },
  { key: '/cadastro', label: 'Pessoas e eleitores', icon: <TeamOutlined /> },
  { key: '/liderancas', label: 'Lideranças', icon: <SolutionOutlined /> },
  { key: '/metas', label: 'Metas e votos', icon: <FlagOutlined /> },
  { key: '/agenda', label: 'Agenda', icon: <CalendarOutlined /> },
  { key: '/demandas', label: 'Demandas', icon: <UnorderedListOutlined /> },
  { key: '/configuracoes', label: 'Configurações', icon: <SettingOutlined /> },
  { key: '/assinatura', label: 'Assinatura', icon: <CreditCardOutlined /> },
  { key: '/admin/tenants', label: 'Tenants', icon: <BankOutlined /> },
];

export const menuItems: MenuProps['items'] = navigationItems.map((item) => ({
  ...item,
  icon: item.icon ?? <IdcardOutlined />,
}));

export function getNavigationLabel(pathname: string) {
  return navigationItems.find((item) => pathname.startsWith(item.key))?.label ?? 'Página';
}
