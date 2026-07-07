import {
  CalendarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  FlagOutlined,
  TeamOutlined,
  UserAddOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Empty,
  List,
  Row,
  Select,
  Space,
  Statistic,
  Tag,
  Typography,
} from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { PageHeader } from '@/components/layout/PageHeader';
import { listarLiderancas } from '@/modules/cadastro/pessoas-service';
import {
  getBirthdays,
  getCommemorativeDates,
  getDashboardConfiguration,
  getDashboardOverview,
} from '@/modules/dashboard/dashboard-service';
import type { DashboardFilters } from '@/modules/dashboard/types';
import { listarTerritorios } from '@/modules/territorios/territorios-service';
import { useSessionStore } from '@/stores/session-store';

import styles from './DashboardPage.module.css';

const { RangePicker } = DatePicker;

export function DashboardPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<DashboardFilters>({
    data_inicio: dayjs().subtract(29, 'day').format('YYYY-MM-DD'),
    data_fim: dayjs().format('YYYY-MM-DD'),
  });
  const currentCampaign = useSessionStore((state) => state.currentCampaign);
  const overview = useQuery({
    queryKey: ['dashboard', 'overview', filters],
    queryFn: () => getDashboardOverview(filters),
  });
  const birthdays = useQuery({
    queryKey: ['dashboard', 'birthdays', filters],
    queryFn: () => getBirthdays(filters),
  });
  const dates = useQuery({
    queryKey: ['dashboard', 'dates', filters],
    queryFn: () => getCommemorativeDates(filters),
  });
  const configuration = useQuery({
    queryKey: ['dashboard', 'configuration'],
    queryFn: getDashboardConfiguration,
  });
  const territories = useQuery({
    queryKey: ['territorios', 'dashboard-options'],
    queryFn: () => listarTerritorios(false),
  });
  const leaders = useQuery({
    queryKey: ['cadastro', 'liderancas', 'dashboard-options'],
    queryFn: listarLiderancas,
  });
  const enabled = (widget: string) =>
    !configuration.data || configuration.data.widgets.includes(widget);
  const data = overview.data;

  return (
    <div className={styles.page}>
      <PageHeader
        title="Painel de controle"
        description={
          currentCampaign
            ? `${currentCampaign.name} — ${currentCampaign.office}, eleições ${currentCampaign.election.year}.`
            : 'Indicadores executivos e operacionais da campanha.'
        }
        breadcrumbs={[{ label: 'Início' }, { label: 'Painel de controle' }]}
        actions={
          <Button icon={<FileTextOutlined />} onClick={() => navigate('/relatorios')}>
            Relatórios
          </Button>
        }
      />

      <Card size="small" aria-label="Filtros globais do dashboard">
        <Space wrap>
          <RangePicker
            allowClear={false}
            value={[dayjs(filters.data_inicio), dayjs(filters.data_fim)]}
            onChange={(range) => {
              if (range?.[0] && range[1]) {
                setFilters((current) => ({
                  ...current,
                  data_inicio: range[0]!.format('YYYY-MM-DD'),
                  data_fim: range[1]!.format('YYYY-MM-DD'),
                }));
              }
            }}
          />
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="Todos os territórios"
            style={{ minWidth: 220 }}
            value={filters.territorio_id}
            options={(territories.data ?? []).map((item) => ({
              value: item.id,
              label: item.nome,
            }))}
            onChange={(territorio_id) =>
              setFilters((current) => ({ ...current, territorio_id }))
            }
          />
          <Select
            allowClear
            placeholder="Todas as lideranças"
            style={{ minWidth: 220 }}
            value={filters.lideranca_id}
            options={(leaders.data ?? []).map((item) => ({
              value: item.id,
              label: item.apelido_campanha || `Liderança #${item.id}`,
            }))}
            onChange={(lideranca_id) =>
              setFilters((current) => ({ ...current, lideranca_id }))
            }
          />
        </Space>
      </Card>

      {overview.isError && (
        <Alert
          type="error"
          showIcon
          message="Não foi possível carregar os indicadores."
          action={<Button onClick={() => overview.refetch()}>Tentar novamente</Button>}
        />
      )}

      <Row gutter={[16, 16]}>
        {enabled('cadastros') && (
          <Col xs={24} md={12} xl={8}>
            <Card loading={overview.isPending} title="Cadastros" extra={<TeamOutlined />}>
              <Row gutter={12}>
                <Col span={8}><Statistic title="Total" value={data?.cadastros.total ?? 0} /></Col>
                <Col span={8}>
                  <Statistic title="Novos" value={data?.cadastros.novos_periodo ?? 0} />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="Pendentes"
                    value={data?.cadastros.incompletos_pendentes ?? 0}
                    valueStyle={{ color: data?.cadastros.incompletos_pendentes ? '#d46b08' : undefined }}
                  />
                </Col>
              </Row>
              <Typography.Text type="secondary">
                Completude média: {data?.cadastros.completude_media ?? 0}% · Duplicidades:{' '}
                {data?.cadastros.duplicidades_abertas ?? 0}
              </Typography.Text>
            </Card>
          </Col>
        )}
        {enabled('liderancas') && (
          <Col xs={24} md={12} xl={8}>
            <Card loading={overview.isPending} title="Lideranças" extra={<UserAddOutlined />}>
              <Row gutter={12}>
                <Col span={8}>
                  <Statistic title="Líderes" value={data?.liderancas.total_lideres ?? 0} />
                </Col>
                <Col span={8}>
                  <Statistic title="Liderados" value={data?.liderancas.total_liderados ?? 0} />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="Média/líder"
                    value={data?.liderancas.media_liderados ?? 0}
                    precision={2}
                  />
                </Col>
              </Row>
            </Card>
          </Col>
        )}
        {enabled('metas') && (
          <Col xs={24} md={12} xl={8}>
            <Card loading={overview.isPending} title="Metas" extra={<FlagOutlined />}>
              <Row gutter={12}>
                <Col span={8}>
                  <Statistic title="Ativas" value={data?.metas.metas_ativas ?? 0} />
                </Col>
                <Col span={8}>
                  <Statistic title="Atingidas" value={data?.metas.atingidas ?? 0} />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="Em risco"
                    value={data?.metas.em_risco ?? 0}
                    valueStyle={{ color: data?.metas.em_risco ? '#cf1322' : undefined }}
                  />
                </Col>
              </Row>
              <Typography.Text type="secondary">
                Atingimento médio: {data?.metas.percentual_medio ?? 0}%
              </Typography.Text>
            </Card>
          </Col>
        )}
        {enabled('demandas') && (
          <Col xs={24} md={12} xl={12}>
            <Card loading={overview.isPending} title="Demandas" extra={<ClockCircleOutlined />}>
              <Row gutter={12}>
                <Col span={6}>
                  <Statistic title="Pendentes" value={data?.demandas.pendentes ?? 0} />
                </Col>
                <Col span={6}>
                  <Statistic title="Em andamento" value={data?.demandas.em_andamento ?? 0} />
                </Col>
                <Col span={6}>
                  <Statistic title="Concluídas" value={data?.demandas.concluidas ?? 0} />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="Vencidas"
                    value={data?.demandas.vencidas ?? 0}
                    prefix={<WarningOutlined />}
                    valueStyle={{ color: data?.demandas.vencidas ? '#cf1322' : undefined }}
                  />
                </Col>
              </Row>
            </Card>
          </Col>
        )}
        {enabled('eventos') && (
          <Col xs={24} md={12} xl={12}>
            <Card loading={overview.isPending} title="Eventos" extra={<CalendarOutlined />}>
              <Row gutter={12}>
                <Col span={6}>
                  <Statistic title="No período" value={data?.eventos.total_periodo ?? 0} />
                </Col>
                <Col span={6}>
                  <Statistic title="Realizados" value={data?.eventos.realizados ?? 0} />
                </Col>
                <Col span={6}>
                  <Statistic title="Cancelados" value={data?.eventos.cancelados ?? 0} />
                </Col>
                <Col span={6}>
                  <Statistic
                    title="Com presença"
                    value={data?.eventos.presencas_registradas ?? 0}
                    prefix={<CheckCircleOutlined />}
                  />
                </Col>
              </Row>
            </Card>
          </Col>
        )}
      </Row>

      <Row gutter={[16, 16]}>
        {enabled('aniversariantes') && (
          <Col xs={24} lg={12}>
            <Card title="Aniversariantes" loading={birthdays.isPending}>
              {!!birthdays.data?.hoje.length && (
                <Alert
                  type="success"
                  showIcon
                  message={`${birthdays.data.hoje.length} aniversariante(s) hoje`}
                  className={styles.widgetAlert}
                />
              )}
              <List
                dataSource={(birthdays.data?.mes ?? []).slice(0, 8)}
                locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Nenhum aniversariante no mês" /> }}
                renderItem={(item) => (
                  <List.Item extra={<Tag>{dayjs(item.data_nascimento).format('DD/MM')}</Tag>}>
                    <List.Item.Meta
                      title={item.nome}
                      description={item.territorio || 'Sem território vinculado'}
                    />
                  </List.Item>
                )}
              />
            </Card>
          </Col>
        )}
        {enabled('datas_comemorativas') && (
          <Col xs={24} lg={12}>
            <Card title="Próximas datas comemorativas" loading={dates.isPending}>
              <List
                dataSource={(dates.data ?? []).slice(0, 8)}
                locale={{ emptyText: 'Nenhuma data nos próximos 30 dias' }}
                renderItem={(item) => (
                  <List.Item extra={<Tag color="blue">{dayjs(item.data).format('DD/MM')}</Tag>}>
                    <List.Item.Meta
                      title={item.nome}
                      description={`${item.categoria || 'Geral'} · ${item.ambito}`}
                    />
                  </List.Item>
                )}
              />
            </Card>
          </Col>
        )}
      </Row>
    </div>
  );
}
