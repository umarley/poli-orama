import type { AccessProfile, AuthUser, TerritorialAccess } from '@/modules/auth/types';

export type UserRecord = AuthUser;
export type ProfileRecord = AccessProfile;

export interface UserCreateInput {
  nome: string;
  email: string;
  senha: string;
  telefone?: string;
  pessoa_id?: number;
  perfil_ids: number[];
}

export interface UserUpdateInput {
  nome?: string;
  email?: string;
  telefone?: string;
  pessoa_id?: number;
  status?: UserRecord['status'];
  perfil_ids?: number[];
}

export type TerritorialAccessInput = Omit<
  TerritorialAccess,
  'id' | 'tenant_id' | 'usuario_id' | 'criado_em'
>;
