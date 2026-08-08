import { AlertOutlined, EditOutlined, StopOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Form,
  Input,
  Modal,
  Popconfirm,
  Row,
  Space,
  Table,
  Tag,
  Timeline,
  Typography,
} from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import { GoalProgress } from '@/components/metas/GoalProgress';
import { cancelarMeta, obterMeta, registrarAcompanhamento } from '@/modules/metas/metas-service';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';
import { formatInteger, formatNumber, formatPercent } from '@/utils/number-format';

interface TrackingForm {
  data_referencia: Dayjs;
  observacao?: string;
}

export function GoalDetailPage() {
  const { id } = useParams();
  const goalId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const canEdit = useSessionStore((state) => state.user?.permissions.includes('metas.editar'));
  const [trackingModal, setTrackingModal] = useState(false);
  const [form] = Form.useForm<TrackingForm>();
  const goal = useQuery({
    queryKey: ['metas', goalId],
    queryFn: () => obterMeta(goalId),
    enabled: Number.isInteger(goalId) && goalId > 0,
  });

  const trackingMutation = useMutation({
    mutationFn: (values: TrackingForm) =>
      registrarAcompanhamento(goalId, {
        data_referencia: values.data_referencia.format('YYYY-MM-DD'),
        observacao: values.observacao,
      }),
    onSuccess: async () => {
      AppToast.success('Acompanhamento registrado.');
      setTrackingModal(false);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['metas'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelarMeta(goalId),
    onSuccess: async () => {
      AppToast.success('Meta cancelada.');
      await queryClient.invalidateQueries({ queryKey: ['metas'] });
      navigate('/metas');
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  if (goal.error) {
    return <Alert type="error" showIcon message={normalizeApiError(goal.error).message} />;
  }
  const item = goal.data;
  return (
    <div>
      <PageHeader
        title={item?.titulo || 'Detalhe da meta'}
        description="Histórico, alvo, progresso, alertas e fatores de risco."
        breadcrumbs={[
          { label: 'Início', to: '/dashboard' },
          { label: 'Metas', to: '/metas' },
          { label: item?.titulo || 'Detalhe' },
        ]}
        actions={
          canEdit && item?.status !== 'cancelada' ? (
            <Space>
              <Button icon={<EditOutlined />} onClick={() => setTrackingModal(true)}>
                Registrar acompanhamento
              </Button>
              <Popconfirm
                title="Cancelar esta meta?"
                description="Metas canceladas deixam de participar dos cálculos ativos."
                onConfirm={() => cancelMutation.mutate()}
              >
                <Button danger icon={<StopOutlined />}>
                  Cancelar meta
                </Button>
              </Popconfirm>
            </Space>
          ) : undefined
        }
      />

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="Progresso" loading={goal.isPending}>
            {item && (
              <GoalProgress
                current={item.quantidade_atual}
                target={item.quantidade_meta}
                percentage={Number(item.percentual)}
                atRisk={item.em_risco}
              />
            )}
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="Risco preditivo" loading={goal.isPending}>
            {item && (
              <Space direction="vertical">
                <Typography.Title level={2}>
                  {formatNumber(item.score_risco, 1, 1)}
                </Typography.Title>
                <Tag color={item.em_risco ? 'error' : 'success'}>
                  {item.em_risco ? '⚠ Requer atenção' : 'Dentro do esperado'}
                </Tag>
                <Typography.Text type="secondary">
                  Modelo: {String(item.fatores_risco.modelo || 'heurística')}
                </Typography.Text>
              </Space>
            )}
          </Card>
        </Col>
      </Row>

      <Card title="Dados da meta" style={{ marginTop: 16 }} loading={goal.isPending}>
        {item && (
          <Descriptions column={{ xs: 1, md: 2, lg: 3 }}>
            <Descriptions.Item label="Tipo">{item.tipo_nome}</Descriptions.Item>
            <Descriptions.Item label="Campanha">{item.campanha_nome}</Descriptions.Item>
            <Descriptions.Item label="Status">{item.status}</Descriptions.Item>
            <Descriptions.Item label="Base vinculada">
              {formatInteger(item.quantidade_eleitores_vinculados)}
            </Descriptions.Item>
            <Descriptions.Item label="Alvos">
              {item.alvos.map((target) => target.nome_alvo || `#${target.alvo_id}`).join(', ') ||
                'Campanha inteira'}
            </Descriptions.Item>
            <Descriptions.Item label="Situação">{item.situacao_risco}</Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} xl={14}>
          <Card title="Histórico de acompanhamento">
            <Table
              rowKey="id"
              pagination={false}
              dataSource={item?.acompanhamentos ?? []}
              columns={[
                {
                  title: 'Data',
                  dataIndex: 'data_referencia',
                  render: (value: string) => dayjs(value).format('DD/MM/YYYY'),
                },
                {
                  title: 'Projetada',
                  dataIndex: 'quantidade_projetada',
                  render: (value: number | null) => (value == null ? '—' : formatInteger(value)),
                },
                {
                  title: 'Confirmada',
                  dataIndex: 'quantidade_confirmada',
                  render: (value: number | null) => (value == null ? '—' : formatInteger(value)),
                },
                {
                  title: '%',
                  dataIndex: 'percentual_atingido',
                  render: (value: string) => formatPercent(value),
                },
                { title: 'Risco', dataIndex: 'situacao_risco' },
                { title: 'Observação', dataIndex: 'observacao' },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} xl={10}>
          <Card
            title={
              <Space>
                <AlertOutlined /> Alertas
              </Space>
            }
          >
            {item?.alertas.length ? (
              <Timeline
                items={item.alertas.map((alert) => ({
                  color: alert.resolvido ? 'green' : 'red',
                  children: (
                    <div>
                      <strong>{alert.resolvido ? 'Resolvido' : 'Aberto'}</strong>
                      <p>{alert.mensagem}</p>
                    </div>
                  ),
                }))}
              />
            ) : (
              <Typography.Text type="secondary">Nenhum alerta registrado.</Typography.Text>
            )}
          </Card>
        </Col>
      </Row>

      <Modal
        open={trackingModal}
        title="Registrar acompanhamento"
        okText="Salvar"
        confirmLoading={trackingMutation.isPending}
        onCancel={() => setTrackingModal(false)}
        onOk={() => form.validateFields().then((values) => trackingMutation.mutate(values))}
      >
        <Form form={form} layout="vertical" initialValues={{ data_referencia: dayjs() }}>
          <Form.Item name="data_referencia" label="Data" rules={[{ required: true }]}>
            <DatePicker format="DD/MM/YYYY" style={{ width: '100%' }} />
          </Form.Item>
          <Alert
            type="info"
            showIcon
            message="Projeção e confirmação são calculadas automaticamente"
            description="A projeção considera os liderados ativos e a confirmação considera as declarações registradas pelo Call Center."
            style={{ marginBottom: 16 }}
          />
          <Form.Item name="observacao" label="Observação">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Alert
            type="info"
            showIcon
            message="Confirmação operacional não representa comprovação oficial de voto."
          />
        </Form>
      </Modal>
    </div>
  );
}
