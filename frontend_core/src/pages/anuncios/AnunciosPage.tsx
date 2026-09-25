import {
  ArrowDownOutlined,
  ArrowUpOutlined,
  DeleteOutlined,
  EditOutlined,
  EnvironmentOutlined,
  EyeOutlined,
  PlusOutlined,
  RocketOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Statistic,
  Switch,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import type { TableProps } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  Tooltip as LeafletTooltip,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

import { BaseTable } from '@/components/data/BaseTable';
import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  createMaterial,
  createPlanning,
  createRoute,
  createTeam,
  deactivateMaterial,
  deactivateTeam,
  getDashboard,
  getRouteTemplate,
  listMaterials,
  listRoutes,
  listRouteTemplates,
  listTeams,
  updateMaterial,
  updateRoute,
  updateRouteTemplate,
  updateTeam,
} from '@/modules/anuncios/anuncios-service';
import type { TeamPayload } from '@/modules/anuncios/anuncios-service';
import type {
  DashboardData,
  MaterialRecord,
  PointStatus,
  RouteInput,
  RouteRecord,
  RouteTemplateDetail,
  RouteTemplateInput,
  RouteTemplateRecord,
  TeamRecord,
} from '@/modules/anuncios/types';
import { listarTerritorios } from '@/modules/territorios/territorios-service';
import { listUsers } from '@/modules/users/user-service';
import { normalizeApiError } from '@/services/api/api-error';
import { httpClient } from '@/services/api/http-client';

import styles from './AnunciosPage.module.css';

const statusColors: Record<PointStatus | RouteRecord['status'], string> = {
  PLANEJADA: 'default',
  LIBERADA: 'blue',
  EM_EXECUCAO: 'processing',
  CONCLUIDA: 'success',
  CANCELADA: 'error',
  PENDENTE: 'default',
  INSTALADO: 'cyan',
  RECOLHIDO: 'green',
  RECOLHIDO_PARCIALMENTE: 'orange',
  COM_EXTRAVIO: 'red',
  NAO_EXECUTADO: 'volcano',
};

const markerColors: Record<PointStatus, string> = {
  PENDENTE: '#8c8c8c',
  EM_EXECUCAO: '#1677ff',
  INSTALADO: '#13c2c2',
  RECOLHIDO: '#52c41a',
  RECOLHIDO_PARCIALMENTE: '#fa8c16',
  COM_EXTRAVIO: '#f5222d',
  NAO_EXECUTADO: '#fa541c',
};

type MaterialForm = { nome: string; descricao?: string; ativo?: boolean };
type RouteForm = RouteTemplateInput;

function handleError(error: unknown) {
  AppToast.error(normalizeApiError(error).message);
}

