export interface DashboardFilters {
  data_inicio: string;
  data_fim: string;
  territorio_id?: number;
  lideranca_id?: number;
}

export interface DashboardOverview {
  filtros: DashboardFilters;
  cadastros: {
    total: number;
    novos_periodo: number;
    incompletos_pendentes: number;
    duplicidades_abertas: number;
    completude_media: number;
  };
  liderancas: {
    total_lideres: number;
    total_liderados: number;
    media_liderados: number;
  };
  metas: {
    metas_ativas: number;
    atingidas: number;
    em_risco: number;
    percentual_medio: number;
  };
  demandas: {
    total: number;
    pendentes: number;
    em_andamento: number;
    concluidas: number;
    vencidas: number;
  };
  eventos: {
    total_periodo: number;
    realizados: number;
    cancelados: number;
    presencas_registradas: number;
  };
  gerado_em: string;
}

export interface Birthday {
  pessoa_id: number;
  nome: string;
  data_nascimento: string;
  idade: number | null;
  territorio: string | null;
}

export interface Birthdays {
  hoje: Birthday[];
  mes: Birthday[];
}

export interface CommemorativeDate {
  id: number;
  nome: string;
  categoria: string | null;
  data: string;
  ambito: string;
}

export type ReportType = 'metas' | 'demandas' | 'agenda' | 'cadastros' | 'lideres';
export type ReportRow = Record<string, string | number | boolean | null>;

export interface DashboardConfiguration {
  id: number | null;
  nome: string;
  perfil: string;
  filtros_padrao: Record<string, unknown>;
  widgets: string[];
}
