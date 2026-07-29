export const env = {
  apiUrl: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  appName: import.meta.env.VITE_APP_NAME ?? 'Poliorama',
  enableDevtools: import.meta.env.VITE_ENABLE_DEVTOOLS === 'true',
} as const;
