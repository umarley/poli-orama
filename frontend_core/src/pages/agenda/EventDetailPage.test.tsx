import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { AgendaEventDetail } from '@/modules/agenda/types';

const { getEvent, getConfiguration, listTerritories, listCatalog } = vi.hoisted(() => ({
  getEvent: vi.fn(),
  getConfiguration: vi.fn(),
  listTerritories: vi.fn(),
  listCatalog: vi.fn(),
}));

vi.mock('@/modules/agenda/agenda-service', () => ({
  getEvent,
  addAgendaItem: vi.fn(),
  addInvitation: vi.fn(),
  addLeadership: vi.fn(),
  addParticipant: vi.fn(),
  cancelEvent: vi.fn(),
  createDemand: vi.fn(),
  recordAttendance: vi.fn(),
  removeParticipant: vi.fn(),
  updateEvent: vi.fn(),
}));

vi.mock('@/modules/tenants/tenant-service', () => ({
  getTenantConfiguration: getConfiguration,
}));

vi.mock('@/modules/territorios/territorios-service', () => ({
  listarTerritorios: listTerritories,
}));

vi.mock('@/modules/demandas/demandas-service', () => ({
  listDemandCatalog: listCatalog,
}));

vi.mock('@/components/arquivos/AttachmentsPanel', () => ({
  AttachmentsPanel: () => null,
}));

vi.mock('@/components/feedback/AppToast', () => ({
  AppToast: { success: vi.fn(), error: vi.fn() },
}));

const sessionState = {
  user: { permissions: [] as string[], profiles: [] as string[] },
};

vi.mock('@/stores/session-store', () => ({
  useSessionStore: (selector: (state: typeof sessionState) => unknown) => selector(sessionState),
}));

import { EventDetailPage } from './EventDetailPage';

function eventDetail(): AgendaEventDetail {
  return {
    id: 7,
    uuid_publico: 'evt-7',
    tenant_id: 1,
    contexto: 'campanha',
    campanha_eleicao_id: null,
    tipo_evento_id: null,
    tipo_evento_nome: null,
    status_evento_id: null,
    status_evento_codigo: null,
    status_evento_nome: null,
    titulo: 'Reunião zonal',
    descricao: null,
    data_inicio: '2026-08-20T18:00:00Z',
    data_fim: null,
    local_nome: 'Sede',
    endereco_id: null,
    codigo_municipio_ibge: null,
    bairro_id: null,
    zona_eleitoral_id: null,
    territorio_id: null,
    territorio_nome: null,
    latitude: null,
    longitude: null,
    responsavel_pessoa_id: 1,
    responsavel_nome: 'Maria',
    motivo_cancelamento: null,
    cancelado_em: null,
    criado_em: '2026-08-01T10:00:00Z',
    atualizado_em: '2026-08-01T10:00:00Z',
    participantes: [],
    liderancas: [
      {
        lideranca_id: 5,
        pessoa_id: 10,
        nome: 'João Coordenador',
        tipo_lideranca: 'coordenador_territorial',
        papel: 'anfitrião',
      },
    ],
    convites: [],
    pautas: [],
    presenca: null,
    demandas: [],
    lembretes: [],
    insights: [],
  };
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MemoryRouter initialEntries={['/agenda/eventos/7']}>
      <QueryClientProvider client={client}>
        <Routes>
          <Route path="/agenda/eventos/:id" element={<EventDetailPage />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe('EventDetailPage nomenclatura de lideranças', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getEvent.mockResolvedValue(eventDetail());
    listTerritories.mockResolvedValue([]);
    listCatalog.mockResolvedValue([]);
  });

  it('mantém a aba Lideranças e a coluna Liderança no padrão do tenant', async () => {
    getConfiguration.mockResolvedValue({ preferencias: { nomenclatura_liderancas: 'liderancas' } });
    renderPage();

    expect(await screen.findByRole('tab', { name: /lideranças \(1\)/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: /lideranças \(1\)/i }));
    expect(await screen.findByRole('columnheader', { name: 'Liderança' })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /coordenadores/i })).not.toBeInTheDocument();
  });

  it('exibe Coordenadores e Coordenação quando o tenant usa essa nomenclatura', async () => {
    getConfiguration.mockResolvedValue({
      preferencias: { nomenclatura_liderancas: 'coordenadores' },
    });
    renderPage();

    expect(await screen.findByRole('tab', { name: /coordenadores \(1\)/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: /coordenadores \(1\)/i }));
    expect(await screen.findByRole('columnheader', { name: 'Coordenação' })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /lideranças/i })).not.toBeInTheDocument();
  });
});
