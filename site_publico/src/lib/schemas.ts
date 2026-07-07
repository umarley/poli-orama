import { z } from "zod";

const optionalText = (max: number) =>
  z.string().trim().max(max, `Use no máximo ${max} caracteres.`).optional().or(z.literal(""));

export const origemSchema = z.object({
  utm_source: optionalText(120),
  utm_medium: optionalText(120),
  utm_campaign: optionalText(120),
  utm_content: optionalText(120),
  utm_term: optionalText(120),
  pagina_origem: optionalText(500),
  referrer: optionalText(500),
  landing_page: optionalText(500),
});

export const leadSchema = z.object({
  nome: z.string().trim().min(2, "Informe seu nome.").max(180),
  email: z.string().trim().max(254).pipe(z.email({ error: "Informe um e-mail válido." })),
  telefone: optionalText(20),
  organizacao: optionalText(180),
  mensagem: optionalText(2000),
  interesse: z.enum(["demo", "planos", "contato", "checkout_abandonado"]),
  consentimento: z.literal(true, { error: "Autorize o contato para continuar." }),
  origem: origemSchema,
});

export const contratacaoSchema = z.object({
  plano_slug: z.string().trim().min(2).max(80),
  ciclo: z.enum(["mensal", "anual"]),
  nome: z.string().trim().min(2, "Informe o nome do responsável.").max(180),
  email: z.string().trim().max(254).pipe(z.email({ error: "Informe um e-mail válido." })),
  telefone: z.string().trim().min(8, "Informe um telefone para a contratação.").max(20),
  documento: optionalText(20),
  nome_campanha: z.string().trim().min(2, "Informe o nome da organização ou campanha.").max(180),
  slug_solicitado: z
    .string()
    .trim()
    .min(2, "Informe o endereço desejado.")
    .max(80)
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "Use apenas letras minúsculas, números e hífens."),
  tipo_organizacao: z.enum(["candidato", "partido", "consultoria", "mandato", "outro"]),
  cidade: optionalText(120),
  uf: z.string().trim().length(2, "Use a sigla com 2 letras.").toUpperCase(),
  aceite_termos: z.literal(true, { error: "Aceite os termos de uso para continuar." }),
  aceite_privacidade: z.literal(true, {
    error: "Aceite a política de privacidade para continuar.",
  }),
  origem: origemSchema,
});

export type LeadFormData = z.infer<typeof leadSchema>;
export type ContractFormData = z.infer<typeof contratacaoSchema>;
