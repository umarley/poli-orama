import type { z } from "zod";
import type { origemSchema } from "./schemas";

export type Attribution = z.infer<typeof origemSchema>;

const UTM_KEYS = [
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_content",
  "utm_term",
] as const;

export function captureAttribution(): Attribution {
  const params = new URLSearchParams(window.location.search);
  const stored = sessionStorage.getItem("vurix_attribution");
  let previous: Attribution = {};
  try {
    previous = stored ? (JSON.parse(stored) as Attribution) : {};
  } catch {
    sessionStorage.removeItem("vurix_attribution");
  }
  const current: Attribution = {
    ...previous,
    pagina_origem: window.location.href,
    landing_page: previous.landing_page || window.location.href,
    referrer: previous.referrer || document.referrer || undefined,
  };
  for (const key of UTM_KEYS) current[key] = params.get(key) || current[key] || undefined;
  sessionStorage.setItem("vurix_attribution", JSON.stringify(current));
  return current;
}
