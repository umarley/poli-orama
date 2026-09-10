import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  CommentOutlined,
  PauseCircleOutlined,
  PhoneOutlined,
  StopOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Card, Col, DatePicker, Form, Row, Select, Space, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { ReactNode } from 'react';
import dayjs from 'dayjs';
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { LocalizedStatistic as Statistic } from '@/components/data/LocalizedStatistic';
import { PageHeader } from '@/components/layout/PageHeader';
import { getAttendanceReasonReport } from '@/modules/comunicacao/atendimento-service';
import type { AttendanceReportItem, AttendanceStatus, VoteIntention } from '@/modules/comunicacao/atendimento-types';
import { normalizeApiError } from '@/services/api/api-error';
import { formatInteger } from '@/utils/number-format';
import { formatPhoneContact } from '@/utils/phone-format';

import styles from './ComunicacaoPage.module.css';

const NO_REASON_ID = 0;

const statusLabels: Record<AttendanceStatus, string> = {
  em_atendimento: 'Em atendimento',
  concluido: 'Concluído',
  sem_resposta: 'Sem resposta',
  numero_invalido: 'Número inválido',
  interrompido: 'Interrompido',
};

const statusColors: Record<AttendanceStatus, string> = {
  em_atendimento: 'processing',
  concluido: 'success',
  sem_resposta: 'warning',
  numero_invalido: 'error',
  interrompido: 'default',
};

const intentionLabels: Record<VoteIntention, string> = {
  votara: 'Votará',
  nao_votara: 'Não votará',
  indeciso: 'Indeciso',
  nao_respondeu: 'Não respondeu',
};

const sexLabels: Record<string, string> = {
  F: 'Feminino',
  M: 'Masculino',
  O: 'Outro',
  N: 'Não informado',
};

interface ReportFilterForm {
  inicio?: dayjs.Dayjs | null;
  fim?: dayjs.Dayjs | null;
  motivo_rejeicao_id?: number;
}

function readDateParam(value: string | null): dayjs.Dayjs | undefined {
  if (!value) return undefined;
  const parsed = dayjs(value);
  return parsed.isValid() ? parsed : undefined;
}

function parseReasonId(value: string | undefined): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : NO_REASON_ID;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—';
  return dayjs(value).format('DD/MM/YYYY HH:mm');
}

function SummaryCard({
  title,
  value,
  icon,
  tone,
  loading,
}: {
  title: string;
  value: number;
  icon: ReactNode;
  tone: 'blue' | 'green' | 'orange' | 'purple' | 'red';
  loading: boolean;
}) {
  return (
    <Col xs={24} sm={12} lg={8} xl={6}>
      <Card className={styles.summaryCard} loading={loading}>
        <span className={`${styles.summaryIcon} ${styles[tone]}`}>{icon}</span>
        <Statistic title={title} value={value} formatter={(item) => formatInteger(Number(item))} />
      </Card>
    </Col>
  );
}

function formatPhone(value: string | null): string {
  if (!value) return '—';
  const digits = value.replace(/\D/g, '');
  const local = digits.startsWith('55') && digits.length > 11 ? digits.slice(2) : digits;
  return formatPhoneContact(local);
}

