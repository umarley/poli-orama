import {
  ArrowLeftOutlined,
  CameraOutlined,
  CheckCircleOutlined,
  EnvironmentOutlined,
  InboxOutlined,
  PlayCircleOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  Col,
  Collapse,
  Descriptions,
  Empty,
  Form,
  Image,
  Input,
  InputNumber,
  Modal,
  Progress,
  Row,
  Skeleton,
  Space,
  Tag,
  Timeline,
  Typography,
  Upload,
} from 'antd';
import type { UploadFile } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  CircleMarker,
  MapContainer,
  Polyline,
  Popup,
  TileLayer,
  Tooltip as LeafletTooltip,
  useMap,
  useMapEvents,
} from 'react-leaflet';
import { useNavigate, useParams } from 'react-router-dom';
import 'leaflet/dist/leaflet.css';

import { PageHeader } from '@/components/layout/PageHeader';
import { AppToast } from '@/components/feedback/AppToast';
import {
  getRoute,
  installPlanningPoint,
  listTeams,
  uploadExecutionMedia,
} from '@/modules/anuncios/anuncios-service';
import type {
  ExecutionHistory,
  ExecutionMedia,
  PointStatus,
  RouteDetail,
  RoutePoint,
  RouteStatus,
} from '@/modules/anuncios/types';
import { normalizeApiError } from '@/services/api/api-error';
import { httpClient } from '@/services/api/http-client';
import { useSessionStore } from '@/stores/session-store';

import styles from './PlanningDetailPage.module.css';

