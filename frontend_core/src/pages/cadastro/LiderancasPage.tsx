import { ApartmentOutlined, PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Card, Form, Modal, Select, Space, Statistic, Table, Tag, Typography } from 'antd';
import type { TableProps } from 'antd';
import { useMemo, useState } from 'react';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  criarHierarquia,
  listarHierarquia,
  listarLiderancas,
  listarPessoas,
} from '@/modules/cadastro/pessoas-service';
import type { Hierarquia, Lideranca, PessoaListItem } from '@/modules/cadastro/types';
import { normalizeApiError } from '@/services/api/api-error';

interface HierarchyForm {
  lideranca_superior_id: number;
  pessoa_subordinada_id: number;
  papel_subordinado: Hierarquia['papel_subordinado'];
}

export function LiderancasPage() {
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm<HierarchyForm>();
  const leadersQuery = useQuery({
    queryKey: ['cadastro', 'liderancas'],
    queryFn: listarLiderancas,
  });
  const hierarchyQuery = useQuery({
    queryKey: ['cadastro', 'hierarquia'],
    queryFn: listarHierarquia,
  });
  const peopleQuery = useQuery({
    queryKey: ['cadastro', 'pessoas', 'leadership-options'],
    queryFn: () => listarPessoas({ page: 1, page_size: 100 }),
  });
  const peopleById = useMemo(
    () => new Map((peopleQuery.data?.items ?? []).map((person) => [person.id, person])),
    [peopleQuery.data],
  );
  const createMutation = useMutation({
    mutationFn: (values: HierarchyForm) =>
      criarHierarquia({
        ...values,
        data_inicio: new Date().toISOString().slice(0, 10),
        data_fim: null,
        ativo: true,
      }),
    onSuccess: async () => {
      AppToast.success('Vínculo de liderança criado.');
      setModalOpen(false);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['cadastro', 'hierarquia'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const leaderColumns: TableProps<Lideranca>['columns'] = [
    {
      title: 'Liderança',
      dataIndex: 'pessoa_id',
      render: (id: number, item) => (
        <div>
          <strong>
            {item.apelido_campanha || peopleById.get(id)?.nome_completo || `Pessoa #${id}`}
          </strong>
          <Typography.Text type="secondary" style={{ display: 'block' }}>
            {item.tipo_lideranca.replaceAll('_', ' ')}
          </Typography.Text>
        </div>
      ),
    },
    {
      title: 'Coordenador',
      dataIndex: 'coordenador_id',
      render: (id: number | null) => (id ? `Liderança #${id}` : 'Raiz da estrutura'),
    },
    {
      title: 'Meta inicial',
      dataIndex: 'meta_votos',
      render: (value: number | null) => value ?? '—',
    },
    {
      title: 'Territórios',
      dataIndex: 'territorio_ids',
      render: (values: number[] = []) =>
        values.length ? values.map((value) => <Tag key={value}>#{value}</Tag>) : 'Não vinculado',
    },
    {
      title: 'Status',
      dataIndex: 'ativo',
      render: (active: boolean) => (
        <Tag color={active ? 'success' : 'default'}>{active ? 'Ativa' : 'Inativa'}</Tag>
      ),
    },
  ];

  const hierarchyColumns: TableProps<Hierarquia>['columns'] = [
    {
      title: 'Superior',
      dataIndex: 'lideranca_superior_id',
      render: (id: number) => `Liderança #${id}`,
    },
    {
      title: 'Pessoa vinculada',
      dataIndex: 'pessoa_subordinada_id',
      render: (id: number) => peopleById.get(id)?.nome_completo || `Pessoa #${id}`,
    },
    {
      title: 'Papel',
      dataIndex: 'papel_subordinado',
      render: (value: string) => <Tag color="blue">{value}</Tag>,
    },
    { title: 'Desde', dataIndex: 'data_inicio' },
  ];

  const leaders = leadersQuery.data ?? [];
  return (
    <div>
      <PageHeader
        title="Lideranças"
        description="Coordenadores, líderes, metas e rede operacional de campo."
        breadcrumbs={[{ label: 'Início', to: '/dashboard' }, { label: 'Lideranças' }]}
        actions={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            Vincular pessoa
          </Button>
        }
      />
      <Space size={16} wrap style={{ marginBottom: 20 }}>
        <Card>
          <Statistic
            title="Lideranças ativas"
            value={leaders.length}
            prefix={<ApartmentOutlined />}
          />
        </Card>
        <Card>
          <Statistic title="Pessoas vinculadas" value={hierarchyQuery.data?.length ?? 0} />
        </Card>
        <Card>
          <Statistic
            title="Meta total"
            value={leaders.reduce((total, item) => total + (item.meta_votos ?? 0), 0)}
          />
        </Card>
      </Space>
      <Card title="Lideranças cadastradas" style={{ marginBottom: 20 }}>
        <Table
          rowKey="id"
          columns={leaderColumns}
          dataSource={leaders}
          loading={leadersQuery.isPending}
          pagination={false}
          scroll={{ x: 760 }}
        />
      </Card>
      <Card title="Hierarquia de campo">
        <Table
          rowKey="id"
          columns={hierarchyColumns}
          dataSource={hierarchyQuery.data ?? []}
          loading={hierarchyQuery.isPending}
          pagination={false}
          scroll={{ x: 680 }}
        />
      </Card>
      <Modal
        open={modalOpen}
        title="Vincular pessoa à liderança"
        okText="Criar vínculo"
        confirmLoading={createMutation.isPending}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.validateFields().then((values) => createMutation.mutate(values))}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="lideranca_superior_id"
            label="Liderança superior"
            rules={[{ required: true }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              options={leaders.map((item) => ({
                value: item.id,
                label:
                  item.apelido_campanha ||
                  peopleById.get(item.pessoa_id)?.nome_completo ||
                  `#${item.id}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="pessoa_subordinada_id" label="Pessoa" rules={[{ required: true }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={(peopleQuery.data?.items ?? []).map((item: PessoaListItem) => ({
                value: item.id,
                label: item.nome_completo,
              }))}
            />
          </Form.Item>
          <Form.Item name="papel_subordinado" label="Papel" initialValue="liderado">
            <Select
              options={[
                { value: 'lider', label: 'Líder' },
                { value: 'liderado', label: 'Liderado' },
                { value: 'apoiador', label: 'Apoiador' },
                { value: 'eleitor', label: 'Eleitor' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
