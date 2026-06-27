import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface SessionUser {
  id: string;
  name: string;
  email: string;
  initials: string;
}

export interface Tenant {
  id: string;
  name: string;
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
  isAuthenticated: boolean;
  setSession: (
    user: SessionUser,
    tenant: Tenant,
    currentCampaign: CampaignElection | null,
    accessToken: string,
  ) => void;
  setTenant: (tenant: Tenant) => void;
  setCurrentCampaign: (campaign: CampaignElection) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      user: null,
      tenant: null,
      currentCampaign: null,
      accessToken: null,
      isAuthenticated: false,
      setSession: (user, tenant, currentCampaign, accessToken) =>
        set({ user, tenant, currentCampaign, accessToken, isAuthenticated: true }),
      setTenant: (tenant) => set({ tenant }),
      setCurrentCampaign: (currentCampaign) => set({ currentCampaign }),
      clearSession: () =>
        set({
          user: null,
          tenant: null,
          currentCampaign: null,
          accessToken: null,
          isAuthenticated: false,
        }),
    }),
    {
      name: 'vurix-eleitoral-session',
      version: 2,
      migrate: () =>
        ({
          user: null,
          tenant: null,
          currentCampaign: null,
          accessToken: null,
          isAuthenticated: false,
        }) as SessionState,
      partialize: ({ user, tenant, currentCampaign, accessToken, isAuthenticated }) => ({
        user,
        tenant,
        currentCampaign,
        accessToken,
        isAuthenticated,
      }),
    },
  ),
);
