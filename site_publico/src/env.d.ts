/// <reference types="astro/client" />

interface ImportMetaEnv {
  readonly PUBLIC_API_BASE_URL?: string;
  readonly PUBLIC_APP_LOGIN_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