export function AnunciosPage() {
  const client = useQueryClient();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [materialModal, setMaterialModal] = useState<MaterialRecord | 'new' | null>(null);
  const [teamModal, setTeamModal] = useState<TeamRecord | 'new' | null>(null);
  const [routeModal, setRouteModal] = useState<RouteTemplateDetail | 'new' | null>(null);
  const [planningModal, setPlanningModal] = useState<RouteRecord | number | 'new' | null>(null);
  const [includeInactive, setIncludeInactive] = useState(false);
  const today = new Date().toISOString().slice(0, 10);
  const [filters, setFilters] = useState<Record<string, string | number | undefined>>({
    data_inicio: today,
    data_fim: today,
  });

  const materials = useQuery({
    queryKey: ['anuncios', 'materiais', includeInactive],
    queryFn: () => listMaterials(includeInactive),
  });
  const teams = useQuery({
    queryKey: ['anuncios', 'equipes', includeInactive],
    queryFn: () => listTeams(includeInactive),
  });
  const routes = useQuery({
    queryKey: ['anuncios', 'rotas', filters],
    queryFn: () => listRoutes(filters),
    refetchInterval: 30_000,
  });
  const routeTemplates = useQuery({
    queryKey: ['anuncios', 'route-templates', includeInactive],
    queryFn: () => listRouteTemplates(includeInactive),
  });
  const dashboard = useQuery({
    queryKey: ['anuncios', 'dashboard', filters],
    queryFn: () => getDashboard(filters),
    refetchInterval: 30_000,
  });
  const users = useQuery({
    queryKey: ['users', 'anuncios-options'],
    queryFn: () => listUsers({ status: 'ativo' }),
  });
  const territories = useQuery({
    queryKey: ['territorios', 'anuncios-options'],
    queryFn: () => listarTerritorios(false),
  });

  const refresh = async () => {
    await client.invalidateQueries({ queryKey: ['anuncios'] });
  };

  const releaseRoute = async (route: RouteRecord) => {
    try {
      await updateRoute(route.uuid_publico, { status: 'LIBERADA' });
      AppToast.success('Rota liberada para a equipe.');
      await refresh();
    } catch (error) {
      handleError(error);
    }
  };

  const cancelRoute = async (route: RouteRecord) => {
    try {
      await updateRoute(route.uuid_publico, { status: 'CANCELADA' });
      AppToast.success('Rota cancelada. O planejamento e o histórico foram preservados.');
      await refresh();
    } catch (error) {
      handleError(error);
    }
  };

  return (
    <div className={styles.root}>
      <PageHeader
        title="Anúncios"
        description="Planeje rotas, acompanhe instalações e controle o recolhimento dos materiais."
        breadcrumbs={[{ label: 'Início', to: '/dashboard' }, { label: 'Anúncios' }]}
        actions={
          <Space>
            <Typography.Text>Exibir inativos</Typography.Text>
            <Switch checked={includeInactive} onChange={setIncludeInactive} />
            <Button icon={<PlusOutlined />} onClick={() => setRouteModal('new')}>
              Novo modelo de rota
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setPlanningModal('new')}>
              Novo planejamento
            </Button>
          </Space>
        }
      />

      <Tabs
        activeKey={searchParams.get('aba') ?? 'dashboard'}
        onChange={(key) => {
          const next = new URLSearchParams(searchParams);
          if (key === 'dashboard') next.delete('aba');
          else next.set('aba', key);
          setSearchParams(next, { replace: true });
        }}
        items={[
          {
            key: 'dashboard',
            label: 'Operação',
            children: (
              <DashboardPanel
                data={dashboard.data}
                loading={dashboard.isPending}
                error={dashboard.error}
                filters={filters}
                onFilters={setFilters}
                teams={teams.data?.items ?? []}
                users={users.data?.items ?? []}
                materials={materials.data?.items ?? []}
                routes={routeTemplates.data?.items ?? []}
                territories={territories.data ?? []}
              />
            ),
          },
          {
            key: 'routes',
            label: `Planejamentos (${routes.data?.total ?? 0})`,
            children: (
              <RoutesTable
                routes={routes.data?.items ?? []}
                filters={filters}
                onFilters={setFilters}
                templates={routeTemplates.data?.items ?? []}
                teams={teams.data?.items ?? []}
                users={users.data?.items ?? []}
                loading={routes.isPending}
                error={routes.error}
                onView={(route) => navigate(`/anuncios/planejamentos/${route.uuid_publico}`)}
                onEdit={(route) => setPlanningModal(route)}
                onRelease={(route) => void releaseRoute(route)}
                onCancel={(route) => void cancelRoute(route)}
                onRetry={() => void routes.refetch()}
              />
            ),
          },
          {
            key: 'route-templates',
            label: `Modelos de rota (${routeTemplates.data?.total ?? 0})`,
            children: (
              <RouteTemplatesTable
                items={routeTemplates.data?.items ?? []}
                loading={routeTemplates.isPending}
                error={routeTemplates.error}
                onNew={() => setRouteModal('new')}
                onPlan={(item) => setPlanningModal(item.id)}
                onEdit={async (item) => {
                  try {
                    setRouteModal(await getRouteTemplate(item.uuid_publico));
                  } catch (error) {
                    handleError(error);
                  }
                }}
                onChanged={refresh}
              />
            ),
          },
          {
            key: 'materials',
            label: `Materiais (${materials.data?.total ?? 0})`,
            children: (
              <MaterialsTable
                items={materials.data?.items ?? []}
                loading={materials.isPending}
                error={materials.error}
                onNew={() => setMaterialModal('new')}
                onEdit={setMaterialModal}
                onChanged={refresh}
              />
            ),
          },
          {
            key: 'teams',
            label: `Equipes (${teams.data?.total ?? 0})`,
            children: (
              <TeamsTable
                items={teams.data?.items ?? []}
                loading={teams.isPending}
                error={teams.error}
                onNew={() => setTeamModal('new')}
                onEdit={setTeamModal}
                onChanged={refresh}
              />
            ),
          },
        ]}
      />

      <MaterialModal
        current={materialModal}
        onClose={() => setMaterialModal(null)}
        onChanged={refresh}
      />
      <TeamModal
        current={teamModal}
        users={users.data?.items ?? []}
        territories={territories.data ?? []}
        onClose={() => setTeamModal(null)}
        onChanged={refresh}
      />
      {routeModal !== null ? (
        <RouteModal
          current={routeModal}
          territories={territories.data ?? []}
          materials={materials.data?.items.filter((item) => item.ativo) ?? []}
          onClose={() => setRouteModal(null)}
          onChanged={refresh}
        />
      ) : null}
      <PlanningModal
        current={planningModal}
        templates={routeTemplates.data?.items.filter((item) => item.ativo) ?? []}
        teams={teams.data?.items.filter((item) => item.ativo) ?? []}
        users={users.data?.items ?? []}
        onClose={() => setPlanningModal(null)}
        onChanged={refresh}
      />
    </div>
  );
}

function DashboardPanel({
  data,
  loading,
  error,
  filters,
  onFilters,
  teams,
  users,
  materials,
  routes,
  territories,
}: {
  data?: DashboardData;
  loading: boolean;
  error: unknown;
  filters: Record<string, string | number | undefined>;
  onFilters: (value: Record<string, string | number | undefined>) => void;
  teams: TeamRecord[];
  users: Array<{ id: number; nome: string }>;
  materials: MaterialRecord[];
  routes: RouteTemplateRecord[];
  territories: Array<{ id: number; nome: string }>;
}) {
  const options = (items: Array<{ id: number; nome: string }>) =>
    items.map((item) => ({ value: item.id, label: item.nome }));
  const totals = data?.totais;
  const metrics = [
    ['Rotas programadas', totals?.rotas_programadas],
    ['Rotas iniciadas', totals?.rotas_iniciadas],
    ['Rotas concluídas', totals?.rotas_concluidas],
    ['Pontos planejados', totals?.pontos_planejados],
    ['Pontos executados', totals?.pontos_executados],
    ['Pontos pendentes', totals?.pontos_pendentes],
    ['Materiais instalados', totals?.materiais_instalados],
    ['Materiais recolhidos', totals?.materiais_recolhidos],
    ['Materiais extraviados', totals?.materiais_extraviados],
    ['Taxa de extravio', totals ? `${totals.taxa_extravio}%` : undefined],
  ] as const;
  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card title="Filtros operacionais">
        <div className={styles.filters}>
          <Input
            type="date"
            value={String(filters.data_inicio ?? '')}
            onChange={(event) => onFilters({ ...filters, data_inicio: event.target.value })}
          />
          <Input
            type="date"
            value={String(filters.data_fim ?? '')}
            onChange={(event) => onFilters({ ...filters, data_fim: event.target.value })}
          />
          <Select
            allowClear
            placeholder="Equipe"
            value={filters.equipe_id}
            options={options(teams)}
            onChange={(value) => onFilters({ ...filters, equipe_id: value })}
          />
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="Usuário"
            value={filters.usuario_id}
            options={options(users)}
            onChange={(value) => onFilters({ ...filters, usuario_id: value })}
          />
          <Select
            allowClear
            placeholder="Material"
            value={filters.material_id}
            options={options(materials)}
            onChange={(value) => onFilters({ ...filters, material_id: value })}
          />
          <Select
            allowClear
            placeholder="Rota"
            value={filters.rota_id}
            options={options(routes)}
            onChange={(value) => onFilters({ ...filters, rota_id: value })}
          />
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="Território"
            value={filters.territorio_id}
            options={options(territories)}
            onChange={(value) => onFilters({ ...filters, territorio_id: value })}
          />
          <Select
            allowClear
            placeholder="Status"
            value={filters.status}
            options={['PLANEJADA', 'LIBERADA', 'EM_EXECUCAO', 'CONCLUIDA', 'CANCELADA'].map(
              (value) => ({ value, label: value.replaceAll('_', ' ') }),
            )}
            onChange={(value) => onFilters({ ...filters, status: value })}
          />
        </div>
      </Card>
      {error ? <Alert type="error" showIcon message={normalizeApiError(error).message} /> : null}
      <div className={styles.metrics}>
        {metrics.map(([label, value]) => (
          <Card key={label} loading={loading}>
            <Statistic title={label} value={value ?? 0} />
          </Card>
        ))}
      </div>
      <Card title="Mapa operacional" extra="Atualização automática a cada 30 segundos">
        <OperationalMap points={data?.pontos ?? []} />
      </Card>
      <Card title="Materiais por tipo">
        <BaseTable
          rowKey="chave"
          pagination={false}
          dataSource={data?.por_material ?? []}
          columns={[
            { title: 'Material', dataIndex: 'nome' },
            { title: 'Instalado', dataIndex: 'instalado' },
            { title: 'Recolhido', dataIndex: 'recolhido' },
            { title: 'Extraviado', dataIndex: 'extraviado' },
          ]}
        />
      </Card>
    </Space>
  );
}

