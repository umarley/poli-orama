import {
  BarChartOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CommentOutlined,
  PhoneOutlined,
  StopOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Card, Col, DatePicker, Form, Row, Select, Table } from 'antd';
import dayjs from 'dayjs';
import { useMemo, useState } from 'react';

import { LocalizedStatistic as Statistic } from '@/components/data/LocalizedStatistic';
import { PageHeader } from '@/components/layout/PageHeader';
import { getAttendanceIndicators, listAttendanceChannels } from '@/modules/comunicacao/atendimento-service';
import { normalizeApiError } from '@/services/api/api-error';
import { formatInteger, formatNumber, formatPercent } from '@/utils/number-format';

import styles from './ComunicacaoPage.module.css';

const statusOptions = [
  { value: 'em_atendimento', label: 'Em atendimento' },
  { value: 'concluido', label: 'Concluído' },
  { value: 'sem_resposta', label: 'Sem resposta' },
  { value: 'numero_invalido', label: 'Número inválido' },
  { value: 'interrompido', label: 'Interrompido' },
];

const resultOptions = [
  { value: 'confirmado', label: 'Confirmado' },
  { value: 'indeciso', label: 'Indeciso' },
  { value: 'nao_apoia', label: 'Não apoia' },
  { value: 'tentativa_sem_resposta', label: 'Sem resposta' },
  { value: 'numero_invalido', label: 'Número inválido' },
  { value: 'contato_invalido', label: 'Contato inválido' },
  { value: 'interrompido', label: 'Interrompido' },
  { value: 'concluido', label: 'Concluído' },
  { value: 'retorno_agendado', label: 'Retorno agendado' },
];

interface IndicatorFilterForm {
  periodo?: [dayjs.Dayjs, dayjs.Dayjs];
  atendente_usuario_id?: number;
  canal?: number;
  situacao?: string;
  resultado?: string;
}

