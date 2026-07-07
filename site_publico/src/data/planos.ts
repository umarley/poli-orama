export type BillingCycle = "mensal" | "anual";

export interface PublicPlan {
  id?: number;
  uuid_publico?: string;
  slug: string;
  nome: string;
  descricao: string;
  preco_mensal: string;
  moeda: string;
  limite_usuarios: number | null;
  limite_pessoas: number | null;
  limite_armazenamento_mb: number | null;
  recursos: Record<string, boolean | string | number>;
  ordem_comercial: number;
  recomendado?: boolean;
}

export const planosFallback: PublicPlan[] = [
  {
    slug: "essencial",
    nome: "Essencial",
    descricao: "Organização da base, equipe e rotina de uma campanha local.",
    preco_mensal: "299.00",
    moeda: "BRL",
    limite_usuarios: 5,
    limite_pessoas: 10_000,
    limite_armazenamento_mb: 5_120,
    recursos: { cadastro: true, agenda: true, demandas: true, relatorios: "básicos" },
    ordem_comercial: 10,
  },
  {
    slug: "profissional",
    nome: "Profissional",
    descricao: "Gestão integrada de território, lideranças, metas e demandas.",
    preco_mensal: "699.00",
    moeda: "BRL",
    limite_usuarios: 15,
    limite_pessoas: 50_000,
    limite_armazenamento_mb: 20_480,
    recursos: {
      cadastro: true,
      territorio: true,
      metas: true,
      agenda: true,
      demandas: true,
      relatorios: "completos",
    },
    ordem_comercial: 20,
    recomendado: true,
  },
  {
    slug: "operacao",
    nome: "Operação",
    descricao: "Escala, modo eleição e governança para operações maiores.",
    preco_mensal: "1499.00",
    moeda: "BRL",
    limite_usuarios: 50,
    limite_pessoas: 200_000,
    limite_armazenamento_mb: 102_400,
    recursos: {
      cadastro: true,
      territorio: true,
      metas: true,
      agenda: true,
      demandas: true,
      comunicacao: true,
      modo_eleicao: true,
      suporte: "prioritário",
    },
    ordem_comercial: 30,
  },
  {
    slug: "enterprise",
    nome: "Enterprise",
    descricao: "Limites, integrações e implantação definidos com sua equipe.",
    preco_mensal: "0.00",
    moeda: "BRL",
    limite_usuarios: null,
    limite_pessoas: null,
    limite_armazenamento_mb: null,
    recursos: { integracoes: true, implantacao: "personalizada", suporte: "dedicado" },
    ordem_comercial: 40,
  },
];

export function annualMonthlyEquivalent(plan: PublicPlan): number {
  return Number(plan.preco_mensal) * 0.85;
}