function OperationalMap({ points }: { points: DashboardData['pontos'] }) {
  const mapped = points.filter(
    (point) =>
      (point.latitude_execucao !== null && point.longitude_execucao !== null) ||
      (point.latitude_planejada !== null && point.longitude_planejada !== null),
  );
  if (!mapped.length) return <Empty description="Nenhum ponto com coordenadas no período." />;
  const center: [number, number] = [
    Number(mapped[0].latitude_execucao ?? mapped[0].latitude_planejada),
    Number(mapped[0].longitude_execucao ?? mapped[0].longitude_planejada),
  ];
  return (
    <MapContainer center={center} zoom={12} className={styles.map}>
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {mapped.map((point) => (
        <CircleMarker
          key={point.uuid_publico}
          center={[
            Number(point.latitude_execucao ?? point.latitude_planejada),
            Number(point.longitude_execucao ?? point.longitude_planejada),
          ]}
          radius={10}
          pathOptions={{ color: markerColors[point.status], fillOpacity: 0.85 }}
        >
          <Popup>
            <strong>{point.descricao_local}</strong>
            <br />
            Rota: {point.rota_nome}
            <br />
            Equipe: {point.equipe_nome ?? 'Atribuição individual'}
            <br />
            Responsável: {point.usuario_nome ?? 'Equipe'}
            <br />
            Executor: {point.executor_nome ?? 'Ainda não executado'}
            {point.executado_em ? (
              <>
                <br />
                Horário: {new Date(point.executado_em).toLocaleString('pt-BR')}
              </>
            ) : null}
            <br />
            Materiais: {point.materiais ?? 'Não informados'}
            <br />
            Instalado: {point.instalado}
            <br />
            Recolhido: {point.recolhido}
            <br />
            Extraviado: {point.extraviado}
            <br />
            Status: {point.status.replaceAll('_', ' ')}
            {point.latitude_planejada !== null ? (
              <>
                <br />
                Planejado: {point.latitude_planejada}, {point.longitude_planejada}
              </>
            ) : null}
            {point.latitude_execucao !== null ? (
              <>
                <br />
                Registrado: {point.latitude_execucao}, {point.longitude_execucao}
              </>
            ) : null}
            {point.anexo_id ? (
              <AuthenticatedImage
                url={`/api/v1/arquivos/anexos/${point.anexo_id}/preview`}
                alt={`Foto de ${point.descricao_local}`}
              />
            ) : null}
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}

function RoutesTable({
  routes,
  filters,
  onFilters,
  templates,
  teams,
  users,
  loading,
  error,
  onView,
  onEdit,
  onRelease,
  onCancel,
  onRetry,
}: {
  routes: RouteRecord[];
  filters: Record<string, string | number | undefined>;
  onFilters: (value: Record<string, string | number | undefined>) => void;
  templates: RouteTemplateRecord[];
  teams: TeamRecord[];
  users: Array<{ id: number; nome: string }>;
  loading: boolean;
  error: unknown;
  onView: (route: RouteRecord) => void;
  onEdit: (route: RouteRecord) => void;
  onRelease: (route: RouteRecord) => void;
  onCancel: (route: RouteRecord) => void;
  onRetry: () => void;
}) {
  const columns: TableProps<RouteRecord>['columns'] = [
    { title: 'Rota', dataIndex: 'nome' },
    {
      title: 'Data',
      dataIndex: 'data_execucao',
      render: (value: string) => dayjs(value).format('DD/MM/YYYY'),
    },
    {
      title: 'Atribuição',
      render: (_, item) => item.usuario_responsavel_nome ?? item.equipe_nome ?? '—',
    },
    {
      title: 'Progresso',
      render: (_, item) => `${item.pontos_concluidos}/${item.total_pontos} pontos`,
    },
    {
      title: 'Status',
      render: (_, item) => <Tag color={statusColors[item.status]}>{item.status}</Tag>,
    },
    {
      title: 'Ações',
      render: (_, item) => (
        <Space>
          <Button
            icon={<EyeOutlined />}
            aria-label="Visualizar rota"
            onClick={() => onView(item)}
          />
          {['PLANEJADA', 'LIBERADA'].includes(item.status) ? (
            <Button icon={<EditOutlined />} aria-label="Editar rota" onClick={() => onEdit(item)} />
          ) : null}
          {item.status === 'PLANEJADA' ? (
            <Button type="primary" icon={<RocketOutlined />} onClick={() => onRelease(item)}>
              Liberar
            </Button>
          ) : null}
          {['PLANEJADA', 'LIBERADA'].includes(item.status) ? (
            <Popconfirm
              title="Cancelar esta rota?"
              description="O planejamento será preservado no histórico."
              onConfirm={() => onCancel(item)}
            >
              <Button danger icon={<StopOutlined />}>
                Cancelar
              </Button>
            </Popconfirm>
          ) : null}
        </Space>
      ),
    },
  ];
  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card title="Filtros dos planejamentos">
        <div className={styles.filters}>
          <Input
            type="date"
            value={String(filters.data_inicio ?? '')}
            onChange={(event) => onFilters({ ...filters, data_inicio: event.target.value })}
          />
          <Input
            type="date"
            value={String(filters.data_fim ?? '')}
            onChange={(event) => onFilters({ ...filters, data_fim: event.target.value })}
          />
          <Select
            allowClear
            placeholder="Modelo de rota"
            value={filters.rota_id}
            options={templates.map((item) => ({ value: item.id, label: item.nome }))}
            onChange={(value) => onFilters({ ...filters, rota_id: value })}
          />
          <Select
            allowClear
            placeholder="Equipe"
            value={filters.equipe_id}
            options={teams.map((item) => ({ value: item.id, label: item.nome }))}
            onChange={(value) => onFilters({ ...filters, equipe_id: value })}
          />
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="Usuário"
            value={filters.usuario_id}
            options={users.map((item) => ({ value: item.id, label: item.nome }))}
            onChange={(value) => onFilters({ ...filters, usuario_id: value })}
          />
          <Select
            allowClear
            placeholder="Status"
            value={filters.status}
            options={['PLANEJADA', 'LIBERADA', 'EM_EXECUCAO', 'CONCLUIDA', 'CANCELADA'].map(
              (value) => ({ value, label: value.replaceAll('_', ' ') }),
            )}
            onChange={(value) => onFilters({ ...filters, status: value })}
          />
        </div>
      </Card>
      <BaseTable
        rowKey="uuid_publico"
        loading={loading}
        error={error ? normalizeApiError(error).message : null}
        onRetry={onRetry}
        dataSource={routes}
        columns={columns}
      />
    </Space>
  );
}

function RouteTemplatesTable({
  items,
  loading,
  error,
  onNew,
  onPlan,
  onEdit,
  onChanged,
}: {
  items: RouteTemplateRecord[];
  loading: boolean;
  error: unknown;
  onNew: () => void;
  onPlan: (item: RouteTemplateRecord) => void;
  onEdit: (item: RouteTemplateRecord) => void;
  onChanged: () => Promise<void>;
}) {
  return (
    <Card
      title="Modelos reutilizáveis de rota"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={onNew}>
          Novo modelo
        </Button>
      }
    >
      <Alert
        type="info"
        showIcon
        message="Os modelos guardam território, pontos, ordem e materiais. A operação é criada em Planejamentos."
        style={{ marginBottom: 16 }}
      />
      <BaseTable
        rowKey="uuid_publico"
        loading={loading}
        error={error ? normalizeApiError(error).message : null}
        dataSource={items}
        columns={[
          { title: 'Nome', dataIndex: 'nome' },
          { title: 'Território', dataIndex: 'territorio_nome' },
          { title: 'Pontos', dataIndex: 'total_pontos' },
          {
            title: 'Status',
            render: (_, item) => (
              <Tag color={item.ativo ? 'green' : 'default'}>{item.ativo ? 'ATIVO' : 'INATIVO'}</Tag>
            ),
          },
          {
            title: 'Ações',
            render: (_, item) => (
              <Space>
                {item.ativo ? (
                  <Button type="primary" icon={<RocketOutlined />} onClick={() => onPlan(item)}>
                    Planejar execução
                  </Button>
                ) : null}
                <Button icon={<EditOutlined />} onClick={() => onEdit(item)}>
                  Editar
                </Button>
                {item.ativo ? (
                  <Popconfirm
                    title="Inativar este modelo?"
                    description="Planejamentos já criados manterão seus snapshots."
                    onConfirm={async () => {
                      try {
                        await updateRouteTemplate(item.uuid_publico, { ativo: false });
                        AppToast.success('Modelo inativado.');
                        await onChanged();
                      } catch (failure) {
                        handleError(failure);
                      }
                    }}
                  >
                    <Button danger icon={<StopOutlined />}>
                      Inativar
                    </Button>
                  </Popconfirm>
                ) : null}
              </Space>
            ),
          },
        ]}
      />
    </Card>
  );
}

function MaterialsTable({
  items,
  loading,
  error,
  onNew,
  onEdit,
  onChanged,
}: {
  items: MaterialRecord[];
  loading: boolean;
  error: unknown;
  onNew: () => void;
  onEdit: (item: MaterialRecord) => void;
  onChanged: () => Promise<void>;
}) {
  const remove = async (id: number) => {
    try {
      await deactivateMaterial(id);
      AppToast.success('Material inativado. O histórico foi preservado.');
      await onChanged();
    } catch (failure) {
      handleError(failure);
    }
  };
  return (
    <Card
      title="Tipos de material"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={onNew}>
          Novo material
        </Button>
      }
    >
      <BaseTable
        rowKey="id"
        loading={loading}
        error={error ? normalizeApiError(error).message : null}
        dataSource={items}
        columns={[
          { title: 'Nome', dataIndex: 'nome' },
          { title: 'Descrição', dataIndex: 'descricao' },
          {
            title: 'Status',
            render: (_, item) => (
              <Tag color={item.ativo ? 'green' : 'default'}>{item.ativo ? 'Ativo' : 'Inativo'}</Tag>
            ),
          },
          {
            title: 'Ações',
            render: (_, item) => (
              <Space>
                <Button icon={<EditOutlined />} onClick={() => onEdit(item)} />
                {item.ativo ? (
                  <Popconfirm
                    title="Inativar este material?"
                    onConfirm={() => void remove(item.id)}
                  >
                    <Button danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                ) : null}
              </Space>
            ),
          },
        ]}
      />
    </Card>
  );
}

function TeamsTable({
  items,
  loading,
  error,
  onNew,
  onEdit,
  onChanged,
}: {
  items: TeamRecord[];
  loading: boolean;
  error: unknown;
  onNew: () => void;
  onEdit: (item: TeamRecord) => void;
  onChanged: () => Promise<void>;
}) {
  const remove = async (id: number) => {
    try {
      await deactivateTeam(id);
      AppToast.success('Equipe inativada.');
      await onChanged();
    } catch (failure) {
      handleError(failure);
    }
  };
  return (
    <Card
      title="Equipes de campo"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={onNew}>
          Nova equipe
        </Button>
      }
    >
      <BaseTable
        rowKey="id"
        loading={loading}
        error={error ? normalizeApiError(error).message : null}
        dataSource={items}
        columns={[
          { title: 'Equipe', dataIndex: 'nome' },
          {
            title: 'Membros',
            render: (_, item) =>
              item.membros.map((member) => member.nome).join(', ') || 'Sem membros',
          },
          {
            title: 'Status',
            render: (_, item) => (
              <Tag color={item.ativo ? 'green' : 'default'}>{item.ativo ? 'Ativa' : 'Inativa'}</Tag>
            ),
          },
          {
            title: 'Ações',
            render: (_, item) => (
              <Space>
                <Button icon={<EditOutlined />} onClick={() => onEdit(item)} />
                {item.ativo ? (
                  <Popconfirm title="Inativar esta equipe?" onConfirm={() => void remove(item.id)}>
                    <Button danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                ) : null}
              </Space>
            ),
          },
        ]}
      />
    </Card>
  );
}

