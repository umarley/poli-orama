/// <reference types="astro/client" />

interface ImportMetaEnv {
  readonly PUBLIC_API_BASE_URL?: string;
  readonly PUBLIC_APP_LOGIN_URL?: string;
  readonly PUBLIC_SITE_URL?: string;
  readonly PUBLIC_ENVIRONMENT?: "development" | "staging" | "production";
  readonly PUBLIC_ANALYTICS_PROVIDER?: "none" | "google" | "plausible";
  readonly PUBLIC_ANALYTICS_ID?: string;
  readonly PUBLIC_SUPPORT_EMAIL?: string;
  readonly PUBLIC_SUPPORT_WHATSAPP?: string;
  readonly PUBLIC_PLANS_SOURCE?: "api" | "static";
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
