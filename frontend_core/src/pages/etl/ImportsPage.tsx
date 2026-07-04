import { InboxOutlined, PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  Col,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Upload,
} from 'antd';
import type { UploadFile } from 'antd';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  createImport,
  listImports,
  listSources,
} from '@/modules/etl/etl-service';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';

interface UploadForm {
  fonte_dado_id: number;
  descricao?: string;
  separador?: string;
  aba?: string;
  arquivo: UploadFile[];
}

const statusColors: Record<string, string> = {
  pendente: 'default',
  processando: 'processing',
  parcial: 'warning',
  concluida: 'success',
  falha: 'error',
  cancelada: 'default',
};

export function ImportsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const canCreate = useSessionStore((state) =>
    state.user?.permissions.includes('etl.criar'),
  );
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm<UploadForm>();
  const imports = useQuery({
    queryKey: ['etl', 'importacoes'],
    queryFn: listImports,
    refetchInterval: (query) =>
      query.state.data?.some((item) => item.status === 'processando') ? 3000 : false,
  });
  const sources = useQuery({ queryKey: ['etl', 'fontes'], queryFn: listSources });
  const upload = useMutation({
    mutationFn: (values: UploadForm) => {
      const selected = values.arquivo[0]?.originFileObj;
      if (!selected) throw new Error('Selecione um arquivo.');
      return createImport({
        file: selected,
        sourceId: values.fonte_dado_id,
        description: values.descricao,
        parameters: {
          separador: values.separador || undefined,
          aba: values.aba || undefined,
        },
      });
    },
    onSuccess: async (item) => {
      AppToast.success('Importação enviada para validação.');
      setModalOpen(false);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['etl'] });
      navigate(`/importacoes/${item.id}`);
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const data = imports.data ?? [];
  return (
    <div>
      <PageHeader
        title="Importações e qualidade"
        description="Valide, deduplique e aprove dados antes da carga no cadastro."
        breadcrumbs={[{ label: 'Início', to: '/dashboard' }, { label: 'Importações' }]}
        actions={
          canCreate ? (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
              Nova importação
            </Button>
          ) : undefined
        }
      />
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} lg={6}><Card><Statistic title="Importações" value={data.length} /></Card></Col>
        <Col xs={12} lg={6}>
          <Card><Statistic title="Processando" value={data.filter((item) => item.status === 'processando').length} /></Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card><Statistic title="Com erros" value={data.reduce((sum, item) => sum + item.linhas_erro, 0)} /></Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card><Statistic title="Carregadas" value={data.reduce((sum, item) => sum + item.linhas_carregadas, 0)} /></Card>
        </Col>
      </Row>
      <Card>
        <Table
          rowKey="id"
          loading={imports.isPending}
          dataSource={data}
          onRow={(item) => ({
            onClick: () => navigate(`/importacoes/${item.id}`),
            style: { cursor: 'pointer' },
          })}
          columns={[
            {
              title: 'Arquivo',
              render: (_, item) => (
                <Space direction="vertical" size={0}>
                  <strong>{item.arquivo?.nome_arquivo || `Importação #${item.id}`}</strong>
                  <span>{item.fonte_nome}</span>
                </Space>
              ),
            },
            { title: 'Total', dataIndex: 'total_linhas' },
            { title: 'Válidas', dataIndex: 'linhas_validas' },
            { title: 'Erros', dataIndex: 'linhas_erro' },
            { title: 'Duplicadas', dataIndex: 'linhas_duplicadas' },
            {
              title: 'Status',
              dataIndex: 'status',
              render: (value: string) => <Tag color={statusColors[value]}>{value}</Tag>,
            },
          ]}
        />
      </Card>
      <Modal
        open={modalOpen}
        title="Nova importação"
        okText="Enviar e validar"
        confirmLoading={upload.isPending}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.validateFields().then((values) => upload.mutate(values))}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="fonte_dado_id" label="Fonte" rules={[{ required: true }]}>
            <Select options={(sources.data ?? []).map((item) => ({ value: item.id, label: item.nome }))} />
          </Form.Item>
          <Form.Item name="descricao" label="Descrição"><Input /></Form.Item>
          <Row gutter={12}>
            <Col span={12}><Form.Item name="separador" label="Separador CSV"><Input placeholder="Automático" maxLength={1} /></Form.Item></Col>
            <Col span={12}><Form.Item name="aba" label="Aba Excel"><Input placeholder="Primeira aba" /></Form.Item></Col>
          </Row>
          <Form.Item
            name="arquivo"
            label="Arquivo CSV ou XLSX"
            valuePropName="fileList"
            getValueFromEvent={(event) => event?.fileList}
            rules={[{ required: true }]}
          >
            <Upload.Dragger beforeUpload={() => false} maxCount={1} accept=".csv,.xlsx">
              <InboxOutlined style={{ fontSize: 34 }} />
              <p>Arraste o arquivo ou clique para selecionar</p>
            </Upload.Dragger>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