function MaterialModal({
  current,
  onClose,
  onChanged,
}: {
  current: MaterialRecord | 'new' | null;
  onClose: () => void;
  onChanged: () => Promise<void>;
}) {
  const [form] = Form.useForm<MaterialForm>();
  useEffect(() => {
    if (current && current !== 'new')
      form.setFieldsValue({
        nome: current.nome,
        descricao: current.descricao ?? undefined,
        ativo: current.ativo,
      });
    else form.resetFields();
  }, [current, form]);
  const mutation = useMutation({
    mutationFn: async (values: MaterialForm) =>
      current === 'new'
        ? createMaterial(values)
        : updateMaterial((current as MaterialRecord).id, values),
    onSuccess: async () => {
      AppToast.success('Material salvo.');
      onClose();
      await onChanged();
    },
    onError: handleError,
  });
  return (
    <Modal
      open={current !== null}
      title={current === 'new' ? 'Novo material' : 'Editar material'}
      okText="Salvar"
      confirmLoading={mutation.isPending}
      onCancel={onClose}
      onOk={() => void form.validateFields().then((values) => mutation.mutate(values))}
      destroyOnHidden
    >
      <Form form={form} layout="vertical">
        <Form.Item name="nome" label="Nome" rules={[{ required: true, min: 2 }]}>
          <Input />
        </Form.Item>
        <Form.Item name="descricao" label="Descrição">
          <Input.TextArea rows={3} />
        </Form.Item>
        {current !== 'new' ? (
          <Form.Item name="ativo" label="Ativo" valuePropName="checked">
            <Switch />
          </Form.Item>
        ) : null}
      </Form>
    </Modal>
  );
}

