import { type SyntheticEvent, useEffect, useId, useState } from "react";
import { z } from "zod";
import { captureAttribution } from "../lib/attribution";
import { track } from "../lib/analytics";
import { contratacaoSchema, leadSchema } from "../lib/schemas";

type FormKind = "demo" | "contact" | "contract";
type FieldErrors = Record<string, string>;

interface Props {
  kind: FormKind;
  initialPlan?: string;
  initialCycle?: string;
}

function fieldValue(form: FormData, name: string): string {
  return String(form.get(name) || "").trim();
}

function apiError(result: unknown): string {
  if (!result || typeof result !== "object") return "Não foi possível concluir o envio.";
  const data = result as { message?: string; detail?: string | { message?: string } };
  if (data.message) return data.message;
  if (typeof data.detail === "string") return data.detail;
  if (data.detail?.message) return data.detail.message;
  return "Não foi possível concluir o envio.";
}

function validationErrors(error: z.ZodError): FieldErrors {
  return Object.fromEntries(error.issues.map((issue) => [String(issue.path[0]), issue.message]));
}

export function CommercialForm({ kind, initialPlan, initialCycle }: Props) {
  const formId = useId();
  const [pending, setPending] = useState(false);
  const [ready, setReady] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [feedback, setFeedback] = useState<{ type: "ok" | "error"; message: string }>();
  const isContract = kind === "contract";

  useEffect(() => setReady(true), []);

  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const origem = captureAttribution();
    setErrors({});
    setFeedback(undefined);

    const raw = isContract
      ? {
          plano_slug: fieldValue(form, "plano_slug"),
          ciclo: fieldValue(form, "ciclo"),
          nome: fieldValue(form, "nome"),
          email: fieldValue(form, "email"),
          telefone: fieldValue(form, "telefone"),
          documento: fieldValue(form, "documento"),
          nome_campanha: fieldValue(form, "nome_campanha"),
          slug_solicitado: fieldValue(form, "slug_solicitado"),
          tipo_organizacao: fieldValue(form, "tipo_organizacao"),
          cidade: fieldValue(form, "cidade"),
          uf: fieldValue(form, "uf"),
          aceite_termos: form.get("aceite_termos") === "on",
          aceite_privacidade: form.get("aceite_privacidade") === "on",
          origem,
        }
      : {
          nome: fieldValue(form, "nome"),
          email: fieldValue(form, "email"),
          telefone: fieldValue(form, "telefone"),
          organizacao: fieldValue(form, "organizacao"),
          mensagem: fieldValue(form, "mensagem"),
          interesse: kind === "demo" ? "demo" : "contato",
          consentimento: form.get("consentimento") === "on",
          origem,
        };
    const parsed = (isContract ? contratacaoSchema : leadSchema).safeParse(raw);
    if (!parsed.success) {
      const nextErrors = validationErrors(parsed.error);
      setErrors(nextErrors);
      const firstField = Object.keys(nextErrors)[0];
      (formElement.elements.namedItem(firstField) as HTMLElement | null)?.focus();
      return;
    }

    setPending(true);
    try {
      if (!isContract) {
        const lead = parsed.data as z.infer<typeof leadSchema>;
        const response = await fetch(
          `${import.meta.env.PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/public/leads`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              nome: lead.nome,
              email: lead.email,
              telefone: lead.telefone || null,
              organizacao: lead.organizacao || null,
              mensagem: lead.mensagem || null,
              interesse: lead.interesse,
              consentimento: lead.consentimento,
              origem: lead.origem,
            }),
          },
        );
        const result: unknown = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(apiError(result));
        track(kind === "demo" ? "demo_request" : "lead_submit", { lead_type: kind });
        setFeedback({ type: "ok", message: "Solicitação recebida. Entraremos em contato." });
        formElement.reset();
        return;
      }

      const contract = parsed.data as z.infer<typeof contratacaoSchema>;
      const idempotencyKey = crypto.randomUUID();
      const response = await fetch(
        `${import.meta.env.PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/public/contratacoes`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey },
          body: JSON.stringify({
            plano_slug: contract.plano_slug,
            nome: contract.nome,
            email: contract.email,
            telefone: contract.telefone,
            documento: contract.documento || null,
            nome_campanha: contract.nome_campanha,
            slug_solicitado: contract.slug_solicitado,
            ciclo: contract.ciclo,
            tipo_organizacao: contract.tipo_organizacao,
            cidade: contract.cidade || null,
            uf: contract.uf,
            consentimento: contract.aceite_privacidade,
            aceite_termos: contract.aceite_termos,
            origem: contract.origem,
          }),
        },
      );
      const result = (await response.json().catch(() => ({}))) as { id?: string };
      if (!response.ok || !result.id) throw new Error(apiError(result));

      track("checkout_start", {
        plan_slug: contract.plano_slug,
        billing_cycle: contract.ciclo,
      });
      const checkoutResponse = await fetch(
        `${import.meta.env.PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/public/checkout/session`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Idempotency-Key": `${idempotencyKey}-checkout`,
          },
          body: JSON.stringify({
            contratacao_id: result.id,
            success_url: `${window.location.origin}/checkout/sucesso`,
            cancel_url: `${window.location.origin}/checkout/falha?motivo=cancelado`,
          }),
        },
      );
      const checkout = (await checkoutResponse.json().catch(() => ({}))) as {
        checkout_url?: string;
        session_id?: string;
        status?: string;
      };
      if (!checkoutResponse.ok) {
        track("checkout_failure", { plan_slug: contract.plano_slug, reason: "unavailable" });
        window.location.assign(
          `/checkout/falha?motivo=indisponivel&contratacao=${encodeURIComponent(result.id)}`,
        );
        return;
      }
      if (checkout.checkout_url) {
        window.location.assign(checkout.checkout_url);
        return;
      }
      window.location.assign(
        `/checkout/sucesso?status=${encodeURIComponent(checkout.status || "pendente")}&session_id=${encodeURIComponent(checkout.session_id || "")}`,
      );
    } catch (error) {
      setFeedback({
        type: "error",
        message: error instanceof Error ? error.message : "Erro inesperado. Tente novamente.",
      });
    } finally {
      setPending(false);
    }
  }

  const describedBy = (name: string) => (errors[name] ? `${formId}-${name}-error` : undefined);
  const error = (name: string) =>
    errors[name] ? (
      <span className="field-error" id={`${formId}-${name}-error`}>
        {errors[name]}
      </span>
    ) : null;

  return (
    <form className="form-card" onSubmit={submit} noValidate aria-busy={pending}>
      <div className="form-grid">
        <label>
          Nome {isContract ? "do responsável" : ""}
          <input name="nome" autoComplete="name" aria-invalid={!!errors.nome} aria-describedby={describedBy("nome")} />
          {error("nome")}
        </label>
        <label>
          E-mail
          <input name="email" type="email" autoComplete="email" aria-invalid={!!errors.email} aria-describedby={describedBy("email")} />
          {error("email")}
        </label>
        <label>
          Telefone {isContract ? "" : "(opcional)"}
          <input name="telefone" type="tel" autoComplete="tel" aria-invalid={!!errors.telefone} aria-describedby={describedBy("telefone")} />
          {error("telefone")}
        </label>
        {!isContract ? (
          <>
            <label>
              Organização (opcional)
              <input name="organizacao" autoComplete="organization" />
            </label>
            <label className="full">
              Como podemos ajudar? (opcional)
              <textarea name="mensagem" rows={4} />
            </label>
          </>
        ) : (
          <>
            <label>
              Plano
              <select name="plano_slug" defaultValue={initialPlan || "profissional"}>
                <option value="essencial">Essencial</option>
                <option value="profissional">Profissional</option>
                <option value="operacao">Operação</option>
                <option value="enterprise">Enterprise</option>
              </select>
            </label>
            <label>
              Ciclo
              <select name="ciclo" defaultValue={initialCycle === "anual" ? "anual" : "mensal"}>
                <option value="mensal">Mensal</option>
                <option value="anual">Anual — 15% de economia</option>
              </select>
            </label>
            <label>
              Organização ou campanha
              <input name="nome_campanha" autoComplete="organization" aria-invalid={!!errors.nome_campanha} aria-describedby={describedBy("nome_campanha")} />
              {error("nome_campanha")}
            </label>
            <label>
              Tipo de organização
              <select name="tipo_organizacao" defaultValue="candidato">
                <option value="candidato">Candidato</option>
                <option value="partido">Partido</option>
                <option value="consultoria">Consultoria</option>
                <option value="mandato">Mandato</option>
                <option value="outro">Outro</option>
              </select>
            </label>
            <label>
              Endereço desejado
              <input name="slug_solicitado" placeholder="minha-campanha" aria-invalid={!!errors.slug_solicitado} aria-describedby={describedBy("slug_solicitado")} />
              {error("slug_solicitado")}
            </label>
            <label>
              CPF/CNPJ (opcional)
              <input name="documento" inputMode="numeric" autoComplete="off" />
            </label>
            <label>
              Cidade (opcional)
              <input name="cidade" autoComplete="address-level2" />
            </label>
            <label>
              UF
              <input name="uf" maxLength={2} autoComplete="address-level1" aria-invalid={!!errors.uf} aria-describedby={describedBy("uf")} />
              {error("uf")}
            </label>
          </>
        )}
      </div>
      {isContract ? (
        <div className="consents">
          <label className="checkbox">
            <input name="aceite_termos" type="checkbox" aria-invalid={!!errors.aceite_termos} aria-describedby={describedBy("aceite_termos")} />
            <span>Li e aceito os <a href="/termos-de-uso" target="_blank">termos de uso</a>.</span>
          </label>
          {error("aceite_termos")}
          <label className="checkbox">
            <input name="aceite_privacidade" type="checkbox" aria-invalid={!!errors.aceite_privacidade} aria-describedby={describedBy("aceite_privacidade")} />
            <span>Autorizo o tratamento dos dados para esta contratação conforme a <a href="/politica-de-privacidade" target="_blank">política de privacidade</a>.</span>
          </label>
          {error("aceite_privacidade")}
        </div>
      ) : (
        <div>
          <label className="checkbox">
            <input name="consentimento" type="checkbox" aria-invalid={!!errors.consentimento} aria-describedby={describedBy("consentimento")} />
            <span>Autorizo o uso destes dados para atendimento comercial conforme a <a href="/politica-de-privacidade" target="_blank">política de privacidade</a>.</span>
          </label>
          {error("consentimento")}
        </div>
      )}
      <button className="button" type="submit" disabled={pending || !ready}>
        {pending ? "Enviando…" : isContract ? "Continuar para o checkout" : "Enviar solicitação"}
      </button>
      {feedback && (
        <div className={`feedback ${feedback.type === "error" ? "error" : ""}`} role={feedback.type === "error" ? "alert" : "status"} tabIndex={-1}>
          {feedback.message}
        </div>
      )}
    </form>
  );
}
