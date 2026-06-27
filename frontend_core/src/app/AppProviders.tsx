import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import dayjs from 'dayjs';
import 'dayjs/locale/pt-br';
import { useState, type PropsWithChildren } from 'react';

import { themeConfig } from '@/styles/theme';

dayjs.locale('pt-br');

export function AppProviders({ children }: PropsWithChildren) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
          mutations: {
            retry: false,
          },
        },
      }),
  );

  return (
    <ConfigProvider locale={ptBR} theme={themeConfig}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </ConfigProvider>
  );
}
