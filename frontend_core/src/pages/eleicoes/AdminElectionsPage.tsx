import { EditOutlined, PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  Select,
  Switch,
  Tag,
} from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { useState } from 'react';

import { BaseTable } from '@/components/data/BaseTable';
import { AppToast } from '@/components/feedback/AppToast';
import { BaseModal } from '@/components/feedback/BaseModal';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  createOfficialElection,
  listOfficialElections,
  updateOfficialElection,
} from '@/modules/eleicoes/eleicoes-service';
import type {
  ElectionType,
  OfficialElection,
  OfficialElectionInput,
} from '@/modules/eleicoes/types';
import { normalizeApiError } from '@/services/api/api-error';

interface ElectionForm
  extends Omit<
    OfficialElectionInput,
    'ano' | 'data_eleicao' | 'codigo_uf_ibge' | 'codigo_municipio_ibge'
  > {
  data_eleicao: Dayjs;
}

const typeLabels: Record<ElectionType, string> = {
  municipal: 'Eleições municipais',
  estadual: 'Estadual',
  federal: 'Eleições gerais',
  suplementar: 'Suplementar',
  outra: 'Outra',
};

const officialElectionTypeOptions = [
  { value: 'federal' satisfies ElectionType, label: 'Eleições gerais' },
  { value: 'municipal' satisfies ElectionType, label: 'Eleições municipais' },
];

export function AdminElectionsPage() {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<OfficialElection | null>(null);
  const [form] = Form.useForm<ElectionForm>();
  const electionType = Form.useWatch('tipo', form);

  const elections = useQuery({
    queryKey: ['official-elections', true],
    queryFn: () => listOfficialElections(true),
  });
  const save = useMutation({
    mutationFn: (values: ElectionForm) => {
      const payload: OfficialElectionInput = {
        ...values,
        ano: values.data_eleicao.year(),
        data_eleicao: values.data_eleicao.format('YYYY-MM-DD'),
        codigo_uf_ibge: null,
        codigo_municipio_ibge: null,
      };
      return editing
        ? updateOfficialElection(editing.id, payload)
        : createOfficialElection(payload);
    },
    onSuccess: async () => {
      AppToast.success(editing ? 'Eleição atualizada.' : 'Eleição oficial cadastrada.');
      setModalOpen(false);
      setEditing(null);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['official-elections'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ tipo: 'federal', turno: 1, ativo: true });
    setModalOpen(true);
  };

  const openEdit = (item: OfficialElection) => {
    setEditing(item);
    form.setFieldsValue({
      ...item,
      tipo: item.tipo === 'municipal' ? 'municipal' : 'federal',
      data_eleicao: dayjs(item.data_eleicao),
      descricao: item.descricao ?? undefined,
    });
    setModalOpen(true);
  };

  return (
    <div>
      <PageHeader
        title="Eleições oficiais"
        description="Catálogo global mantido pela plataforma e compartilhado por todos os tenants."
        actions={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Nova eleição
          </Button>
        }
      />
      <Card>
        <BaseTable
          rowKey="id"
          loading={elections.isPending}
          error={elections.error ? normalizeApiError(elections.error).message : null}
          onRetry={() => elections.refetch()}
          dataSource={elections.data ?? []}
          columns={[
            {
              title: 'Eleição',
              render: (_, item: OfficialElection) =>
                item.descricao || `${typeLabels[item.tipo]} ${item.ano}`,
            },
            {
              title: 'Tipo',
              dataIndex: 'tipo',
              render: (value: ElectionType) => typeLabels[value],
            },
            { title: 'Turno', dataIndex: 'turno', render: (value: number) => `${value}º turno` },
            {
              title: 'Data',
              dataIndex: 'data_eleicao',
              render: (value: string) => dayjs(value).format('DD/MM/YYYY'),
            },
            {
              title: 'Escopo',
              render: (_, item: OfficialElection) =>
                item.tipo === 'municipal' ? 'Todos os municípios' : 'Todos os estados',
            },
            {
              title: 'Status',
              dataIndex: 'ativo',
              render: (active: boolean) => (
                <Tag color={active ? 'success' : 'default'}>{active ? 'Ativa' : 'Inativa'}</Tag>
              ),
            },
            {
              title: 'Ações',
              render: (_, item: OfficialElection) => (
                <Button icon={<EditOutlined />} onClick={() => openEdit(item)}>
                  Editar
                </Button>
              ),
            },
          ]}
        />
      </Card>

      <BaseModal
        isOpen={modalOpen}
        title={editing ? 'Editar eleição oficial' : 'Nova eleição oficial'}
        confirmLoading={save.isPending}
        onCancel={() => {
          setModalOpen(false);
          setEditing(null);
        }}
        onOk={() => form.validateFields().then((values) => save.mutate(values))}
      >
        <Form form={form} layout="vertical">
          <Alert
            type="info"
            showIcon
            message="Cadastro compartilhado por todos os tenants"
            description="Informe apenas o calendário oficial. Estado, município e cargo serão definidos em cada campanha."
            style={{ marginBottom: 16 }}
          />
          <Form.Item name="tipo" label="Tipo" rules={[{ required: true }]}>
            <Select options={officialElectionTypeOptions} />
          </Form.Item>
          <Form.Item name="data_eleicao" label="Data da eleição" rules={[{ required: true }]}>
            <DatePicker format="DD/MM/YYYY" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="turno" label="Turno" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 1, label: '1º turno' },
                { value: 2, label: '2º turno' },
              ]}
            />
          </Form.Item>
          <Form.Item label="Abrangência">
            <Select
              disabled
              value={electionType === 'municipal' ? 'all-cities' : 'all-states'}
              options={[
                {
                  value: electionType === 'municipal' ? 'all-cities' : 'all-states',
                  label:
                    electionType === 'municipal' ? 'Todos os municípios' : 'Todos os estados',
                },
              ]}
            />
          </Form.Item>
          <Form.Item name="descricao" label="Nome da eleição (opcional)">
            <Input maxLength={180} placeholder="Ex.: Eleições Gerais 2026" />
          </Form.Item>
          {editing && (
            <Form.Item name="ativo" label="Ativa" valuePropName="checked">
              <Switch />
            </Form.Item>
          )}
        </Form>
      </BaseModal>
    </div>
  );
}
