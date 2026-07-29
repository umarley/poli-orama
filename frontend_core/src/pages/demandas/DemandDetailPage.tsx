import { EditOutlined, PlusOutlined, UserSwitchOutlined, WarningOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  DatePicker,
  Descriptions,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { AttachmentsPanel } from '@/components/arquivos/AttachmentsPanel';
import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  addDemandAttendance,
  changeDemandStatus,
  getDemand,
  listDemandCatalog,
  listDemandResponsibles,
  updateDemand,
} from '@/modules/demandas/demandas-service';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';

type ModalKind = 'status' | 'assign' | 'attendance' | null;

export function DemandDetailPage() {
  const id = Number(useParams().id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const permissions = useSessionStore((state) => state.user?.permissions ?? []);
  const [modal, setModal] = useState<ModalKind>(null);
  const [form] = Form.useForm();
  const demand = useQuery({
    queryKey: ['demandas', id],
    queryFn: () => getDemand(id),
    enabled: id > 0,
  });
  const statuses = useQuery({
    queryKey: ['demandas', 'catalogo', 'status'],
    queryFn: () => listDemandCatalog('status'),
  });
  const results = useQuery({
    queryKey: ['demandas', 'catalogo', 'resultados'],
    queryFn: () => listDemandCatalog('resultados'),
  });
  const responsibles = useQuery({
    queryKey: ['demandas', 'responsaveis'],
    queryFn: listDemandResponsibles,
  });
  const action = useMutation({
    mutationFn: async (values: Record<string, unknown>) => {
      if (modal === 'status') {
        return changeDemandStatus(id, {
          status_demanda_id: Number(values.status_demanda_id),
          resultado_atendimento_id: values.resultado_atendimento_id
            ? Number(values.resultado_atendimento_id)
            : undefined,
          observacao: String(values.observacao),
        });
      }
      if (modal === 'assign') {
        const prazo = values.prazo as Dayjs | undefined;
        return updateDemand(id, {
          responsavel_atendimento_id: values.responsavel_atendimento_id,
          prazo: prazo?.format('YYYY-MM-DD'),
          observacao: values.observacao,
        });
      }
      const prazo = values.prazo as Dayjs | undefined;
      const execution = values.data_execucao as Dayjs | undefined;
      return addDemandAttendance(id, {
        ...values,
        prazo: prazo?.format('YYYY-MM-DD'),
        data_execucao: execution?.format('YYYY-MM-DD'),
      });
    },
    onSuccess: async () => {
      AppToast.success('Demanda atualizada.');
      setModal(null);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['demandas'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const item = demand.data;
  const options = (values: Array<{ id: number; nome: string }> | undefined) =>
    (values ?? []).map(({ id: value, nome: label }) => ({ value, label }));

  return (
    <div>
      <PageHeader
        title={item?.titulo || item?.protocolo || 'Demanda'}
        description={item?.protocolo ?? 'Carregando demanda'}
        breadcrumbs={[
          { label: 'Início', to: '/dashboard' },
          { label: 'Demandas', to: '/demandas' },
          { label: item?.protocolo ?? `#${id}` },
        ]}
        actions={
          permissions.includes('demandas.editar') && (
            <Space>
              <Button icon={<EditOutlined />} onClick={() => setModal('status')}>
                Alterar status
              </Button>
              <Button icon={<UserSwitchOutlined />} onClick={() => setModal('assign')}>
                Atribuir
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setModal('attendance')}>
                Registrar atendimento
              </Button>
            </Space>
          )
        }
      />
      {item?.vencida && (
        <Card style={{ marginBottom: 16, borderColor: '#ff4d4f' }}>
          <Typography.Text strong type="danger">
            <WarningOutlined /> Prazo vencido em {item.prazo}. Esta demanda requer atenção.
          </Typography.Text>
        </Card>
      )}
      <Tabs
        items={[
          {
            key: 'data',
            label: 'Dados',
            children: (
              <Card loading={demand.isLoading}>
                <Descriptions bordered column={{ xs: 1, md: 2 }}>
                  <Descriptions.Item label="Status">
                    <Tag>{item?.status_nome}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Categoria">
                    {item?.categoria_nome || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Solicitante">
                    {item?.solicitante_nome || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Território">
                    {item?.territorio_nome || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Responsável">
                    {item?.responsavel_nome || 'Não atribuído'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Prazo">{item?.prazo || 'Sem prazo'}</Descriptions.Item>
                  <Descriptions.Item label="Resultado">
                    {item?.resultado_nome || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Descrição" span={2}>
                    {item?.descricao}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            ),
          },
          {
            key: 'attendance',
            label: `Atendimentos (${item?.atendimentos.length ?? 0})`,
            children: (
              <Table
                rowKey={(row) => String(row.id)}
                dataSource={item?.atendimentos ?? []}
                columns={[
                  { title: 'Data', dataIndex: 'data_execucao' },
                  { title: 'Responsável', dataIndex: 'responsavel_nome' },
                  { title: 'Descrição', dataIndex: 'descricao' },
                  { title: 'Resultado', dataIndex: 'resultado_nome' },
                ]}
              />
            ),
          },
          {
            key: 'movements',
            label: `Movimentações (${item?.movimentacoes.length ?? 0})`,
            children: (
              <Table
                rowKey={(row) => String(row.id)}
                dataSource={item?.movimentacoes ?? []}
                columns={[
                  { title: 'Data', dataIndex: 'criado_em' },
                  { title: 'Observação', dataIndex: 'observacao' },
                  { title: 'Usuário', dataIndex: 'usuario_id' },
                  { title: 'Status anterior', dataIndex: 'status_anterior_id' },
                  { title: 'Status novo', dataIndex: 'status_novo_id' },
                ]}
              />
            ),
          },
          {
            key: 'attachments',
            label: 'Anexos',
            children: (
              <AttachmentsPanel
                entity="demanda"
                entityId={id}
                allowedTypeCodes={['comprovante', 'documento_pessoal', 'imagem', 'pdf']}
                canEdit={permissions.includes('demandas.editar')}
              />
            ),
          },
        ]}
      />
      <Modal
        open={modal !== null}
        title={
          modal === 'status'
            ? 'Alterar status'
            : modal === 'assign'
              ? 'Atribuir responsável e prazo'
              : 'Registrar atendimento'
        }
        okText="Salvar"
        confirmLoading={action.isPending}
        onCancel={() => setModal(null)}
        onOk={() => form.submit()}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={(values) => action.mutate(values)}>
          {modal === 'status' && (
            <>
              <Form.Item name="status_demanda_id" label="Novo status" rules={[{ required: true }]}>
                <Select options={options(statuses.data)} />
              </Form.Item>
              <Form.Item name="resultado_atendimento_id" label="Resultado">
                <Select allowClear options={options(results.data)} />
              </Form.Item>
              <Form.Item name="observacao" label="Observação" rules={[{ required: true, min: 3 }]}>
                <Input.TextArea />
              </Form.Item>
            </>
          )}
          {modal === 'assign' && (
            <>
              <Form.Item
                name="responsavel_atendimento_id"
                label="Responsável"
                rules={[{ required: true }]}
              >
                <Select options={options(responsibles.data)} />
              </Form.Item>
              <Form.Item
                name="prazo"
                label="Prazo"
                initialValue={item?.prazo ? dayjs(item.prazo) : undefined}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="observacao" label="Observação">
                <Input.TextArea />
              </Form.Item>
            </>
          )}
          {modal === 'attendance' && (
            <>
              <Form.Item name="responsavel_atendimento_id" label="Responsável">
                <Select allowClear options={options(responsibles.data)} />
              </Form.Item>
              <Form.Item name="data_execucao" label="Data" initialValue={dayjs()}>
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="resultado_atendimento_id" label="Resultado">
                <Select allowClear options={options(results.data)} />
              </Form.Item>
              <Form.Item
                name="descricao"
                label="Ação realizada"
                rules={[{ required: true, min: 2 }]}
              >
                <Input.TextArea />
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>
      <Button type="link" onClick={() => navigate('/demandas')}>
        Voltar para demandas
      </Button>
    </div>
  );
}
