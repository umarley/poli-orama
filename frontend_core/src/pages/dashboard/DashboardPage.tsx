import {
  ArrowRightOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  EnvironmentOutlined,
  FlagOutlined,
  PlusOutlined,
  TeamOutlined,
  UserAddOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { Button, Card, Col, List, Progress, Row, Statistic, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useNavigate } from 'react-router-dom';

import { PageHeader } from '@/components/layout/PageHeader';
import { listEvents } from '@/modules/agenda/agenda-service';
import { obterResumoMetas } from '@/modules/metas/metas-service';
import { getDemandSummary } from '@/modules/demandas/demandas-service';
import { useSessionStore } from '@/stores/session-store';

import styles from './DashboardPage.module.css';

const summary = [
  {
    title: 'Pessoas cadastradas',
    value: 12480,
    suffix: '+6,2%',
    icon: <TeamOutlined />,
    tone: 'blue',
  },
  {
    title: 'Lideranças ativas',
    value: 186,
    suffix: '+12',
    icon: <UserAddOutlined />,
    tone: 'green',
  },
  {
    title: 'Meta de votos',
    value: 68,
    suffix: '%',
    icon: <FlagOutlined />,
    tone: 'orange',
  },
  {
    title: 'Demandas pendentes',
    value: 0,
    suffix: '',
    icon: <ClockCircleOutlined />,
    tone: 'purple',
  },
] as const;

const activities = [
  {
    title: 'Reunião com lideranças do Setor Norte',
    meta: 'Hoje, 14:30 · Comitê central',
    icon: <CalendarOutlined />,
    color: 'blue',
  },
  {
    title: 'Nova liderança vinculada à Vila Aurora',
    meta: 'Há 45 minutos · Cadastro',
    icon: <UserAddOutlined />,
    color: 'green',
  },
  {
    title: 'Demanda de iluminação foi concluída',
    meta: 'Há 2 horas · Jardim Primavera',
    icon: <CheckCircleOutlined />,
    color: 'cyan',
  },
  {
    title: 'Meta territorial revisada',
    meta: 'Ontem, 18:15 · Zona Leste',
    icon: <EnvironmentOutlined />,
    color: 'orange',
  },
];

export function DashboardPage() {
  const navigate = useNavigate();
  const goalsSummary = useQuery({
    queryKey: ['metas', 'resumo'],
    queryFn: () => obterResumoMetas(),
  });
  const upcomingEvents = useQuery({
    queryKey: ['agenda', 'dashboard-proximos'],
    queryFn: () =>
      listEvents({
        data_inicio: dayjs().toISOString(),
        data_fim: dayjs().add(30, 'day').toISOString(),
      }),
  });
  const demandSummary = useQuery({
    queryKey: ['demandas', 'resumo'],
    queryFn: getDemandSummary,
  });
  const demandStatusTotal = (status: string) =>
    demandSummary.data?.por_status.find(
      (item) => item.chave.toLocaleLowerCase() === status.toLocaleLowerCase(),
    )?.total ?? 0;
  const currentCampaign = useSessionStore((state) => state.currentCampaign);
  const campaignDescription = currentCampaign
    ? `${currentCampaign.name} — ${currentCampaign.office}, eleições ${currentCampaign.election.year}.`
    : 'Selecione uma campanha para acompanhar seus principais indicadores.';

  return (
    <div className={styles.page}>
      <PageHeader
        title="Painel de controle"
        description={campaignDescription}
        breadcrumbs={[{ label: 'Início' }, { label: 'Painel de controle' }]}
        actions={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/cadastro')}>
            Novo cadastro
          </Button>
        }
      />

      <Row gutter={[16, 16]}>
        {summary.map((item) => {
          const isGoals = item.title === 'Meta de votos';
          const isDemands = item.title === 'Demandas pendentes';
          const value = isDemands
            ? demandStatusTotal('Pendente')
            : isGoals
            ? Number(goalsSummary.data?.percentual_geral ?? 0)
            : item.value;
          const suffix = isGoals ? '%' : item.suffix;
          return (
          <Col xs={24} sm={12} xl={6} key={item.title}>
            <Card className={styles.summaryCard}>
              <div className={`${styles.summaryIcon} ${styles[item.tone]}`}>{item.icon}</div>
              <Statistic title={item.title} value={value} groupSeparator="." />
              {suffix && <Tag
                bordered={false}
                color={
                  isGoals && (goalsSummary.data?.metas_em_risco ?? 0) > 0
                    ? 'red'
                    : suffix.startsWith('-')
                      ? 'red'
                      : 'success'
                }
                className={styles.trend}
              >
                {isGoals && (goalsSummary.data?.metas_em_risco ?? 0) > 0
                  ? `${goalsSummary.data?.metas_em_risco} em risco`
                  : suffix}
              </Tag>}
            </Card>
          </Col>
          );
        })}
      </Row>

      <Row gutter={[16, 16]} aria-label="Resumo de demandas">
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="Demandas em andamento"
              value={demandStatusTotal('Em andamento')} prefix={<ClockCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="Demandas concluídas"
              value={demandStatusTotal('Concluida')} prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic title="Demandas vencidas" value={demandSummary.data?.vencidas ?? 0}
              prefix={<WarningOutlined />}
              valueStyle={(demandSummary.data?.vencidas ?? 0) > 0
                ? { color: '#cf1322' } : undefined} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} aria-label="Resumo operacional de metas">
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="Metas ativas"
              value={goalsSummary.data?.metas_ativas ?? 0}
              prefix={<FlagOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="Metas atingidas"
              value={goalsSummary.data?.metas_atingidas ?? 0}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card>
            <Statistic
              title="Metas em risco"
              value={goalsSummary.data?.metas_em_risco ?? 0}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={16}>
          <Card
            title="Desempenho por território"
            extra={
              <Button type="link" onClick={() => navigate('/metas')}>
                Ver detalhes <ArrowRightOutlined />
              </Button>
            }
          >
            <div className={styles.territoryList}>
              {[
                ['Zona Norte', 82, '4.920 de 6.000'],
                ['Zona Sul', 74, '3.700 de 5.000'],
                ['Zona Leste', 67, '5.360 de 8.000'],
                ['Zona Oeste', 51, '2.550 de 5.000'],
              ].map(([name, value, detail]) => (
                <div className={styles.territoryRow} key={name}>
                  <div className={styles.territoryInfo}>
                    <strong>{name}</strong>
                    <Typography.Text type="secondary">{detail} votos mapeados</Typography.Text>
                  </div>
                  <div className={styles.progress}>
                    <Progress
                      percent={Number(value)}
                      strokeColor={Number(value) >= 70 ? '#52c41a' : '#1677ff'}
                      trailColor="#f0f0f0"
                    />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Col>

        <Col xs={24} xl={8}>
          <Card
            title="Atividade recente"
            extra={<Button type="link">Ver todas</Button>}
            className={styles.activityCard}
          >
            <List
              dataSource={activities}
              renderItem={(activity) => (
                <List.Item>
                  <List.Item.Meta
                    avatar={
                      <span className={styles.activityIcon} data-color={activity.color}>
                        {activity.icon}
                      </span>
                    }
                    title={activity.title}
                    description={activity.meta}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      <Card title="Próximos compromissos">
        <div className={styles.events}>
          {(upcomingEvents.data ?? []).slice(0, 5).map((event) => (
            <div
              className={styles.event}
              key={event.id}
              role="button"
              tabIndex={0}
              onClick={() => navigate(`/agenda/eventos/${event.id}`)}
              onKeyDown={(keyEvent) => {
                if (keyEvent.key === 'Enter') navigate(`/agenda/eventos/${event.id}`);
              }}
            >
              <div className={styles.date}>
                <strong>{dayjs(event.data_inicio).format('DD')}</strong>
                <span>{dayjs(event.data_inicio).format('MMM').toUpperCase()}</span>
              </div>
              <div>
                <strong>{event.titulo}</strong>
                <Typography.Text type="secondary">
                  {dayjs(event.data_inicio).format('HH:mm')} ·{' '}
                  {event.local_nome || event.territorio_nome || 'Local a definir'}
                </Typography.Text>
              </div>
            </div>
          ))}
          {!upcomingEvents.isPending && !upcomingEvents.data?.length && (
            <Typography.Text type="secondary">
              Nenhum compromisso nos próximos 30 dias.
            </Typography.Text>
          )}
        </div>
      </Card>
    </div>
  );
}
