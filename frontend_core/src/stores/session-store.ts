import { create } from 'zustand';
import { persist } from 'zustand/middleware';

import type { AuthUser } from '@/modules/auth/types';

export interface SessionUser {
  id: number;
  name: string;
  email: string;
  initials: string;
  role: string;
  profiles: string[];
  permissions: string[];
  mustChangePassword: boolean;
  mfaEnabled: boolean;
}

export interface Tenant {
  id: number;
  name: string;
  slug: string;
  status: 'pendente' | 'ativo' | 'suspenso' | 'cancelado' | 'trial' | 'inadimplente';
}

export type ElectionScope = 'municipal' | 'estadual' | 'federal' | 'suplementar' | 'outra';

export interface Election {
  id: string;
  year: number;
  type: ElectionScope;
  round: 1 | 2;
  date: string;
}

export interface CampaignElection {
  id: string;
  name: string;
  office: string;
  active: boolean;
  election: Election;
}

interface SessionState {
  user: SessionUser | null;
  tenant: Tenant | null;
  currentCampaign: CampaignElection | null;
  accessToken: string | null;
  refreshToken: string | null;
  accessTokenExpiresAt: number | null;
  isAuthenticated: boolean;
  setSession: (
    user: SessionUser,
    tenant: Tenant,
    currentCampaign: CampaignElection | null,
    accessToken: string,
    refreshToken: string,
    expiresIn: number,
  ) => void;
  updateAuthentication: (
    apiUser: AuthUser,
    accessToken: string,
    refreshToken: string,
    expiresIn: number,
  ) => void;
  updateUser: (apiUser: AuthUser) => void;
  setTenant: (tenant: Tenant) => void;
  setCurrentCampaign: (campaign: CampaignElection | null) => void;
  clearSession: () => void;
}

export function mapAuthUser(user: AuthUser): SessionUser {
  const profiles = user.perfis.map((profile) => profile.codigo);
  const initials = user.nome
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');
  return {
    id: user.id,
    name: user.nome,
    email: user.email,
    initials: initials || 'VU',
    role: profiles[0] ?? 'usuario',
    profiles,
    permissions: user.permissoes,
    mustChangePassword: user.deve_alterar_senha,
    mfaEnabled: user.mfa_habilitado,
  };
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      user: null,
      tenant: null,
      currentCampaign: null,
      accessToken: null,
      refreshToken: null,
      accessTokenExpiresAt: null,
      isAuthenticated: false,
      setSession: (user, tenant, currentCampaign, accessToken, refreshToken, expiresIn) =>
        set({
          user,
          tenant,
          currentCampaign,
          accessToken,
          refreshToken,
          accessTokenExpiresAt: Date.now() + expiresIn * 1000,
          isAuthenticated: true,
        }),
      updateAuthentication: (apiUser, accessToken, refreshToken, expiresIn) =>
        set({
          user: mapAuthUser(apiUser),
          accessToken,
          refreshToken,
          accessTokenExpiresAt: Date.now() + expiresIn * 1000,
          isAuthenticated: true,
        }),
      updateUser: (apiUser) => set({ user: mapAuthUser(apiUser) }),
      setTenant: (tenant) => set({ tenant }),
      setCurrentCampaign: (currentCampaign) => set({ currentCampaign }),
      clearSession: () =>
        set({
          user: null,
          tenant: null,
          currentCampaign: null,
          accessToken: null,
          refreshToken: null,
          accessTokenExpiresAt: null,
          isAuthenticated: false,
        }),
    }),
    {
      name: 'vurix-eleitoral-session',
      version: 5,
      migrate: () =>
        ({
          user: null,
          tenant: null,
          currentCampaign: null,
          accessToken: null,
          refreshToken: null,
          accessTokenExpiresAt: null,
          isAuthenticated: false,
        }) as SessionState,
      partialize: ({
        user,
        tenant,
        currentCampaign,
        accessToken,
        refreshToken,
        accessTokenExpiresAt,
        isAuthenticated,
      }) => ({
        user,
        tenant,
        currentCampaign,
        accessToken,
        refreshToken,
        accessTokenExpiresAt,
        isAuthenticated,
      }),
    },
  ),
);
