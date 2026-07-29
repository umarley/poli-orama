import { AlertOutlined, PlusOutlined, ReloadOutlined, TrophyOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  Col,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
} from 'antd';
import type { Dayjs } from 'dayjs';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { GoalProgress } from '@/components/metas/GoalProgress';
import { LocalizedStatistic as Statistic } from '@/components/data/LocalizedStatistic';
import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import { TerritorySelect } from '@/components/territorios/TerritorySelect';
import { listarLiderancas } from '@/modules/cadastro/pessoas-service';
import {
  criarMeta,
  criarPeriodo,
  criarTipoMeta,
  listarMetas,
  listarOpcoesAlvo,
  listarPeriodos,
  listarRanking,
  listarTiposMeta,
  obterResumoMetas,
  recalcularRanking,
} from '@/modules/metas/metas-service';
import type { GoalInput, GoalStatus, LeadershipRanking, TargetType } from '@/modules/metas/types';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';
import { formatInteger, formatNumber, formatPercent } from '@/utils/number-format';

interface GoalForm {
  titulo: string;
  tipo_meta_voto_id: number;
  periodo_meta_id: number;
  quantidade_meta: number;
  coordenador_id?: number;
  tipo_alvo?: TargetType;
  alvo_id?: number;
  quantidade_atribuida?: number;
}

interface PeriodForm {
  nome: string;
  datas: [Dayjs, Dayjs];
  ciclo?: string;
}

interface GoalFilters {
  territorio_id?: number;
  lideranca_id?: number;
  periodo_id?: number;
  status?: GoalStatus;
}

const targetLabels: Record<TargetType, string> = {
  lideranca: 'Liderança',
  territorio: 'Território',
  equipe: 'Equipe',
  comunidade: 'Comunidade',
  nucleo_familiar: 'Núcleo familiar',
  pessoa: 'Pessoa',
};