function TeamModal({
  current,
  users,
  territories,
  onClose,
  onChanged,
}: {
  current: TeamRecord | 'new' | null;
  users: Array<{ id: number; nome: string; email: string; pessoa_id?: number | null }>;
  territories: Array<{ id: number; nome: string }>;
  onClose: () => void;
  onChanged: () => Promise<void>;
}) {
  const [form] = Form.useForm<TeamPayload>();
  useEffect(() => {
    if (current && current !== 'new')
      form.setFieldsValue({
        nome: current.nome,
        descricao: current.descricao ?? undefined,
        territorio_id: current.territorio_id ?? undefined,
        usuario_ids: current.membros.map((member) => member.usuario_id),
        ativo: current.ativo,
      });
    else {
      form.resetFields();
      form.setFieldValue('usuario_ids', []);
    }
  }, [current, form]);
  const mutation = useMutation({
    mutationFn: async (values: TeamPayload) =>
      current === 'new' ? createTeam(values) : updateTeam((current as TeamRecord).id, values),
    onSuccess: async () => {
      AppToast.success('Equipe salva.');
      onClose();
      await onChanged();
    },
    onError: handleError,
  });
  return (
    <Modal
      open={current !== null}
      title={current === 'new' ? 'Nova equipe' : 'Editar equipe'}
      width={680}
      okText="Salvar"
      confirmLoading={mutation.isPending}
      onCancel={onClose}
      onOk={() => void form.validateFields().then((values) => mutation.mutate(values))}
      destroyOnHidden
    >
      <Form form={form} layout="vertical">
        <Form.Item name="nome" label="Nome" rules={[{ required: true, min: 2 }]}>
          <Input />
        </Form.Item>
        <Form.Item name="descricao" label="Descrição">
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item name="territorio_id" label="Território de referência">
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            options={territories.map((item) => ({ value: item.id, label: item.nome }))}
          />
        </Form.Item>
        <Form.Item
          name="usuario_ids"
          label="Membros"
          rules={[{ required: true, message: 'Selecione ao menos um membro.' }]}
        >
          <Select
            mode="multiple"
            showSearch
            optionFilterProp="label"
            options={users
              .filter((item) => item.pessoa_id)
              .map((item) => ({ value: item.id, label: `${item.nome} · ${item.email}` }))}
          />
        </Form.Item>
        {current !== 'new' ? (
          <Form.Item name="ativo" label="Ativa" valuePropName="checked">
            <Switch />
          </Form.Item>
        ) : null}
      </Form>
    </Modal>
  );
}

