import { useEffect, useState } from "react";
import {
  annualMonthlyEquivalent,
  planosFallback,
  type BillingCycle,
  type PublicPlan,
} from "../data/planos";
import { track } from "../lib/analytics";

function money(value: number, currency = "BRL"): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

export function PricingGrid() {
  const [plans, setPlans] = useState<PublicPlan[]>(planosFallback);
  const [cycle, setCycle] = useState<BillingCycle>("mensal");

  useEffect(() => {
    track("pricing_view");
    if (import.meta.env.PUBLIC_PLANS_SOURCE === "static") return;
    const controller = new AbortController();
    fetch(`${import.meta.env.PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/public/planos`, {
      signal: controller.signal,
    })
      .then((response) => {
        if (!response.ok) throw new Error("API de planos indisponível.");
        return response.json() as Promise<PublicPlan[]>;
      })
      .then((result) => setPlans(result.length ? result : planosFallback))
      .catch(() => {
        if (!controller.signal.aborted) setPlans(planosFallback);
      });
    return () => controller.abort();
  }, []);

  return (
    <>
      <fieldset className="cycle-toggle">
        <legend className="sr-only">Ciclo de cobrança</legend>
        <button
          className={cycle === "mensal" ? "active" : ""}
          type="button"
          aria-pressed={cycle === "mensal"}
          onClick={() => setCycle("mensal")}
        >
          Mensal
        </button>
        <button
          className={cycle === "anual" ? "active" : ""}
          type="button"
          aria-pressed={cycle === "anual"}
          onClick={() => setCycle("anual")}
        >
          Anual <small>15% de economia</small>
        </button>
      </fieldset>
      <div className="plans">
        {plans
          .toSorted((a, b) => a.ordem_comercial - b.ordem_comercial)
          .map((plan) => {
            const monthlyPrice =
              cycle === "anual" ? annualMonthlyEquivalent(plan) : Number(plan.preco_mensal);
            return (
              <article className={`plan ${plan.recomendado ? "recommended" : ""}`} key={plan.slug}>
                {plan.recomendado && <span className="plan-badge">Mais escolhido</span>}
                <h2>{plan.nome}</h2>
                <p className="muted">{plan.descricao}</p>
                <div className="price">
                  {monthlyPrice
                    ? `${money(monthlyPrice, plan.moeda)}/mês`
                    : "Sob consulta"}
                </div>
                {cycle === "anual" && monthlyPrice > 0 && (
                  <small>Cobrança anual de {money(monthlyPrice * 12, plan.moeda)}</small>
                )}
                <ul>
                  <li>
                    {plan.limite_usuarios
                      ? `Até ${plan.limite_usuarios} usuários`
                      : "Usuários sob medida"}
                  </li>
                  <li>
                    {plan.limite_pessoas
                      ? `Até ${plan.limite_pessoas.toLocaleString("pt-BR")} pessoas`
                      : "Base sob medida"}
                  </li>
                  <li>
                    {plan.limite_armazenamento_mb
                      ? `${Math.round(plan.limite_armazenamento_mb / 1024)} GB de armazenamento`
                      : "Armazenamento sob medida"}
                  </li>
                </ul>
                <a
                  className="button"
                  href={`/contratar?plano=${plan.slug}&ciclo=${cycle}`}
                  onClick={() => track("plan_select", { plan_slug: plan.slug, billing_cycle: cycle })}
                >
                  {plan.slug === "enterprise" ? "Falar com consultor" : "Contratar"}
                </a>
              </article>
            );
          })}
      </div>
    </>
  );
}