export function ComunicacaoMotivoRelatorioPage() {
  const { reasonId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [form] = Form.useForm<ReportFilterForm>();
  const [filters, setFilters] = useState<ReportFilterForm>({
    motivo_rejeicao_id: parseReasonId(reasonId),
    inicio: readDateParam(searchParams.get('inicio')) ?? dayjs().subtract(29, 'day').startOf('day'),
    fim: readDateParam(searchParams.get('fim')) ?? dayjs().endOf('day'),
  });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  useEffect(() => {
    const next = {
      motivo_rejeicao_id: parseReasonId(reasonId),
      inicio: readDateParam(searchParams.get('inicio')) ?? dayjs().subtract(29, 'day').startOf('day'),
      fim: readDateParam(searchParams.get('fim')) ?? dayjs().endOf('day'),
    };
    setFilters(next);
    form.setFieldsValue(next);
    setPage(1);
  }, [form, reasonId, searchParams]);

  const queryParams = useMemo(
    () => ({
      motivo_rejeicao_id:
        filters.motivo_rejeicao_id && filters.motivo_rejeicao_id > 0
          ? filters.motivo_rejeicao_id
          : null,
      inicio: filters.inicio?.startOf('day').toISOString(),
      fim: filters.fim?.endOf('day').add(1, 'millisecond').toISOString(),
      pagina: page,
      tamanho: pageSize,
    }),
    [filters, page, pageSize],
  );

  const report = useQuery({
    queryKey: ['comunicacao', 'indicadores', 'rejeicoes', queryParams],
    queryFn: () => getAttendanceReasonReport(queryParams),
  });

  const reasonOptions = useMemo(() => {
    const items = (report.data?.motivos ?? []).map((item) => ({
      motivo_rejeicao_id: item.motivo_rejeicao_id ?? NO_REASON_ID,
      motivo: item.motivo,
      quantidade: item.quantidade,
    }));
    const currentId = filters.motivo_rejeicao_id ?? NO_REASON_ID;
    if (report.data?.motivo && !items.some((item) => item.motivo_rejeicao_id === currentId)) {
      return [
        {
          motivo_rejeicao_id: currentId,
          motivo: report.data.motivo,
          quantidade: report.data.total,
        },
        ...items,
      ];
    }
    return items;
  }, [filters.motivo_rejeicao_id, report.data]);

  const persistNavigation = (next: ReportFilterForm) => {
    const params = new URLSearchParams();
    if (next.inicio) params.set('inicio', next.inicio.format('YYYY-MM-DD'));
    if (next.fim) params.set('fim', next.fim.format('YYYY-MM-DD'));
    const nextId = next.motivo_rejeicao_id ?? NO_REASON_ID;
    navigate(`/comunicacao/indicadores/motivo/${nextId}?${params.toString()}`, { replace: true });
  };

  const columns: ColumnsType<AttendanceReportItem> = [
    {
      title: 'Eleitor',
      dataIndex: 'nome_completo',
      render: (value: string, row) => (
        <Space direction="vertical" size={0}>
          <Link to={`/cadastro/pessoas/${row.pessoa_id}`}>{value}</Link>
          <Typography.Text type="secondary">{formatPhone(row.telefone)}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Telefonista',
      dataIndex: 'atendente_nome',
      render: (value: string | null) => value || '—',
    },
    {
      title: 'Início',
      dataIndex: 'iniciado_em',
      render: (value: string) => formatDateTime(value),
    },
    {
      title: 'Fim',
      dataIndex: 'finalizado_em',
      render: (value: string | null) => formatDateTime(value),
    },
    {
      title: 'Situação',
      dataIndex: 'situacao',
      render: (value: AttendanceStatus) => <Tag color={statusColors[value]}>{statusLabels[value]}</Tag>,
    },
    {
      title: 'Canal',
      dataIndex: 'canal_nome',
      render: (value: string | null, row) =>
        row.canal_outro ? `${value ?? 'Canal'} (${row.canal_outro})` : (value ?? '—'),
    },
    {
      title: 'Observação',
      dataIndex: 'observacao',
      ellipsis: true,
      render: (value: string | null) => value || '—',
    },
  ];

  return (
    <div className={styles.page}>
      <PageHeader
        title={report.data?.motivo ?? 'Atendimentos por motivo'}
        description="Relatório analítico dos atendimentos com intenção negativa e o motivo selecionado."
        breadcrumbs={[
          { label: 'Início', to: '/dashboard' },
          { label: 'Comunicação', to: '/comunicacao' },
          { label: 'Indicadores', to: '/comunicacao/indicadores' },
          { label: 'Motivo de rejeição' },
        ]}
        actions={
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/comunicacao/indicadores')}>
            Voltar
          </Button>
        }
      />

      <Card size="small">
        <Form
          form={form}
          layout="vertical"
          initialValues={filters}
          onFinish={(values) => {
            const next = {
              motivo_rejeicao_id: values.motivo_rejeicao_id ?? NO_REASON_ID,
              inicio: values.inicio ?? null,
              fim: values.fim ?? null,
            };
            setPage(1);
            setFilters(next);
            persistNavigation(next);
          }}
        >
          <div className={styles.filters}>
            <Form.Item
              name="motivo_rejeicao_id"
              label="Motivo"
              rules={[{ required: true, message: 'Selecione o motivo.' }]}
            >
              <Select
                showSearch
                optionFilterProp="label"
                options={reasonOptions.map((item) => ({
                  value: item.motivo_rejeicao_id,
                  label: `${item.motivo} (${item.quantidade})`,
                }))}
              />
            </Form.Item>
            <Form.Item name="inicio" label="Data inicial">
              <DatePicker allowClear={false} format="DD/MM/YYYY" style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="fim" label="Data final">
              <DatePicker allowClear={false} format="DD/MM/YYYY" style={{ width: '100%' }} />
            </Form.Item>
            <div className={styles.filterActions}>
              <Button type="primary" htmlType="submit">
                Aplicar filtros
              </Button>
            </div>
          </div>
        </Form>
      </Card>

      {report.isError && (
        <Alert
          type="error"
          showIcon
          message="Não foi possível carregar o relatório analítico."
          description={normalizeApiError(report.error).message}
        />
      )}

      <Row gutter={[16, 16]}>
        <SummaryCard
          title="Atendimentos"
          value={report.data?.resumo.total ?? report.data?.total ?? 0}
          icon={<PhoneOutlined />}
          tone="blue"
          loading={report.isPending}
        />
        <SummaryCard
          title="Concluídos"
          value={report.data?.resumo.concluido ?? 0}
          icon={<CheckCircleOutlined />}
          tone="green"
          loading={report.isPending}
        />
        <SummaryCard
          title="Número inválido"
          value={report.data?.resumo.numero_invalido ?? 0}
          icon={<StopOutlined />}
          tone="red"
          loading={report.isPending}
        />
        <SummaryCard
          title="Sem resposta"
          value={report.data?.resumo.sem_resposta ?? 0}
          icon={<PauseCircleOutlined />}
          tone="orange"
          loading={report.isPending}
        />
        <SummaryCard
          title="Interrompidos"
          value={report.data?.resumo.interrompido ?? 0}
          icon={<CloseCircleOutlined />}
          tone="purple"
          loading={report.isPending}
        />
        <SummaryCard
          title="Votará"
          value={report.data?.resumo.votara ?? 0}
          icon={<TeamOutlined />}
          tone="green"
          loading={report.isPending}
        />
        <SummaryCard
          title="Não votará"
          value={report.data?.resumo.nao_votara ?? 0}
          icon={<CommentOutlined />}
          tone="red"
          loading={report.isPending}
        />
        <SummaryCard
          title="Indecisos"
          value={report.data?.resumo.indeciso ?? 0}
          icon={<UserOutlined />}
          tone="purple"
          loading={report.isPending}
        />
        <SummaryCard
          title="Não respondeu"
          value={report.data?.resumo.nao_respondeu ?? 0}
          icon={<CommentOutlined />}
          tone="orange"
          loading={report.isPending}
        />
      </Row>

      <Card>
        <Table
          rowKey="id"
          size="small"
          loading={report.isPending}
          dataSource={report.data?.itens ?? []}
          columns={columns}
          expandable={{
            expandedRowRender: (row) => (
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                <Typography.Text>
                  <strong>E-mail:</strong> {row.email || '—'}
                </Typography.Text>
                <Typography.Text>
                  <strong>Nascimento:</strong>{' '}
                  {row.data_nascimento ? dayjs(row.data_nascimento).format('DD/MM/YYYY') : '—'}
                  {' · '}
                  <strong>Sexo:</strong> {row.sexo ? sexLabels[row.sexo] ?? row.sexo : '—'}
                </Typography.Text>
                <Typography.Text>
                  <strong>Resultado:</strong> {row.resultado || '—'}
                </Typography.Text>
                <Typography.Text>
                  <strong>Motivo de rejeição:</strong> {row.motivo_rejeicao_nome || 'Sem motivo'}
                </Typography.Text>
                {row.motivo_observacao ? (
                  <Typography.Text>
                    <strong>Complemento do motivo:</strong> {row.motivo_observacao}
                  </Typography.Text>
                ) : null}
                {row.motivo_encerramento ? (
                  <Typography.Text>
                    <strong>Motivo do encerramento:</strong> {row.motivo_encerramento}
                  </Typography.Text>
                ) : null}
                {row.motivo_inativacao ? (
                  <Typography.Text>
                    <strong>Motivo da inativação:</strong> {row.motivo_inativacao}
                  </Typography.Text>
                ) : null}
                <Typography.Text>
                  <strong>Observação:</strong> {row.observacao || '—'}
                </Typography.Text>
              </Space>
            ),
          }}
          pagination={{
            current: page,
            pageSize,
            total: report.data?.total ?? 0,
            showSizeChanger: true,
            showTotal: (total) => `${total} atendimento${total === 1 ? '' : 's'}`,
            onChange: (nextPage, nextSize) => {
              setPage(nextPage);
              setPageSize(nextSize);
            },
          }}
        />
      </Card>
    </div>
  );
}