function PlanningModal({
  current,
  templates,
  teams,
  users,
  onClose,
  onChanged,
}: {
  current: RouteRecord | number | 'new' | null;
  templates: RouteTemplateRecord[];
  teams: TeamRecord[];
  users: Array<{ id: number; nome: string }>;
  onClose: () => void;
  onChanged: () => Promise<void>;
}) {
  const [form] = Form.useForm<RouteInput>();
  useEffect(() => {
    if (current && current !== 'new' && typeof current !== 'number') {
      form.setFieldsValue({
        rota_id: current.rota_id,
        data_execucao: current.data_execucao,
        equipe_id: current.equipe_id ?? undefined,
        usuario_responsavel_id: current.usuario_responsavel_id ?? undefined,
        observacao: current.observacao ?? undefined,
      });
    } else {
      form.resetFields();
      form.setFieldsValue({
        data_execucao: new Date().toISOString().slice(0, 10),
        rota_id: typeof current === 'number' ? current : undefined,
      });
    }
  }, [current, form]);
  const mutation = useMutation({
    mutationFn: (values: RouteInput) =>
      current === 'new' || typeof current === 'number'
        ? createPlanning(values)
        : updateRoute((current as RouteRecord).uuid_publico, values),
    onSuccess: async () => {
      AppToast.success('Planejamento salvo. O snapshot da rota foi preservado.');
      onClose();
      await onChanged();
    },
    onError: handleError,
  });
  return (
    <Modal
      open={current !== null}
      title={
        current === 'new' || typeof current === 'number'
          ? 'Novo planejamento'
          : 'Editar planejamento'
      }
      okText="Salvar planejamento"
      confirmLoading={mutation.isPending}
      onCancel={onClose}
      onOk={() => void form.validateFields().then((values) => mutation.mutate(values))}
      destroyOnHidden
    >
      <Form form={form} layout="vertical">
        <Form.Item name="rota_id" label="Modelo de rota" rules={[{ required: true }]}>
          <Select
            disabled={current !== 'new' && typeof current !== 'number'}
            showSearch
            optionFilterProp="label"
            options={templates.map((item) => ({
              value: item.id,
              label: `${item.nome} · ${item.total_pontos} pontos`,
            }))}
          />
        </Form.Item>
        <Form.Item name="data_execucao" label="Data de execução" rules={[{ required: true }]}>
          <Input type="date" />
        </Form.Item>
        <Form.Item name="equipe_id" label="Equipe">
          <Select
            allowClear
            options={teams.map((item) => ({ value: item.id, label: item.nome }))}
          />
        </Form.Item>
        <Form.Item name="usuario_responsavel_id" label="Responsável individual">
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            options={users.map((item) => ({ value: item.id, label: item.nome }))}
          />
        </Form.Item>
        <Form.Item name="observacao" label="Observações operacionais">
          <Input.TextArea rows={3} />
        </Form.Item>
        <Alert
          type="info"
          showIcon
          message="Informe uma equipe, um responsável individual ou ambos. O modelo será copiado como snapshot deste planejamento."
        />
      </Form>
    </Modal>
  );
}

