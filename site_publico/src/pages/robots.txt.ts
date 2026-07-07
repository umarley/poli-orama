import type { APIRoute } from "astro";

export const GET: APIRoute = ({ site }) => {
  const environment = import.meta.env.PUBLIC_ENVIRONMENT || "development";
  const indexable = environment === "production";
  const body = indexable
    ? `User-agent: *\nAllow: /\nSitemap: ${new URL("sitemap-index.xml", site)}\n`
    : "User-agent: *\nDisallow: /\n";
  return new Response(body, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
};