const statusColors: Record<PointStatus | RouteStatus, string> = {
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

function statusLabel(status: string) {
  return status.replaceAll('_', ' ');
}

function formatDate(value: string) {
  return dayjs(value).format('DD/MM/YYYY');
}

function formatDateTime(value: string) {
  return dayjs(value).format('DD/MM/YYYY [às] HH:mm:ss');
}

function coordinate(value: string | null | undefined) {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function executionMedia(execution: ExecutionHistory): ExecutionMedia[] {
  if (execution.midias?.length) return execution.midias;
  if (!execution.foto) return [];
  return [
    {
      ...execution.foto,
      nome_original: `Fotografia ${execution.foto.anexo_id}`,
      mime_type: 'image/jpeg',
      tipo: 'foto',
    },
  ];
}

export function PlanningDetailPage() {
  const { uuid = '' } = useParams();
  const navigate = useNavigate();
  const user = useSessionStore((state) => state.user);
  const planning = useQuery({
    queryKey: ['anuncios', 'planejamento', uuid],
    queryFn: () => getRoute(uuid),
    enabled: Boolean(uuid),
    refetchInterval: 30_000,
  });
  const teams = useQuery({
    queryKey: ['anuncios', 'equipes', true],
    queryFn: () => listTeams(true),
    enabled: Boolean(planning.data?.equipe_id),
  });
  const item = planning.data;
  const team = teams.data?.items.find((candidate) => candidate.id === item?.equipe_id);
  const canRegisterExecution = Boolean(
    user?.permissions.includes('anuncios.execucao.registrar') &&
    user.profiles.some((profile) => ['gestor', 'coordenador_territorial'].includes(profile)),
  );

  if (planning.error) {
    return (
      <div className={styles.root}>
        <PageHeader
          title="Detalhamento do planejamento"
          breadcrumbs={[
            { label: 'Início', to: '/dashboard' },
            { label: 'Anúncios', to: '/anuncios' },
            { label: 'Planejamento' },
          ]}
        />
        <Alert
          type="error"
          showIcon
          message="Não foi possível carregar o planejamento"
          description={normalizeApiError(planning.error).message}
          action={<Button onClick={() => void planning.refetch()}>Tentar novamente</Button>}
        />
      </div>
    );
  }

  if (!item) {
    return (
      <div className={styles.root}>
        <Skeleton active paragraph={{ rows: 10 }} />
      </div>
    );
  }

  const percentage = item.total_pontos
    ? Math.round((item.pontos_concluidos / item.total_pontos) * 100)
    : 0;
  const executions = item.pontos.flatMap((point) => point.historico);
  const mediaCount = executions.reduce(
    (total, execution) => total + executionMedia(execution).length,
    0,
  );
  const executionDates = executions.map((execution) => execution.executado_em).sort();

  return (
    <div className={styles.root}>
      <PageHeader
        title={item.nome}
        description="Visão completa do planejamento, execução da rota e evidências registradas em campo."
        breadcrumbs={[
          { label: 'Início', to: '/dashboard' },
          { label: 'Anúncios', to: '/anuncios' },
          { label: item.nome },
        ]}
        actions={
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/anuncios?aba=routes')}>
            Voltar para planejamentos
          </Button>
        }
      />

      <section className={styles.summaryGrid} aria-label="Resumo do planejamento">
        <Card className={styles.summaryCard}>
          <Typography.Text type="secondary">Status do planejamento</Typography.Text>
          <div className={styles.summaryValue}>
            <Tag color={statusColors[item.status]}>{statusLabel(item.status)}</Tag>
          </div>
        </Card>
        <Card className={styles.summaryCard}>
          <Typography.Text type="secondary">Progresso dos pontos</Typography.Text>
          <Progress percent={percentage} size="small" />
          <Typography.Text>
            {item.pontos_concluidos} de {item.total_pontos} concluídos
          </Typography.Text>
        </Card>
        <Card className={styles.summaryCard}>
          <Typography.Text type="secondary">Execuções registradas</Typography.Text>
          <Typography.Title level={3}>{executions.length}</Typography.Title>
        </Card>
        <Card className={styles.summaryCard}>
          <Typography.Text type="secondary">Mídias registradas</Typography.Text>
          <Typography.Title level={3}>{mediaCount}</Typography.Title>
        </Card>
      </section>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={14}>
          <Card title="Dados gerais e programação" className={styles.fullHeightCard}>
            <Descriptions bordered size="small" column={{ xs: 1, md: 2 }}>
              <Descriptions.Item label="Data programada">
                {formatDate(item.data_execucao)}
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={statusColors[item.status]}>{statusLabel(item.status)}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Criado em">
                {formatDateTime(item.criado_em)}
              </Descriptions.Item>
              <Descriptions.Item label="Última atualização">
                {formatDateTime(item.atualizado_em)}
              </Descriptions.Item>
              <Descriptions.Item label="Primeiro registro em campo">
                {executionDates[0] ? formatDateTime(executionDates[0]) : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Último registro em campo">
                {executionDates.at(-1) ? formatDateTime(executionDates.at(-1)!) : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Observações" span={2}>
                {item.observacao || 'Nenhuma observação informada.'}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} xl={10}>
          <Card title="Rota e território" className={styles.fullHeightCard}>
            <Descriptions size="small" column={1}>
              <Descriptions.Item label="Rota">{item.nome}</Descriptions.Item>
              <Descriptions.Item label="Descrição">
                {item.descricao || 'Sem descrição.'}
              </Descriptions.Item>
              <Descriptions.Item label="Território">
                {item.territorio_nome || 'Não informado'}
              </Descriptions.Item>
              <Descriptions.Item label="Pontos previstos">{item.total_pontos}</Descriptions.Item>
              <Descriptions.Item label="Pontos pendentes">
                {item.pontos_pendentes}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <>
            <TeamOutlined /> Equipe e usuários associados
          </>
        }
      >
        <Descriptions column={{ xs: 1, md: 2 }}>
          <Descriptions.Item label="Equipe">
            {item.equipe_nome || 'Atribuição sem equipe'}
          </Descriptions.Item>
          <Descriptions.Item label="Responsável individual">
            {item.usuario_responsavel_nome || 'Não informado'}
          </Descriptions.Item>
          <Descriptions.Item label="Integrantes" span={2}>
            {team?.membros.length ? (
              <Space wrap>
                {team.membros.map((member) => (
                  <Tag key={member.usuario_id}>
                    {member.nome} · {member.email}
                  </Tag>
                ))}
              </Space>
            ) : item.equipe_id && teams.isPending ? (
              'Carregando integrantes…'
            ) : (
              'Nenhum integrante disponível.'
            )}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card
        title={
          <>
            <EnvironmentOutlined /> Mapa do planejamento e da execução
          </>
        }
      >
        <PlanningMap planning={item} />
      </Card>

      <PlanningMediaSection planning={item} />

      <Card title={`Pontos previstos na rota (${item.pontos.length})`}>
        <PointsSection
          points={item.pontos}
          planningStatus={item.status}
          canRegisterExecution={canRegisterExecution}
          onExecuted={() => void planning.refetch()}
        />
      </Card>
    </div>
  );
}

function PlanningMap({ planning }: { planning: RouteDetail }) {
  const planned = planning.pontos.flatMap((point) => {
    const latitude = coordinate(point.latitude_planejada);
    const longitude = coordinate(point.longitude_planejada);
    return latitude === null || longitude === null ? [] : [{ point, latitude, longitude }];
  });
  const registered = planning.pontos.flatMap((point) =>
    point.historico.flatMap((execution) => {
      const latitude = coordinate(execution.latitude);
      const longitude = coordinate(execution.longitude);
      return latitude === null || longitude === null
        ? []
        : [{ point, execution, latitude, longitude }];
    }),
  );
  const allCoordinates = [
    ...planned.map(({ latitude, longitude }) => [latitude, longitude] as [number, number]),
    ...registered.map(({ latitude, longitude }) => [latitude, longitude] as [number, number]),
  ];

  if (!allCoordinates.length) {
    return <Empty description="Nenhuma localização foi informada para este planejamento." />;
  }

  return (
    <>
      <Space wrap className={styles.mapLegend}>
        <Tag color="blue">Círculo numerado: ponto planejado</Tag>
        <Tag color="green">Ponto interno: instalação</Tag>
        <Tag color="orange">Ponto interno: retirada</Tag>
      </Space>
      <MapContainer center={allCoordinates[0]} zoom={14} className={styles.map}>
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitPlanningMap coordinates={allCoordinates} />
        {planned.length > 1 ? (
          <Polyline
            positions={planned.map(({ latitude, longitude }) => [latitude, longitude])}
            pathOptions={{ color: '#1677ff', opacity: 0.55, weight: 3 }}
          />
        ) : null}
        {planned.map(({ point, latitude, longitude }) => (
          <CircleMarker
            key={`planned-${point.uuid_publico}`}
            center={[latitude, longitude]}
            radius={12}
            pathOptions={{
              color: markerColors[point.status],
              fillColor: markerColors[point.status],
              fillOpacity: 0.7,
              weight: 2,
            }}
          >
            <LeafletTooltip permanent direction="center" className={styles.pointNumberTooltip}>
              {point.ordem}
            </LeafletTooltip>
            <Popup>
              <strong>
                {point.ordem}. {point.descricao_local}
              </strong>
              <br />
              Local planejado
              <br />
              {point.endereco || 'Sem endereço'}
              <br />
              Status: {statusLabel(point.status)}
            </Popup>
          </CircleMarker>
        ))}
        {registered.map(({ point, execution, latitude, longitude }) => (
          <CircleMarker
            key={`registered-${execution.uuid_publico}`}
            center={[latitude, longitude]}
            radius={6}
            pathOptions={{
              color: '#fff',
              fillColor: execution.tipo_operacao === 'INSTALACAO' ? '#389e0d' : '#d46b08',
              fillOpacity: 1,
              weight: 2,
            }}
          >
            <Popup>
              <strong>
                {point.ordem}. {point.descricao_local}
              </strong>
              <br />
              {execution.tipo_operacao === 'INSTALACAO' ? 'Instalação' : 'Retirada'}
              <br />
              {formatDateTime(execution.executado_em)}
              <br />
              Registrado por {execution.usuario_nome}
              {execution.precisao ? (
                <>
                  <br />
                  Precisão: {execution.precisao} m
                </>
              ) : null}
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </>
  );
}

function FitPlanningMap({ coordinates }: { coordinates: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    map.invalidateSize();
    if (coordinates.length === 1) {
      map.setView(coordinates[0], 16);
    } else {
      map.fitBounds(coordinates, { padding: [32, 32], maxZoom: 16 });
    }
  }, [coordinates, map]);
  return null;
}

function PlanningMediaSection({ planning }: { planning: RouteDetail }) {
  const groups = planning.pontos.flatMap((point) =>
    point.historico.flatMap((execution) => {
      const media = executionMedia(execution);
      return media.length ? [{ point, execution, media }] : [];
    }),
  );
  const total = groups.reduce((sum, group) => sum + group.media.length, 0);

  return (
    <Card title={`Mídias registradas durante a execução (${total})`}>
      {groups.length ? (
        <div className={styles.mediaGroups}>
          {groups.map(({ point, execution, media }) => (
            <section className={styles.mediaGroup} key={execution.uuid_publico}>
              <div className={styles.mediaGroupHeader}>
                <div>
                  <Typography.Title level={5}>
                    Ponto {point.ordem} · {point.descricao_local}
                  </Typography.Title>
                  <Typography.Text type="secondary">
                    {execution.tipo_operacao === 'INSTALACAO' ? 'Instalação' : 'Retirada'} por{' '}
                    {execution.usuario_nome} em {formatDateTime(execution.executado_em)}
                  </Typography.Text>
                </div>
                <Tag color={execution.tipo_operacao === 'INSTALACAO' ? 'green' : 'orange'}>
                  {execution.tipo_operacao === 'INSTALACAO' ? 'INSTALAÇÃO' : 'RETIRADA'}
                </Tag>
              </div>
              <div className={styles.mediaGrid}>
                {media.map((item) => (
                  <AuthenticatedMedia media={item} key={item.anexo_id} />
                ))}
              </div>
            </section>
          ))}
        </div>
      ) : (
        <Empty description="Nenhuma mídia foi registrada neste planejamento." />
      )}
    </Card>
  );
}

function AuthenticatedMedia({ media }: { media: ExecutionMedia }) {
  const [source, setSource] = useState<string>();
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    let objectUrl: string | undefined;
    void httpClient
      .get<Blob>(media.preview_url || media.download_url, {
        responseType: 'blob',
        timeout: 120_000,
      })
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
  }, [media.download_url, media.preview_url]);

  return (
    <article className={styles.mediaCard}>
      <div className={styles.mediaViewport}>
        {failed ? (
          <Alert type="error" showIcon message="Mídia indisponível" />
        ) : !source ? (
          <Skeleton.Image active />
        ) : media.tipo === 'video' ? (
          <video className={styles.video} controls preload="metadata" src={source}>
            Seu navegador não oferece suporte à reprodução deste vídeo.
          </video>
        ) : (
          <Image
            className={styles.image}
            src={source}
            alt={media.nome_original}
            preview={{ mask: 'Ampliar fotografia' }}
          />
        )}
      </div>
      <div className={styles.mediaMetadata}>
        <Tag icon={media.tipo === 'video' ? <PlayCircleOutlined /> : <CameraOutlined />}>
          {media.tipo === 'video' ? 'Vídeo' : 'Fotografia'}
        </Tag>
        <Typography.Text ellipsis title={media.nome_original}>
          {media.nome_original}
        </Typography.Text>
        <Typography.Text type="secondary">{formatDateTime(media.criado_em)}</Typography.Text>
      </div>
    </article>
  );
}

function PointsSection({
  points,
  planningStatus,
  canRegisterExecution,
  onExecuted,
}: {
  points: RoutePoint[];
  planningStatus: RouteStatus;
  canRegisterExecution: boolean;
  onExecuted: () => void;
}) {
  const items = useMemo(
    () =>
      [...points]
        .sort((first, second) => first.ordem - second.ordem)
        .map((point) => ({
          key: point.uuid_publico,
          label: (
            <div className={styles.pointHeading}>
              <strong>
                {point.ordem}. {point.descricao_local}
              </strong>
              <Tag color={statusColors[point.status]}>{statusLabel(point.status)}</Tag>
            </div>
          ),
          children: (
            <PointDetails
              point={point}
              planningStatus={planningStatus}
              canRegisterExecution={canRegisterExecution}
              onExecuted={onExecuted}
            />
          ),
        })),
    [canRegisterExecution, onExecuted, planningStatus, points],
  );

  return <Collapse items={items} defaultActiveKey={items[0]?.key ? [items[0].key] : []} />;
}

function PointDetails({
  point,
  planningStatus,
  canRegisterExecution,
  onExecuted,
}: {
  point: RoutePoint;
  planningStatus: RouteStatus;
  canRegisterExecution: boolean;
  onExecuted: () => void;
}) {
  const [executionOpen, setExecutionOpen] = useState(false);
  const canInstall =
    canRegisterExecution &&
    ['LIBERADA', 'EM_EXECUCAO'].includes(planningStatus) &&
    ['PENDENTE', 'EM_EXECUCAO'].includes(point.status) &&
    point.materiais.some((material) => material.quantidade_pendente > 0);

  return (
    <Space direction="vertical" size={20} className={styles.pointDetails}>
      {canInstall ? (
        <Alert
          type="info"
          showIcon
          message="Este ponto está disponível para execução"
          description="Registre o local efetivo, as quantidades instaladas e as evidências da instalação."
          action={
            <Button
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={() => setExecutionOpen(true)}
            >
              Registrar execução
            </Button>
          }
        />
      ) : null}
      <Descriptions size="small" bordered column={{ xs: 1, md: 2 }}>
        <Descriptions.Item label="Endereço" span={2}>
          {point.endereco || 'Não informado'}
        </Descriptions.Item>
        <Descriptions.Item label="Localização planejada">
          {point.latitude_planejada && point.longitude_planejada
            ? `${point.latitude_planejada}, ${point.longitude_planejada}`
            : 'Não informada'}
        </Descriptions.Item>
        <Descriptions.Item label="Status">
          <Tag color={statusColors[point.status]}>{statusLabel(point.status)}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Observações" span={2}>
          {point.observacao || 'Nenhuma observação.'}
        </Descriptions.Item>
      </Descriptions>

      <div>
        <Typography.Title level={5}>Materiais</Typography.Title>
        {point.materiais.length ? (
          <div className={styles.materialGrid}>
            {point.materiais.map((material) => (
              <Card size="small" key={material.id} title={material.material_nome}>
                <Descriptions size="small" column={2}>
                  <Descriptions.Item label="Planejado">
                    {material.quantidade_planejada}
                  </Descriptions.Item>
                  <Descriptions.Item label="Instalado">
                    {material.quantidade_instalada}
                  </Descriptions.Item>
                  <Descriptions.Item label="Recolhido">
                    {material.quantidade_recolhida}
                  </Descriptions.Item>
                  <Descriptions.Item label="Extraviado">
                    {material.quantidade_extraviada}
                  </Descriptions.Item>
                  <Descriptions.Item label="Pendente">
                    {material.quantidade_pendente}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            ))}
          </div>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Nenhum material previsto." />
        )}
      </div>

      <div>
        <Typography.Title level={5}>Histórico da execução</Typography.Title>
        {point.historico.length ? (
          <Timeline
            items={point.historico.map((execution) => ({
              color: execution.tipo_operacao === 'INSTALACAO' ? 'green' : 'orange',
              children: <ExecutionDetails execution={execution} />,
            }))}
          />
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Sem execução registrada." />
        )}
      </div>

      <ExecutionModal
        point={point}
        open={executionOpen}
        onCancel={() => setExecutionOpen(false)}
        onExecuted={onExecuted}
      />
    </Space>
  );
}

interface ExecutionFormValues {
  materiais: Record<string, number>;
  observacao?: string;
}

interface SelectedLocation {
  latitude: number;
  longitude: number;
  accuracy?: number;
}

function ExecutionModal({
  point,
  open,
  onCancel,
  onExecuted,
}: {
  point: RoutePoint;
  open: boolean;
  onCancel: () => void;
  onExecuted: () => void;
}) {
  const [form] = Form.useForm<ExecutionFormValues>();
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [location, setLocation] = useState<SelectedLocation>();
  const [locationError, setLocationError] = useState('');
  const [locating, setLocating] = useState(false);
  const idempotencyKey = useRef(crypto.randomUUID());
  const plannedLatitude = coordinate(point.latitude_planejada);
  const plannedLongitude = coordinate(point.longitude_planejada);
  const mapCenter: [number, number] =
    plannedLatitude !== null && plannedLongitude !== null
      ? [plannedLatitude, plannedLongitude]
      : [-15.7797, -47.9297];

  const save = useMutation({
    mutationFn: async (values: ExecutionFormValues) => {
      if (!location) throw new Error('Indique no mapa o local efetivo da instalação.');
      const materials = point.materiais.flatMap((material) => {
        const quantity = Number(values.materiais?.[String(material.material_id)] ?? 0);
        return quantity > 0 ? [{ material_id: material.material_id, quantidade: quantity }] : [];
      });
      if (!materials.length) throw new Error('Informe ao menos uma quantidade maior que zero.');
      const primaryPhoto = files.find((file) => file.type?.startsWith('image/'))?.originFileObj;
      if (!primaryPhoto) throw new Error('Anexe ao menos uma fotografia da instalação.');

      const operation = await installPlanningPoint(
        point.uuid_publico,
        {
          chave_idempotencia: idempotencyKey.current,
          latitude: location.latitude,
          longitude: location.longitude,
          precisao: location.accuracy,
          capturado_em: new Date().toISOString(),
          observacao: values.observacao?.trim() || undefined,
          materiais: materials,
        },
        primaryPhoto,
      );
      const additionalFiles = files.flatMap((file) =>
        file.originFileObj && file.originFileObj !== primaryPhoto ? [file.originFileObj] : [],
      );
      const uploads = await Promise.allSettled(
        additionalFiles.map((file) => uploadExecutionMedia(operation.execucao.uuid_publico, file)),
      );
      return { failedUploads: uploads.filter((result) => result.status === 'rejected').length };
    },
    onSuccess: ({ failedUploads }) => {
      AppToast.success('Execução do ponto registrada com sucesso.');
      if (failedUploads) {
        AppToast.error(
          `${failedUploads} mídia(s) não puderam ser enviadas. A execução e as demais evidências foram preservadas.`,
        );
      }
      form.resetFields();
      setFiles([]);
      setLocation(undefined);
      setLocationError('');
      idempotencyKey.current = crypto.randomUUID();
      onCancel();
      onExecuted();
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const useCurrentLocation = () => {
    if (!navigator.geolocation) {
      setLocationError('A geolocalização não está disponível neste navegador.');
      return;
    }
    setLocating(true);
    setLocationError('');
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setLocation({
          latitude: coords.latitude,
          longitude: coords.longitude,
          accuracy: coords.accuracy,
        });
        setLocating(false);
      },
      () => {
        setLocationError(
          'Não foi possível obter sua localização. Autorize o navegador ou marque o ponto no mapa.',
        );
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 15_000, maximumAge: 0 },
    );
  };

  return (
    <Modal
      open={open}
      width="min(920px, 96vw)"
      title={`Registrar execução · Ponto ${point.ordem}`}
      okText="Confirmar execução"
      cancelText="Cancelar"
      confirmLoading={save.isPending}
      maskClosable={!save.isPending}
      closable={!save.isPending}
      cancelButtonProps={{ disabled: save.isPending }}
      onCancel={onCancel}
      onOk={() => void form.validateFields().then((values) => save.mutate(values))}
      destroyOnHidden
    >
      <Alert
        type="warning"
        showIcon
        message="Confirme o local onde o material foi realmente instalado"
        description="Clique no mapa ou use a localização atual do dispositivo. O marcador verde será gravado no histórico."
        className={styles.executionNotice}
      />
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          materiais: Object.fromEntries(
            point.materiais.map((material) => [
              String(material.material_id),
              material.quantidade_pendente,
            ]),
          ),
        }}
      >
        <Form.Item label="Local efetivo da instalação" required>
          <div className={styles.executionMapToolbar}>
            <Button icon={<EnvironmentOutlined />} loading={locating} onClick={useCurrentLocation}>
              Usar minha localização
            </Button>
            <Typography.Text type={location ? 'success' : 'secondary'}>
              {location
                ? `${location.latitude.toFixed(7)}, ${location.longitude.toFixed(7)}${location.accuracy ? ` · precisão ${Math.round(location.accuracy)} m` : ''}`
                : 'Nenhum local selecionado'}
            </Typography.Text>
          </div>
          {locationError ? <Alert type="error" message={locationError} showIcon /> : null}
          <MapContainer
            center={mapCenter}
            zoom={plannedLatitude === null ? 4 : 17}
            className={styles.executionMap}
          >
            <TileLayer
              attribution="&copy; OpenStreetMap contributors"
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <LocationPicker onSelect={setLocation} />
            <RecenterLocation location={location} />
            {plannedLatitude !== null && plannedLongitude !== null ? (
              <CircleMarker
                center={[plannedLatitude, plannedLongitude]}
                radius={10}
                pathOptions={{ color: '#1677ff', fillColor: '#1677ff', fillOpacity: 0.45 }}
              >
                <LeafletTooltip>Local planejado</LeafletTooltip>
              </CircleMarker>
            ) : null}
            {location ? (
              <CircleMarker
                center={[location.latitude, location.longitude]}
                radius={9}
                pathOptions={{ color: '#237804', fillColor: '#52c41a', fillOpacity: 0.9 }}
              >
                <LeafletTooltip permanent>Instalação</LeafletTooltip>
              </CircleMarker>
            ) : null}
          </MapContainer>
        </Form.Item>

        <Typography.Title level={5}>Materiais efetivamente instalados</Typography.Title>
        <div className={styles.executionMaterials}>
          {point.materiais.map((material) => (
            <Form.Item
              key={material.material_id}
              name={['materiais', String(material.material_id)]}
              label={`${material.material_nome} (saldo: ${material.quantidade_pendente})`}
              rules={[
                { required: true, message: 'Informe a quantidade.' },
                {
                  type: 'number',
                  min: 0,
                  max: material.quantidade_pendente,
                  message: `Use um valor entre 0 e ${material.quantidade_pendente}.`,
                },
              ]}
            >
              <InputNumber min={0} max={material.quantidade_pendente} precision={0} />
            </Form.Item>
          ))}
        </div>

        <Form.Item name="observacao" label="Observações">
          <Input.TextArea rows={3} maxLength={1000} showCount />
        </Form.Item>

        <Form.Item
          label="Fotografias e vídeos"
          required
          extra="Ao menos uma fotografia é obrigatória. Você pode anexar várias fotos e vídeos."
        >
          <Upload.Dragger
            multiple
            accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/webm"
            fileList={files}
            beforeUpload={(file) => {
              if (!file.type.startsWith('image/') && !file.type.startsWith('video/')) {
                AppToast.error('Selecione somente fotografias ou vídeos.');
                return Upload.LIST_IGNORE;
              }
              return false;
            }}
            onChange={({ fileList }) => setFiles(fileList)}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">Clique ou arraste as evidências para esta área</p>
            <p className="ant-upload-hint">Imagens JPG, PNG ou WebP e vídeos MP4, MOV ou WebM.</p>
          </Upload.Dragger>
        </Form.Item>
      </Form>
    </Modal>
  );
}

function LocationPicker({ onSelect }: { onSelect: (location: SelectedLocation) => void }) {
  useMapEvents({
    click: ({ latlng }) => onSelect({ latitude: latlng.lat, longitude: latlng.lng }),
  });
  return null;
}

function RecenterLocation({ location }: { location?: SelectedLocation }) {
  const map = useMap();
  useEffect(() => {
    if (location) map.setView([location.latitude, location.longitude], Math.max(map.getZoom(), 17));
  }, [location, map]);
  return null;
}

function ExecutionDetails({ execution }: { execution: ExecutionHistory }) {
  const media = executionMedia(execution);
  return (
    <div className={styles.execution}>
      <Space wrap>
        <Typography.Text strong>
          {execution.tipo_operacao === 'INSTALACAO' ? 'Instalação' : 'Retirada'}
        </Typography.Text>
        <Tag>{formatDateTime(execution.executado_em)}</Tag>
        {media.length ? <Tag color="purple">{media.length} mídia(s)</Tag> : null}
      </Space>
      <div>Registrado por: {execution.usuario_nome}</div>
      <div>
        Localização: {execution.latitude}, {execution.longitude}
        {execution.precisao ? ` · precisão ${execution.precisao} m` : ''}
      </div>
      {execution.observacao ? (
        <Typography.Paragraph>{execution.observacao}</Typography.Paragraph>
      ) : null}
      {execution.movimentacoes.length ? (
        <div className={styles.movements}>
          {execution.movimentacoes.map((movement) => (
            <Tag key={movement.id}>
              {statusLabel(movement.tipo_movimentacao)} · {movement.material_nome} ·{' '}
              {movement.quantidade}
            </Tag>
          ))}
        </div>
      ) : (
        <Typography.Text type="secondary">Nenhuma movimentação de material.</Typography.Text>
      )}
    </div>
  );
}