export function GoalsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const permissions = useSessionStore((state) => state.user?.permissions ?? []);
  const profiles = useSessionStore((state) => state.user?.profiles ?? []);
  const canCreate = permissions.includes('metas.criar');
  const canApprove = permissions.includes('metas.aprovar');
  const canAdminTypes = profiles.includes('gestor_saas');
  const [filters, setFilters] = useState<GoalFilters>({});
  const [goalModal, setGoalModal] = useState(false);
  const [periodModal, setPeriodModal] = useState(false);
  const [typeModal, setTypeModal] = useState(false);
  const [goalForm] = Form.useForm<GoalForm>();
  const [periodForm] = Form.useForm<PeriodForm>();
  const [typeForm] = Form.useForm<{ codigo: string; nome: string; descricao?: string }>();
  const targetType = Form.useWatch('tipo_alvo', goalForm);

  const goals = useQuery({
    queryKey: ['metas', filters],
    queryFn: () => listarMetas(filters),
  });
  const summary = useQuery({
    queryKey: ['metas', 'resumo', filters],
    queryFn: () => obterResumoMetas(filters),
  });
  const types = useQuery({ queryKey: ['metas', 'tipos'], queryFn: () => listarTiposMeta() });
  const periods = useQuery({
    queryKey: ['metas', 'periodos'],
    queryFn: () => listarPeriodos(),
  });
  const leaders = useQuery({
    queryKey: ['cadastro', 'liderancas'],
    queryFn: () => listarLiderancas(),
  });
  const ranking = useQuery({ queryKey: ['metas', 'ranking'], queryFn: listarRanking });
  const targetOptions = useQuery({
    queryKey: ['metas', 'alvos', targetType],
    queryFn: () => listarOpcoesAlvo(targetType!),
    enabled: Boolean(targetType),
  });

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['metas'] });
  };

  const createGoalMutation = useMutation({
    mutationFn: (values: GoalForm) => {
      const payload: GoalInput = {
        titulo: values.titulo,
        tipo_meta_voto_id: values.tipo_meta_voto_id,
        periodo_meta_id: values.periodo_meta_id,
        quantidade_meta: values.quantidade_meta,
        coordenador_id: values.coordenador_id,
        alvos:
          values.tipo_alvo && values.alvo_id
            ? [
                {
                  tipo_alvo: values.tipo_alvo,
                  alvo_id: values.alvo_id,
                  quantidade_atribuida: values.quantidade_atribuida,
                },
              ]
            : [],
      };
      return criarMeta(payload);
    },
    onSuccess: async (goal) => {
      AppToast.success('Meta criada.');
      setGoalModal(false);
      goalForm.resetFields();
      await refresh();
      navigate(`/metas/${goal.id}`);
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const createPeriodMutation = useMutation({
    mutationFn: (values: PeriodForm) =>
      criarPeriodo({
        nome: values.nome,
        data_inicio: values.datas[0].format('YYYY-MM-DD'),
        data_fim: values.datas[1].format('YYYY-MM-DD'),
        ciclo: values.ciclo,
      }),
    onSuccess: async () => {
      AppToast.success('Período criado.');
      setPeriodModal(false);
      periodForm.resetFields();
      await refresh();
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const createTypeMutation = useMutation({
    mutationFn: criarTipoMeta,
    onSuccess: async () => {
      AppToast.success('Tipo de meta criado.');
      setTypeModal(false);
      typeForm.resetFields();
      await refresh();
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const rankingMutation = useMutation({
    mutationFn: recalcularRanking,
    onSuccess: async () => {
      AppToast.success('Ranking recalculado.');
      await queryClient.invalidateQueries({ queryKey: ['metas', 'ranking'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  return (
    <div>
      <PageHeader
        title="Metas e votos"
        description="Defina metas, acompanhe projeções e identifique riscos operacionais."
        breadcrumbs={[{ label: 'Início', to: '/dashboard' }, { label: 'Metas' }]}
        actions={
          canCreate ? (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setGoalModal(true)}>
              Nova meta
            </Button>
          ) : undefined
        }
      />

      <Row gutter={[16, 16]} style={{ marginBottom: 20 }}>
        <Col xs={12} lg={6}>
          <Card>
            <Statistic title="Metas ativas" value={summary.data?.metas_ativas ?? 0} />
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card>
            <Statistic title="Atingidas" value={summary.data?.metas_atingidas ?? 0} />
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card>
            <Statistic
              title="Em risco"
              value={summary.data?.metas_em_risco ?? 0}
              prefix={<AlertOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card>
            <Statistic
              title="Atingimento geral"
              value={Number(summary.data?.percentual_geral ?? 0)}
              suffix="%"
              precision={1}
            />
          </Card>
        </Col>
      </Row>

      <Tabs
        items={[
          {
            key: 'goals',
            label: 'Metas',
            children: (
              <Card>
                <Form
                  layout="inline"
                  style={{ marginBottom: 16, rowGap: 12 }}
                  onValuesChange={(_, values) => setFilters(values as GoalFilters)}
                >
                  <Form.Item name="territorio_id">
                    <TerritorySelect style={{ width: 210 }} />
                  </Form.Item>
                  <Form.Item name="lideranca_id">
                    <Select
                      allowClear
                      placeholder="Liderança"
                      style={{ width: 180 }}
                      options={(leaders.data ?? []).map((item) => ({
                        value: item.id,
                        label: item.pessoa_nome_completo || `Liderança #${item.id}`,
                      }))}
                    />
                  </Form.Item>
                  <Form.Item name="periodo_id">
                    <Select
                      allowClear
                      placeholder="Período"
                      style={{ width: 180 }}
                      options={(periods.data ?? []).map((item) => ({
                        value: item.id,
                        label: item.nome,
                      }))}
                    />
                  </Form.Item>
                  <Form.Item name="status">
                    <Select
                      allowClear
                      placeholder="Status"
                      style={{ width: 150 }}
                      options={[
                        { value: 'ativa', label: 'Ativa' },
                        { value: 'em_risco', label: 'Em risco' },
                        { value: 'concluida', label: 'Concluída' },
                        { value: 'cancelada', label: 'Cancelada' },
                        { value: 'suspensa', label: 'Suspensa' },
                      ]}
                    />
                  </Form.Item>
                </Form>
                <Table
                  rowKey="id"
                  loading={goals.isPending}
                  dataSource={goals.data ?? []}
                  onRow={(item) => ({
                    onClick: () => navigate(`/metas/${item.id}`),
                    style: { cursor: 'pointer' },
                  })}
                  columns={[
                    {
                      title: 'Meta',
                      dataIndex: 'titulo',
                      render: (title: string, item) => (
                        <Space direction="vertical" size={0}>
                          <strong>{title}</strong>
                          <span>
                            {item.tipo_nome} · {item.periodo_nome}
                          </span>
                        </Space>
                      ),
                    },
                    {
                      title: 'Progresso',
                      width: 300,
                      render: (_, item) => (
                        <GoalProgress
                          compact
                          current={item.quantidade_atual}
                          target={item.quantidade_meta}
                          percentage={Number(item.percentual)}
                          atRisk={item.em_risco}
                        />
                      ),
                    },
                    {
                      title: 'Base vinculada',
                      dataIndex: 'quantidade_eleitores_vinculados',
                      render: (value: number) => formatInteger(value),
                    },
                    {
                      title: 'Situação',
                      render: (_, item) => (
                        <Tag color={item.em_risco ? 'error' : 'success'}>
                          {item.em_risco ? '⚠ Em risco' : item.status}
                        </Tag>
                      ),
                    },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: 'ranking',
            label: 'Ranking',
            children: (
              <Card
                title={
                  <Space>
                    <TrophyOutlined /> Ranking de lideranças
                  </Space>
                }
                extra={
                  canApprove && (
                    <Button
                      icon={<ReloadOutlined />}
                      loading={rankingMutation.isPending}
                      onClick={() => rankingMutation.mutate()}
                    >
                      Recalcular
                    </Button>
                  )
                }
              >
                <Table<LeadershipRanking>
                  rowKey="lideranca_id"
                  loading={ranking.isPending}
                  dataSource={ranking.data ?? []}
                  columns={[
                    { title: '#', dataIndex: 'posicao', width: 60 },
                    { title: 'Liderança', dataIndex: 'nome_lideranca' },
                    {
                      title: 'Cadastros',
                      dataIndex: 'total_cadastros',
                      render: (value: number) => formatInteger(value),
                    },
                    {
                      title: 'Meta',
                      render: (_, item) =>
                        `${formatInteger(item.quantidade_atual)} / ${formatInteger(item.quantidade_meta)}`,
                    },
                    {
                      title: 'Atingimento',
                      render: (_, item) => formatPercent(item.percentual_meta),
                    },
                    {
                      title: 'Pontuação',
                      dataIndex: 'pontuacao',
                      render: (value: number | string) => formatNumber(value),
                    },
                    {
                      title: 'Risco',
                      render: (_, item) =>
                        item.em_risco ? <Tag color="error">⚠ Em risco</Tag> : <Tag>Normal</Tag>,
                    },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: 'periods',
            label: 'Períodos',
            children: (
              <Card
                title="Períodos de meta"
                extra={
                  canCreate && (
                    <Button icon={<PlusOutlined />} onClick={() => setPeriodModal(true)}>
                      Novo período
                    </Button>
                  )
                }
              >
                <Table
                  rowKey="id"
                  pagination={false}
                  dataSource={periods.data ?? []}
                  columns={[
                    { title: 'Nome', dataIndex: 'nome' },
                    { title: 'Início', dataIndex: 'data_inicio' },
                    { title: 'Fim', dataIndex: 'data_fim' },
                    { title: 'Ciclo', dataIndex: 'ciclo' },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: 'types',
            label: 'Tipos',
            children: (
              <Card
                title="Tipos de meta"
                extra={
                  canAdminTypes && (
                    <Button icon={<PlusOutlined />} onClick={() => setTypeModal(true)}>
                      Novo tipo
                    </Button>
                  )
                }
              >
                <Table
                  rowKey="id"
                  pagination={false}
                  dataSource={types.data ?? []}
                  columns={[
                    { title: 'Nome', dataIndex: 'nome' },
                    { title: 'Código', dataIndex: 'codigo' },
                    {
                      title: 'Origem',
                      dataIndex: 'tenant_id',
                      render: (value: number | null) => (value ? 'Tenant' : 'Sistema'),
                    },
                  ]}
                />
              </Card>
            ),
          },
        ]}
      />

      <Modal
        open={goalModal}
        title="Nova meta"
        okText="Criar meta"
        width={680}
        confirmLoading={createGoalMutation.isPending}
        onCancel={() => setGoalModal(false)}
        onOk={() => goalForm.validateFields().then((values) => createGoalMutation.mutate(values))}
      >
        <Form form={goalForm} layout="vertical">
          <Form.Item name="titulo" label="Título" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="tipo_meta_voto_id" label="Tipo" rules={[{ required: true }]}>
                <Select
                  options={(types.data ?? []).map((item) => ({
                    value: item.id,
                    label: item.nome,
                  }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="periodo_meta_id" label="Período" rules={[{ required: true }]}>
                <Select
                  options={(periods.data ?? []).map((item) => ({
                    value: item.id,
                    label: item.nome,
                  }))}
                />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="quantidade_meta" label="Quantidade da meta" rules={[{ required: true }]}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="coordenador_id" label="Responsável">
            <Select
              allowClear
              options={(leaders.data ?? [])
                .filter((item) => item.tipo_lideranca.startsWith('coordenador_'))
                .map((item) => ({
                  value: item.id,
                  label: item.pessoa_nome_completo || `Liderança #${item.id}`,
                }))}
            />
          </Form.Item>
          <Row gutter={12}>
            <Col span={10}>
              <Form.Item name="tipo_alvo" label="Tipo de alvo">
                <Select
                  allowClear
                  options={Object.entries(targetLabels).map(([value, label]) => ({
                    value,
                    label,
                  }))}
                  onChange={() => goalForm.setFieldValue('alvo_id', undefined)}
                />
              </Form.Item>
            </Col>
            <Col span={14}>
              <Form.Item name="alvo_id" label="Alvo">
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  disabled={!targetType}
                  loading={targetOptions.isPending}
                  options={(targetOptions.data ?? []).map((item) => ({
                    value: item.id,
                    label: item.nome,
                  }))}
                />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      <Modal
        open={periodModal}
        title="Novo período"
        okText="Criar"
        confirmLoading={createPeriodMutation.isPending}
        onCancel={() => setPeriodModal(false)}
        onOk={() =>
          periodForm.validateFields().then((values) => createPeriodMutation.mutate(values))
        }
      >
        <Form form={periodForm} layout="vertical">
          <Form.Item name="nome" label="Nome" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="datas" label="Período" rules={[{ required: true }]}>
            <DatePicker.RangePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="ciclo" label="Ciclo">
            <Input placeholder="Mensal, trimestral, campanha..." />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={typeModal}
        title="Novo tipo de meta"
        okText="Criar"
        confirmLoading={createTypeMutation.isPending}
        onCancel={() => setTypeModal(false)}
        onOk={() => typeForm.validateFields().then((values) => createTypeMutation.mutate(values))}
      >
        <Form form={typeForm} layout="vertical">
          <Form.Item name="nome" label="Nome" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="codigo"
            label="Código"
            rules={[
              { required: true },
              { pattern: /^[a-z0-9_]+$/, message: 'Use letras minúsculas, números e _.' },
            ]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="descricao" label="Descrição">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
