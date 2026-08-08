import {
  BankOutlined,
  CalendarOutlined,
  CreditCardOutlined,
  DashboardOutlined,
  FlagOutlined,
  GlobalOutlined,
  ImportOutlined,
  MergeCellsOutlined,
  FileTextOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  ShareAltOutlined,
  SolutionOutlined,
  TagsOutlined,
  TeamOutlined,
  UnorderedListOutlined,
  UserOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';

import {
  getCommunityTerminologyLabels,
  getLeadershipTerminologyLabels,
} from '@/modules/tenants/tenant-preferences';

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
    key: '/relatorios',
    label: 'Relatórios',
    icon: <FileTextOutlined />,
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
    key: '/cadastro/segmentacao',
    label: 'Tags e comunidades',
    icon: <TagsOutlined />,
    permission: 'cadastro.visualizar',
  },
  {
    key: '/cadastro/indicacoes',
    label: 'Rede de indicações',
    icon: <ShareAltOutlined />,
    permission: 'cadastro.visualizar',
  },
  {
    key: '/cadastro/duplicidades',
    label: 'Duplicidades',
    icon: <MergeCellsOutlined />,
    permission: 'cadastro.visualizar',
    profiles: ['gestor', 'gestor_saas'],
  },
  {
    key: '/territorios',
    label: 'Territórios e mapa',
    icon: <GlobalOutlined />,
    permission: 'territorio.visualizar',
  },
  {
    key: '/metas',
    label: 'Metas e votos',
    icon: <FlagOutlined />,
    permission: 'metas.visualizar',
  },
  {
    key: '/importacoes',
    label: 'Importações',
    icon: <ImportOutlined />,
    permission: 'etl.visualizar',
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
    profiles: ['gestor', 'gestor_saas', 'coordenador_territorial'],
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
  {
    key: '/admin/eleicoes',
    label: 'Eleições oficiais',
    icon: <FlagOutlined />,
    profiles: ['gestor_saas'],
  },
];

export const menuItems: MenuProps['items'] = navigationItems.map((item) => ({ ...item }));

export function getNavigationItems(
  configuration?: { preferencias?: Record<string, unknown> } | null,
): NavigationItem[] {
  const communityTerms = getCommunityTerminologyLabels(configuration);
  const leadershipTerms = getLeadershipTerminologyLabels(configuration);
  return navigationItems.map((item) => {
    if (item.key === '/liderancas') return { ...item, label: leadershipTerms.menu };
    if (item.key === '/cadastro/segmentacao') {
      return { ...item, label: `Tags e ${communityTerms.pluralLower}` };
    }
    return item;
  });
}

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

export function getNavigationLabel(
  pathname: string,
  configuration?: { preferencias?: Record<string, unknown> } | null,
) {
  return (
    getNavigationItems(configuration)
      .sort((left, right) => right.key.length - left.key.length)
      .find((item) => pathname.startsWith(item.key))?.label ?? 'Página'
  );
}