function RouteModal({
  current,
  territories,
  materials,
  onClose,
  onChanged,
}: {
  current: RouteTemplateDetail | 'new';
  territories: Array<{ id: number; nome: string }>;
  materials: MaterialRecord[];
  onClose: () => void;
  onChanged: () => Promise<void>;
}) {
  const [form] = Form.useForm<RouteForm>();
  const [selectedPoint, setSelectedPoint] = useState<number | null>(
    current !== 'new' && current.pontos.length ? 0 : null,
  );
  const [repositioningPoint, setRepositioningPoint] = useState<number | null>(null);
  const points = Form.useWatch('pontos', form) ?? [];
  useEffect(() => {
    if (current !== 'new') {
      form.setFieldsValue({
        nome: current.nome,
        descricao: current.descricao ?? undefined,
        territorio_id: current.territorio_id ?? undefined,
        ativo: current.ativo,
        pontos: current.pontos.map((point) => ({
          ordem: point.ordem,
          descricao_local: point.descricao_local,
          endereco: point.endereco ?? undefined,
          latitude_planejada:
            point.latitude_planejada !== null ? Number(point.latitude_planejada) : undefined,
          longitude_planejada:
            point.longitude_planejada !== null ? Number(point.longitude_planejada) : undefined,
          observacao: point.observacao ?? undefined,
          materiais: point.materiais.map((material) => ({
            material_id: material.material_id,
            quantidade_planejada: material.quantidade_planejada,
          })),
        })),
      });
    } else {
      form.resetFields();
      form.setFieldsValue({ pontos: [] });
    }
  }, [current, form]);
  const mutation = useMutation({
    mutationFn: async (values: RouteForm) => {
      const payload = {
        ...values,
        territorio_id: values.territorio_id || undefined,
        pontos: values.pontos.map((point, index) => ({ ...point, ordem: index + 1 })),
      };
      return current === 'new'
        ? createRoute(payload)
        : updateRouteTemplate((current as RouteTemplateDetail).uuid_publico, payload);
    },
    onSuccess: async () => {
      AppToast.success('Rota salva.');
      onClose();
      await onChanged();
    },
    onError: handleError,
  });
  return (
    <Modal
      open
      title={current === 'new' ? 'Novo modelo de rota' : 'Editar modelo de rota'}
      width={1180}
      okText="Salvar modelo"
      confirmLoading={mutation.isPending}
      onCancel={onClose}
      onOk={() => void form.validateFields().then((values) => mutation.mutate(values))}
      destroyOnHidden
    >
      <Form form={form} layout="vertical">
        <div className={styles.pointGrid}>
          <Form.Item name="nome" label="Nome da rota" rules={[{ required: true, min: 2 }]}>
            <Input />
          </Form.Item>
          <Form.Item name="territorio_id" label="Território de referência">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              options={territories.map((item) => ({ value: item.id, label: item.nome }))}
            />
          </Form.Item>
          <Form.Item name="descricao" label="Descrição">
            <Input.TextArea rows={2} />
          </Form.Item>
          {current !== 'new' ? (
            <Form.Item name="ativo" label="Modelo ativo" valuePropName="checked">
              <Switch />
            </Form.Item>
          ) : null}
        </div>
        <Alert
          type="info"
          showIcon
          message="Este modelo é reutilizável. Data, equipe, responsável e status são definidos separadamente em cada planejamento."
        />
        <Typography.Title level={4}>Pontos da rota</Typography.Title>
        <Form.List
          name="pontos"
          rules={[
            {
              validator: async (_, value: RouteForm['pontos'] | undefined) => {
                if (!value?.length) {
                  throw new Error('Adicione pelo menos um ponto clicando no mapa.');
                }
              },
            },
          ]}
        >
          {(fields, { add, remove, move }, { errors }) => {
            const trackMove = (tracked: number | null, from: number, to: number) => {
              if (tracked === null) return null;
              if (tracked === from) return to;
              if (from < to && tracked > from && tracked <= to) return tracked - 1;
              if (from > to && tracked >= to && tracked < from) return tracked + 1;
              return tracked;
            };
            const movePoint = (from: number, to: number) => {
              move(from, to);
              setSelectedPoint((value) => trackMove(value, from, to));
              setRepositioningPoint((value) => trackMove(value, from, to));
            };
            const removePoint = (index: number) => {
              remove(index);
              setSelectedPoint((value) => {
                if (value === null) return null;
                if (value === index)
                  return fields.length > 1 ? Math.min(index, fields.length - 2) : null;
                return value > index ? value - 1 : value;
              });
              setRepositioningPoint((value) => {
                if (value === index) return null;
                return value !== null && value > index ? value - 1 : value;
              });
            };
            const pickLocation = (latitude: number, longitude: number) => {
              if (repositioningPoint !== null) {
                form.setFieldValue(['pontos', repositioningPoint, 'latitude_planejada'], latitude);
                form.setFieldValue(
                  ['pontos', repositioningPoint, 'longitude_planejada'],
                  longitude,
                );
                setSelectedPoint(repositioningPoint);
                setRepositioningPoint(null);
                return;
              }
              const index = fields.length;
              add({
                ordem: index + 1,
                descricao_local: `Ponto ${index + 1}`,
                latitude_planejada: latitude,
                longitude_planejada: longitude,
                materiais: [
                  {
                    material_id: undefined as unknown as number,
                    quantidade_planejada: 1,
                  },
                ],
              });
              setSelectedPoint(index);
            };
            return (
              <>
                <div className={styles.routeBuilder}>
                  <section className={styles.routeMapPanel}>
                    <div className={styles.routeMapHeading}>
                      <div>
                        <Typography.Text strong>Defina a rota no mapa</Typography.Text>
                        <Typography.Paragraph type="secondary" className={styles.routeMapHint}>
                          Clique em uma localização para adicionar um ponto. Todos os marcadores
                          permanecerão visíveis até o salvamento.
                        </Typography.Paragraph>
                      </div>
                      <Tag color="blue">
                        {fields.length} {fields.length === 1 ? 'ponto' : 'pontos'}
                      </Tag>
                    </div>
                    {repositioningPoint !== null ? (
                      <Alert
                        className={styles.repositionAlert}
                        type="warning"
                        showIcon
                        message={`Clique no novo local do Ponto ${repositioningPoint + 1}.`}
                        action={
                          <Button size="small" onClick={() => setRepositioningPoint(null)}>
                            Cancelar
                          </Button>
                        }
                      />
                    ) : null}
                    <RoutePointsMap
                      points={points}
                      selectedPoint={selectedPoint}
                      repositioningPoint={repositioningPoint}
                      onPick={pickLocation}
                      onSelect={setSelectedPoint}
                    />
                  </section>

                  <aside className={styles.routePointListPanel}>
                    <Typography.Text strong>Pontos adicionados</Typography.Text>
                    <Typography.Paragraph type="secondary" className={styles.routePointListHint}>
                      A sequência abaixo será a ordem inicial da rota.
                    </Typography.Paragraph>
                    <div className={styles.routePointList}>
                      {fields.length ? (
                        fields.map((field, index) => {
                          const point = points[field.name];
                          const hasCoordinates =
                            point?.latitude_planejada !== undefined &&
                            point?.longitude_planejada !== undefined;
                          return (
                            <div
                              className={`${styles.routePointItem} ${
                                selectedPoint === index ? styles.routePointItemSelected : ''
                              }`}
                              key={field.key}
                            >
                              <button
                                className={styles.routePointSummary}
                                type="button"
                                onClick={() => setSelectedPoint(index)}
                              >
                                <span className={styles.routePointOrder}>{index + 1}</span>
                                <span className={styles.routePointText}>
                                  <strong>{point?.descricao_local || `Ponto ${index + 1}`}</strong>
                                  <small>
                                    {hasCoordinates
                                      ? `${Number(point.latitude_planejada).toFixed(7)}, ${Number(
                                          point.longitude_planejada,
                                        ).toFixed(7)}`
                                      : 'Localização não definida'}
                                  </small>
                                </span>
                              </button>
                              <div className={styles.routePointActions}>
                                <Button
                                  size="small"
                                  title="Mover para cima"
                                  aria-label={`Mover Ponto ${index + 1} para cima`}
                                  disabled={index === 0}
                                  icon={<ArrowUpOutlined />}
                                  onClick={() => movePoint(index, index - 1)}
                                />
                                <Button
                                  size="small"
                                  title="Mover para baixo"
                                  aria-label={`Mover Ponto ${index + 1} para baixo`}
                                  disabled={index === fields.length - 1}
                                  icon={<ArrowDownOutlined />}
                                  onClick={() => movePoint(index, index + 1)}
                                />
                                <Button
                                  size="small"
                                  title="Reposicionar no mapa"
                                  aria-label={`Reposicionar Ponto ${index + 1}`}
                                  type={repositioningPoint === index ? 'primary' : 'default'}
                                  icon={<EnvironmentOutlined />}
                                  onClick={() => {
                                    setSelectedPoint(index);
                                    setRepositioningPoint(index);
                                  }}
                                />
                                <Button
                                  size="small"
                                  danger
                                  title="Remover ponto"
                                  aria-label={`Remover Ponto ${index + 1}`}
                                  icon={<DeleteOutlined />}
                                  onClick={() => removePoint(index)}
                                />
                              </div>
                            </div>
                          );
                        })
                      ) : (
                        <Empty
                          image={Empty.PRESENTED_IMAGE_SIMPLE}
                          description="Clique no mapa para adicionar o primeiro ponto."
                        />
                      )}
                    </div>
                  </aside>
                </div>
                <Form.ErrorList errors={errors} />

                {fields.map((field, index) => (
                  <div key={field.key} hidden={selectedPoint !== index}>
                    <PointEditor fieldName={field.name} index={index} materials={materials} />
                  </div>
                ))}
              </>
            );
          }}
        </Form.List>
      </Form>
    </Modal>
  );
}

