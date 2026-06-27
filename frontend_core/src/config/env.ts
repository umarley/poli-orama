export const env = {
  apiUrl: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1',
  appName: import.meta.env.VITE_APP_NAME ?? 'Vurix Eleitoral',
  enableDevtools: import.meta.env.VITE_ENABLE_DEVTOOLS === 'true',
} as const;
