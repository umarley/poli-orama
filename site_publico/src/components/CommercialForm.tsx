import { type SyntheticEvent, useState } from "react";

export function CommercialForm({
  kind,
  initialPlan,
}: {
  kind: "lead" | "contract";
  initialPlan?: string;
}) {
  const [pending, setPending] = useState(false);
  const [feedback, setFeedback] = useState<{
    type: "ok" | "error";
    message: string;
  }>();

  async function submit(event: SyntheticEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setFeedback(undefined);
    const form = new FormData(event.currentTarget);
    const params = new URLSearchParams(window.location.search);
    const common = {
      nome: form.get("nome"),
      email: form.get("email"),
      telefone: form.get("telefone") || null,
      consentimento: form.get("consentimento") === "on",
      origem: {
        utm_source: params.get("utm_source"),
        utm_medium: params.get("utm_medium"),
        utm_campaign: params.get("utm_campaign"),
        pagina_origem: window.location.href,
      },
    };
    const payload =
      kind === "lead"
        ? {
            ...common,
            organizacao: form.get("organizacao"),
            mensagem: form.get("mensagem"),
          }
        : {
            ...common,
            plano_slug: form.get("plano_slug"),
            nome_campanha: form.get("nome_campanha"),
            slug_solicitado: form.get("slug_solicitado"),
            documento: form.get("documento") || null,
          };
    try {
      const response = await fetch(
        `${import.meta.env.PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/public/${kind === "lead" ? "leads" : "contratacoes"}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        },
      );
      const result = await response.json();
      if (!response.ok)
        throw new Error(result.message || "Não foi possível enviar.");
      setFeedback({
        type: "ok",
        message:
          kind === "lead"
            ? "Solicitação recebida. Entraremos em contato."
            : "Pré-cadastro recebido. A ativação ocorrerá após aprovação comercial ou pagamento.",
      });
      event.currentTarget.reset();
    } catch (error) {
      setFeedback({
        type: "error",
        message: error instanceof Error ? error.message : "Erro inesperado.",
      });
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="form-card" onSubmit={submit}>
      <label>
        Nome
        <input name="nome" required minLength={2} />
      </label>
      <label>
        E-mail
        <input name="email" type="email" required />
      </label>
      <label>
        Telefone
        <input name="telefone" type="tel" />
      </label>
      {kind === "lead" ? (
        <>
          <label>
            Organização
            <input name="organizacao" />
          </label>
          <label>
            Como podemos ajudar?
            <textarea name="mensagem" rows={4} />
          </label>
        </>
      ) : (
        <>
          <label>
            Plano
            <select
              name="plano_slug"
              defaultValue={initialPlan || "profissional"}
              required
            >
              <option value="essencial">Essencial</option>
              <option value="profissional">Profissional</option>
              <option value="operacao">Operação</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </label>
          <label>
            Nome da campanha
            <input name="nome_campanha" required minLength={2} />
          </label>
          <label>
            Endereço desejado
            <input
              name="slug_solicitado"
              required
              pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
              placeholder="minha-campanha"
            />
          </label>
          <label>
            CPF/CNPJ (opcional)
            <input name="documento" />
          </label>
        </>
      )}
      <label className="checkbox">
        <input name="consentimento" type="checkbox" required />
        <span>
          Concordo com o uso destes dados para atendimento comercial, conforme a
          política de privacidade.
        </span>
      </label>
      <button className="button" type="submit" disabled={pending}>
        {pending ? "Enviando…" : "Enviar"}
      </button>
      {feedback && (
        <div
          className={`feedback ${feedback.type === "error" ? "error" : ""}`}
          role="status"
        >
          {feedback.message}
        </div>
      )}
    </form>
  );
}