function PointEditor({
  fieldName,
  index,
  materials,
}: {
  fieldName: number;
  index: number;
  materials: MaterialRecord[];
}) {
  return (
    <Card className={styles.pointCard} title={`Configuração do Ponto ${index + 1}`}>
      <div className={styles.pointGrid}>
        <Form.Item
          name={[fieldName, 'descricao_local']}
          label="Local"
          rules={[{ required: true, min: 2 }]}
        >
          <Input placeholder="Praça, avenida ou referência" />
        </Form.Item>
        <Form.Item name={[fieldName, 'endereco']} label="Endereço">
          <Input />
        </Form.Item>
        <Form.Item name={[fieldName, 'latitude_planejada']} label="Latitude">
          <InputNumber style={{ width: '100%' }} precision={7} min={-90} max={90} />
        </Form.Item>
        <Form.Item name={[fieldName, 'longitude_planejada']} label="Longitude">
          <InputNumber style={{ width: '100%' }} precision={7} min={-180} max={180} />
        </Form.Item>
        <Form.Item className={styles.full} name={[fieldName, 'observacao']} label="Observação">
          <Input.TextArea rows={2} />
        </Form.Item>
      </div>
      <Typography.Title level={5}>Materiais planejados</Typography.Title>
      <Form.List name={[fieldName, 'materiais']}>
        {(materialFields, { add, remove }) => (
          <>
            {materialFields.map((materialField) => (
              <div className={styles.materialRow} key={materialField.key}>
                <Form.Item
                  name={[materialField.name, 'material_id']}
                  rules={[{ required: true, message: 'Selecione o material.' }]}
                >
                  <Select
                    placeholder="Material"
                    options={materials.map((item) => ({ value: item.id, label: item.nome }))}
                  />
                </Form.Item>
                <Form.Item
                  name={[materialField.name, 'quantidade_planejada']}
                  rules={[{ required: true }]}
                >
                  <InputNumber
                    min={1}
                    precision={0}
                    style={{ width: '100%' }}
                    placeholder="Quantidade"
                  />
                </Form.Item>
                <Button
                  danger
                  icon={<DeleteOutlined />}
                  disabled={materialFields.length === 1}
                  onClick={() => remove(materialField.name)}
                />
              </div>
            ))}
            <Button type="dashed" onClick={() => add({ quantidade_planejada: 1 })}>
              Adicionar material
            </Button>
          </>
        )}
      </Form.List>
    </Card>
  );
}

function RoutePointsMap({
  points,
  selectedPoint,
  repositioningPoint,
  onPick,
  onSelect,
}: {
  points: RouteForm['pontos'];
  selectedPoint: number | null;
  repositioningPoint: number | null;
  onPick: (lat: number, lng: number) => void;
  onSelect: (index: number) => void;
}) {
  const coordinates = points.flatMap((point, index) => {
    if (
      point.latitude_planejada === undefined ||
      point.longitude_planejada === undefined ||
      !Number.isFinite(Number(point.latitude_planejada)) ||
      !Number.isFinite(Number(point.longitude_planejada))
    ) {
      return [];
    }
    return [
      {
        index,
        latitude: Number(point.latitude_planejada),
        longitude: Number(point.longitude_planejada),
        description: point.descricao_local || `Ponto ${index + 1}`,
      },
    ];
  });
  const center: [number, number] = coordinates.length
    ? [coordinates[0].latitude, coordinates[0].longitude]
    : [-16.6869, -49.2648];
  return (
    <MapContainer
      center={center}
      zoom={coordinates.length ? 15 : 11}
      className={styles.routePickerMap}
    >
      <TileLayer
        attribution="&copy; OpenStreetMap contributors"
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <MapClick onPick={onPick} />
      <FitRoutePoints coordinates={coordinates} />
      {coordinates.map((point) => {
        const selected = selectedPoint === point.index;
        const repositioning = repositioningPoint === point.index;
        return (
          <CircleMarker
            key={point.index}
            center={[point.latitude, point.longitude]}
            radius={selected ? 13 : 11}
            bubblingMouseEvents={false}
            eventHandlers={{ click: () => onSelect(point.index) }}
            pathOptions={{
              color: repositioning ? '#fa8c16' : selected ? '#0958d9' : '#1677ff',
              fillColor: repositioning ? '#fa8c16' : '#1677ff',
              fillOpacity: 0.9,
              weight: selected ? 4 : 2,
            }}
          >
            <LeafletTooltip permanent direction="center" className={styles.routePointNumberTooltip}>
              {point.index + 1}
            </LeafletTooltip>
            <Popup>
              <strong>Ponto {point.index + 1}</strong>
              <br />
              {point.description}
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}

function FitRoutePoints({
  coordinates,
}: {
  coordinates: Array<{ latitude: number; longitude: number }>;
}) {
  const map = useMap();
  useEffect(() => {
    map.invalidateSize();
    if (coordinates.length === 1) {
      map.setView([coordinates[0].latitude, coordinates[0].longitude], 16);
    } else if (coordinates.length > 1) {
      map.fitBounds(
        coordinates.map((point) => [point.latitude, point.longitude] as [number, number]),
        { padding: [30, 30], maxZoom: 16 },
      );
    }
  }, [coordinates, map]);
  return null;
}

function MapClick({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click: ({ latlng }) => onPick(Number(latlng.lat.toFixed(7)), Number(latlng.lng.toFixed(7))),
  });
  return null;
}

function AuthenticatedImage({ url, alt }: { url: string; alt: string }) {
  const [source, setSource] = useState<string>();
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    let objectUrl: string | undefined;
    void httpClient
      .get<Blob>(url, { responseType: 'blob' })
      .then(({ data }) => {
        objectUrl = URL.createObjectURL(data);
        if (active) setSource(objectUrl);
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [url]);
  if (failed) return <Typography.Text type="danger">Fotografia indisponível.</Typography.Text>;
  return source ? <img className={styles.historyImage} src={source} alt={alt} /> : null;
}
