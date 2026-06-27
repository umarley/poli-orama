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
} from '@ant-design/icons';
import { Button, Card, Col, List, Progress, Row, Statistic, Tag, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';

import { PageHeader } from '@/components/layout/PageHeader';
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
    value: 34,
    suffix: '-8%',
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
        {summary.map((item) => (
          <Col xs={24} sm={12} xl={6} key={item.title}>
            <Card className={styles.summaryCard}>
              <div className={`${styles.summaryIcon} ${styles[item.tone]}`}>{item.icon}</div>
              <Statistic title={item.title} value={item.value} groupSeparator="." />
              <Tag
                bordered={false}
                color={item.suffix.startsWith('-') ? 'red' : 'success'}
                className={styles.trend}
              >
                {item.suffix}
              </Tag>
            </Card>
          </Col>
        ))}
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
          {[
            ['27', 'JUN', 'Encontro regional com coordenadores', '09:00 · Centro'],
            ['28', 'JUN', 'Caminhada no bairro Nova Esperança', '15:30 · Zona Norte'],
            ['30', 'JUN', 'Reunião de planejamento semanal', '18:00 · Comitê central'],
          ].map(([day, month, title, meta]) => (
            <div className={styles.event} key={title}>
              <div className={styles.date}>
                <strong>{day}</strong>
                <span>{month}</span>
              </div>
              <div>
                <strong>{title}</strong>
                <Typography.Text type="secondary">{meta}</Typography.Text>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
