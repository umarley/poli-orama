import { useEffect, useState } from "react";

interface Plan {
  slug: string;
  nome: string;
  descricao?: string;
  preco_mensal: string;
  limite_usuarios?: number;
  limite_pessoas?: number;
}

const fallback: Plan[] = [
  {
    slug: "essencial",
    nome: "Essencial",
    preco_mensal: "299",
    limite_usuarios: 5,
    limite_pessoas: 10000,
  },
  {
    slug: "profissional",
    nome: "Profissional",
    preco_mensal: "699",
    limite_usuarios: 15,
    limite_pessoas: 50000,
  },
  {
    slug: "operacao",
    nome: "Operação",
    preco_mensal: "1499",
    limite_usuarios: 50,
    limite_pessoas: 200000,
  },
  { slug: "enterprise", nome: "Enterprise", preco_mensal: "0" },
];

export function PricingGrid() {
  const [plans, setPlans] = useState(fallback);
  useEffect(() => {
    fetch(
      `${import.meta.env.PUBLIC_API_BASE_URL || "http://localhost:8000"}/api/public/planos`,
    )
      .then((response) => {
        if (!response.ok) throw new Error("API indisponível");
        return response.json() as Promise<Plan[]>;
      })
      .then(setPlans)
      .catch(() => setPlans(fallback));
  }, []);

  return (
    <div className="plans">
      {plans.map((plan) => (
        <article className="plan" key={plan.slug}>
          <h2>{plan.nome}</h2>
          <p className="muted">
            {plan.descricao || "Plano preparado para sua operação."}
          </p>
          <div className="price">
            {Number(plan.preco_mensal)
              ? `R$ ${Number(plan.preco_mensal).toLocaleString("pt-BR")}/mês`
              : "Sob consulta"}
          </div>
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
          </ul>
          <a className="button" href={`/contratar?plano=${plan.slug}`}>
            Contratar
          </a>
        </article>
      ))}
    </div>
  );
}
