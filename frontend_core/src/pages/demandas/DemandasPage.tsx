import { DownloadOutlined, PlusOutlined, WarningOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  Col,
  DatePicker,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import type { Dayjs } from 'dayjs';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import { buscarPessoas, listarLiderancas } from '@/modules/cadastro/pessoas-service';
import {
  classifyDemand,
  createDemand,
  downloadDemands,
  listDemandCatalog,
  listDemandResponsibles,
  listDemands,
} from '@/modules/demandas/demandas-service';
import type { DemandFilters } from '@/modules/demandas/types';
import { listarTerritorios } from '@/modules/territorios/territorios-service';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';

interface DemandForm {
  titulo?: string;
  descricao: string;
  pessoa_solicitante_id?: number;
  lideranca_indicacao_id?: number;
  territorio_id: number;
  categoria_demanda_id: number;
  prioridade_demanda_id?: number;
  origem_demanda_id: number;
  prazo?: Dayjs;
}

export function DemandasPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const permissions = useSessionStore((state) => state.user?.permissions ?? []);
  const [filters, setFilters] = useState<DemandFilters>({});
  const [open, setOpen] = useState(false);
  const [personQuery, setPersonQuery] = useState('');
  const [form] = Form.useForm<DemandForm>();
  const demands = useQuery({
    queryKey: ['demandas', 'lista', filters],
    queryFn: () => listDemands(filters),
  });
  const useCatalog = (key: 'categorias' | 'status' | 'prioridades' | 'origens') =>
    useQuery({
      queryKey: ['demandas', 'catalogo', key],
      queryFn: () => listDemandCatalog(key),
    });
  const categories = useCatalog('categorias');
  const statuses = useCatalog('status');
  const priorities = useCatalog('prioridades');
  const origins = useCatalog('origens');
  const responsibles = useQuery({
    queryKey: ['demandas', 'responsaveis'],
    queryFn: listDemandResponsibles,
  });
  const territories = useQuery({
    queryKey: ['territorios', 'demandas'],
    queryFn: () => listarTerritorios(),
  });
  const leaderships = useQuery({
    queryKey: ['cadastro', 'liderancas', 'demandas'],
    queryFn: () => listarLiderancas(),
  });
  const people = useQuery({
    queryKey: ['cadastro', 'pessoas', 'demandas', personQuery],
    queryFn: () => buscarPessoas(personQuery),
    enabled: personQuery.trim().length >= 2,
  });
  const creation = useMutation({
    mutationFn: (values: DemandForm) =>
      createDemand({ ...values, prazo: values.prazo?.format('YYYY-MM-DD') }),
    onSuccess: async (item) => {
      AppToast.success('Demanda criada.');
      setOpen(false);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['demandas'] });
      navigate(`/demandas/${item.id}`);
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const classification = useMutation({
    mutationFn: classifyDemand,
    onSuccess: (suggestion) => {
      const current = form.getFieldsValue();
      form.setFieldsValue({
        categoria_demanda_id:
          current.categoria_demanda_id ?? suggestion.categoria_demanda_id ?? undefined,
        prioridade_demanda_id:
          current.prioridade_demanda_id ?? suggestion.prioridade_demanda_id ?? undefined,
      });
      if (suggestion.categoria_demanda_id || suggestion.prioridade_demanda_id) {
        AppToast.info('Categoria ou prioridade sugerida a partir da descrição.');
      }
    },
  });
  const exporting = useMutation({
    mutationFn: () => downloadDemands(filters),
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const options = (items: Array<{ id: number; nome: string }> | undefined) =>
    (items ?? []).map(({ id, nome }) => ({ value: id, label: nome }));

  return (
    <div>
      <PageHeader
        title="Demandas"
        description="Solicitações, responsáveis, prazos e resultados de atendimento."
        breadcrumbs={[{ label: 'Início', to: '/dashboard' }, { label: 'Demandas' }]}
        actions={
          <Space>
            {permissions.includes('demandas.exportar') && (
              <Button
                icon={<DownloadOutlined />}
                loading={exporting.isPending}
                onClick={() => exporting.mutate()}
              >
                Exportar
              </Button>
            )}
            {permissions.includes('demandas.criar') && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
                Nova demanda
              </Button>
            )}
          </Space>
        }
      />
      <Card style={{ marginBottom: 16 }} aria-label="Filtros de demandas">
        <Row gutter={[12, 12]}>
          {[
            ['Status', 'status', statuses.data],
            ['Categoria', 'categoria', categories.data],
            ['Responsável', 'responsavel', responsibles.data],
            ['Território', 'territorio', territories.data],
          ].map(([label, key, data]) => (
            <Col xs={24} md={6} key={String(key)}>
              <Select
                allowClear
                placeholder={String(label)}
                style={{ width: '100%' }}
                options={options(data as Array<{ id: number; nome: string }> | undefined)}
                onChange={(value) => setFilters((old) => ({ ...old, [String(key)]: value }))}
              />
            </Col>
          ))}
        </Row>
      </Card>
      <Card>
        <Table
          rowKey="id"
          loading={demands.isLoading}
          dataSource={demands.data ?? []}
          onRow={(item) => ({
            onClick: () => navigate(`/demandas/${item.id}`),
            style: { cursor: 'pointer' },
          })}
          columns={[
            { title: 'Protocolo', dataIndex: 'protocolo' },
            { title: 'Título', dataIndex: 'titulo' },
            { title: 'Categoria', dataIndex: 'categoria_nome' },
            { title: 'Status', dataIndex: 'status_nome' },
            { title: 'Responsável', dataIndex: 'responsavel_nome' },
            {
              title: 'Prazo',
              render: (_, item) =>
                item.vencida ? (
                  <Typography.Text strong type="danger">
                    <WarningOutlined /> Vencida — {item.prazo}
                  </Typography.Text>
                ) : (
                  item.prazo || 'Sem prazo'
                ),
            },
            {
              title: 'Prioridade',
              render: (_, item) => item.prioridade_nome && <Tag>{item.prioridade_nome}</Tag>,
            },
          ]}
        />
      </Card>
      <Modal
        open={open}
        title="Nova demanda"
        okText="Criar demanda"
        confirmLoading={creation.isPending}
        onCancel={() => setOpen(false)}
        onOk={() => form.submit()}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={(values) => creation.mutate(values)}>
          <Form.Item name="titulo" label="Título">
            <Input />
          </Form.Item>
          <Form.Item name="descricao" label="Descrição" rules={[{ required: true }]}>
            <Input.TextArea
              rows={4}
              onBlur={(event) => {
                const description = event.target.value.trim();
                if (description.length >= 2) classification.mutate(description);
              }}
            />
          </Form.Item>
          <Form.Item name="pessoa_solicitante_id" label="Solicitante">
            <Select
              showSearch
              allowClear
              filterOption={false}
              onSearch={setPersonQuery}
              options={(people.data ?? []).map((item) => ({
                value: item.id,
                label: item.nome_completo,
              }))}
              notFoundContent="Digite ao menos dois caracteres"
            />
          </Form.Item>
          <Form.Item name="lideranca_indicacao_id" label="Liderança indicadora">
            <Select
              allowClear
              options={(leaderships.data ?? []).map((item) => ({
                value: item.id,
                label: item.pessoa_nome_completo || `Liderança #${item.id}`,
              }))}
            />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="categoria_demanda_id" label="Categoria" rules={[{ required: true }]}>
                <Select options={options(categories.data)} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="origem_demanda_id" label="Origem" rules={[{ required: true }]}>
                <Select options={options(origins.data)} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="territorio_id" label="Território" rules={[{ required: true }]}>
                <Select options={options(territories.data)} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="prioridade_demanda_id" label="Prioridade">
                <Select allowClear options={options(priorities.data)} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="prazo" label="Prazo">
            <DatePicker format="DD/MM/YYYY" style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