export function ComunicacaoIndicadoresPage() {
  const [form] = Form.useForm<IndicatorFilterForm>();
  const [filters, setFilters] = useState<IndicatorFilterForm>({
    periodo: [dayjs().subtract(29, 'day').startOf('day'), dayjs().endOf('day')],
  });

  const params = useMemo(() => {
    return {
      inicio: filters.periodo?.[0]?.toISOString(),
      fim: filters.periodo?.[1]?.add(1, 'millisecond').toISOString(),
      atendente_usuario_id: filters.atendente_usuario_id,
      canal: filters.canal,
      situacao: filters.situacao,
      resultado: filters.resultado,
    };
  }, [filters]);

  const operatorParams = useMemo(
    () => ({
      inicio: params.inicio,
      fim: params.fim,
      canal: params.canal,
      situacao: params.situacao,
      resultado: params.resultado,
    }),
    [params.inicio, params.fim, params.canal, params.situacao, params.resultado],
  );

  const channels = useQuery({
    queryKey: ['comunicacao', 'atendimento', 'canais'],
    queryFn: listAttendanceChannels,
  });
  const channelOptions = useMemo(
    () => (channels.data ?? []).map((item) => ({ value: item.id, label: item.nome })),
    [channels.data],
  );

  const indicators = useQuery({
    queryKey: ['comunicacao', 'indicadores', params],
    queryFn: () => getAttendanceIndicators(params),
  });
  const operators = useQuery({
    queryKey: ['comunicacao', 'indicadores', 'operadores', operatorParams],
    queryFn: () => getAttendanceIndicators(operatorParams),
  });

  const data = indicators.data;

  return (
    <div className={styles.page}>
      <PageHeader
        title="Indicadores de comunicação"
        description="Conversão considera apenas atendimentos concluídos: votos confirmados ÷ concluídos × 100."
        breadcrumbs={[
          { label: 'Início', to: '/dashboard' },
          { label: 'Comunicação', to: '/comunicacao' },
          { label: 'Indicadores' },
        ]}
      />

      <Card size="small">
        <Form
          form={form}
          layout="vertical"
          initialValues={filters}
          onFinish={(values) => setFilters(values)}
        >
          <div className={styles.filters}>
            <Form.Item name="periodo" label="Período">
              <DatePicker.RangePicker allowClear={false} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="canal" label="Canal">
              <Select allowClear options={channelOptions} />
            </Form.Item>
            <Form.Item name="situacao" label="Situação">
              <Select allowClear options={statusOptions} />
            </Form.Item>
            <Form.Item name="resultado" label="Resultado">
              <Select allowClear options={resultOptions} />
            </Form.Item>
            <Form.Item name="atendente_usuario_id" label="Atendente">
              <Select
                allowClear
                showSearch
                optionFilterProp="label"
                options={(operators.data?.por_telefonista ?? []).map((item) => ({
                  value: item.atendente_usuario_id,
                  label: item.atendente_nome,
                }))}
              />
            </Form.Item>
            <div className={styles.filterActions}>
              <Button
                onClick={() => {
                  const next = {
                    periodo: [dayjs().subtract(29, 'day').startOf('day'), dayjs().endOf('day')] as [
                      dayjs.Dayjs,
                      dayjs.Dayjs,
                    ],
                  };
                  form.setFieldsValue({
                    ...next,
                    canal: undefined,
                    situacao: undefined,
                    resultado: undefined,
                    atendente_usuario_id: undefined,
                  });
                  setFilters(next);
                }}
              >
                Limpar
              </Button>
              <Button type="primary" htmlType="submit">
                Aplicar filtros
              </Button>
            </div>
          </div>
        </Form>
      </Card>

      {indicators.isError && (
        <Alert
          type="error"
          showIcon
          message="Não foi possível carregar os indicadores."
          description={normalizeApiError(indicators.error).message}
        />
      )}

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={8} xl={6}>
          <Card className={styles.summaryCard} loading={indicators.isPending}>
            <span className={`${styles.summaryIcon} ${styles.blue}`}>
              <PhoneOutlined />
            </span>
            <Statistic
              title="Total de atendimentos"
              value={data?.total_atendimentos ?? 0}
              formatter={(value) => formatInteger(Number(value))}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8} xl={6}>
          <Card className={styles.summaryCard} loading={indicators.isPending}>
            <span className={`${styles.summaryIcon} ${styles.green}`}>
              <CheckCircleOutlined />
            </span>
            <Statistic
              title="Contatos concluídos"
              value={data?.concluidos ?? 0}
              formatter={(value) => formatInteger(Number(value))}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8} xl={6}>
          <Card className={styles.summaryCard} loading={indicators.isPending}>
            <span className={`${styles.summaryIcon} ${styles.orange}`}>
              <StopOutlined />
            </span>
            <Statistic
              title="Sem resposta"
              value={data?.sem_resposta ?? 0}
              formatter={(value) => formatInteger(Number(value))}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8} xl={6}>
          <Card className={styles.summaryCard} loading={indicators.isPending}>
            <span className={`${styles.summaryIcon} ${styles.green}`}>
              <TeamOutlined />
            </span>
            <Statistic
              title="Votos confirmados"
              value={data?.votos_confirmados ?? 0}
              formatter={(value) => formatInteger(Number(value))}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8} xl={6}>
          <Card className={styles.summaryCard} loading={indicators.isPending}>
            <span className={`${styles.summaryIcon} ${styles.purple}`}>
              <UserOutlined />
            </span>
            <Statistic
              title="Eleitores indecisos"
              value={data?.indecisos ?? 0}
              formatter={(value) => formatInteger(Number(value))}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8} xl={6}>
          <Card className={styles.summaryCard} loading={indicators.isPending}>
            <span className={`${styles.summaryIcon} ${styles.red}`}>
              <CommentOutlined />
            </span>
            <Statistic
              title="Respostas negativas"
              value={data?.respostas_negativas ?? 0}
              formatter={(value) => formatInteger(Number(value))}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8} xl={6}>
          <Card className={styles.summaryCard} loading={indicators.isPending}>
            <span className={`${styles.summaryIcon} ${styles.blue}`}>
              <ClockCircleOutlined />
            </span>
            <Statistic
              title="Tempo médio (min)"
              value={data?.tempo_medio_minutos ?? 0}
              formatter={(value) => formatNumber(Number(value), 1, 1)}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={8} xl={6}>
          <Card className={styles.summaryCard} loading={indicators.isPending}>
            <span className={`${styles.summaryIcon} ${styles.green}`}>
              <BarChartOutlined />
            </span>
            <Statistic
              title="Conversão"
              value={data?.percentual_conversao ?? 0}
              formatter={(value) => formatPercent(Number(value))}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Atendimentos por período">
            <Table
              size="small"
              rowKey={(row) => String(row.periodo)}
              pagination={false}
              dataSource={data?.por_periodo ?? []}
              columns={[
                {
                  title: 'Data',
                  dataIndex: 'periodo',
                  render: (value: string) => dayjs(value).format('DD/MM/YYYY'),
                },
                {
                  title: 'Quantidade',
                  dataIndex: 'quantidade',
                  render: (value: number) => formatInteger(value),
                },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Atendimentos por telefonista">
            <Table
              size="small"
              rowKey={(row) => String(row.atendente_usuario_id)}
              pagination={false}
              dataSource={data?.por_telefonista ?? []}
              columns={[
                { title: 'Telefonista', dataIndex: 'atendente_nome' },
                {
                  title: 'Quantidade',
                  dataIndex: 'quantidade',
                  render: (value: number) => formatInteger(value),
                },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Atendimentos por canal">
            <Table
              size="small"
              rowKey={(row) => String(row.canal_id)}
              pagination={false}
              dataSource={data?.por_canal ?? []}
              columns={[
                {
                  title: 'Canal',
                  dataIndex: 'canal',
                },
                {
                  title: 'Quantidade',
                  dataIndex: 'quantidade',
                  render: (value: number) => formatInteger(value),
                },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Principais motivos de rejeição">
            <Table
              size="small"
              rowKey={(row) => row.motivo}
              pagination={false}
              dataSource={data?.principais_motivos_rejeicao ?? []}
              columns={[
                { title: 'Motivo', dataIndex: 'motivo' },
                {
                  title: 'Quantidade',
                  dataIndex: 'quantidade',
                  render: (value: number) => formatInteger(value),
                },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
