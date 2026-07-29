import { ApartmentOutlined, CrownOutlined, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd';
import type { TableProps } from 'antd';
import { useEffect, useMemo, useState } from 'react';

import { AppToast } from '@/components/feedback/AppToast';
import { LocalizedStatistic as Statistic } from '@/components/data/LocalizedStatistic';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  alterarStatusHierarquia,
  criarHierarquia,
  definirLideranca,
  excluirHierarquia,
  excluirLideranca,
  listarHierarquia,
  listarLiderancas,
  listarPessoas,
} from '@/modules/cadastro/pessoas-service';
import type {
  Hierarquia,
  Lideranca,
  LiderancaInput,
  PessoaListItem,
} from '@/modules/cadastro/types';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';

interface HierarchyForm {
  lideranca_superior_id: number;
  pessoa_subordinada_id: number;
  papel_subordinado: Hierarquia['papel_subordinado'];
}

interface LeadershipForm extends LiderancaInput {
  pessoa_id: number;
}

function formatDate(value: string): string {
  const [year, month, day] = value.split('T')[0].split('-');
  return year && month && day ? `${day}/${month}/${year}` : value;
}

function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedValue(value), delay);
    return () => window.clearTimeout(timeout);
  }, [delay, value]);

  return debouncedValue;
}

export function LiderancasPage() {
  const queryClient = useQueryClient();
  const profiles = useSessionStore((state) => state.user?.profiles ?? []);
  const canDelete = profiles.some((profile) => ['gestor', 'gestor_saas'].includes(profile));
  const [linkModalOpen, setLinkModalOpen] = useState(false);
  const [leadershipModalOpen, setLeadershipModalOpen] = useState(false);
  const [leaderFilter, setLeaderFilter] = useState('');
  const [coordinatorFilter, setCoordinatorFilter] = useState<number>();
  const [territoryFilter, setTerritoryFilter] = useState<number>();
  const [superiorFilter, setSuperiorFilter] = useState<number>();
  const [linkedPersonFilter, setLinkedPersonFilter] = useState('');
  const [roleFilter, setRoleFilter] = useState<Hierarquia['papel_subordinado']>();
  const [linkForm] = Form.useForm<HierarchyForm>();
  const [leadershipForm] = Form.useForm<LeadershipForm>();
  const debouncedLeaderFilter = useDebouncedValue(leaderFilter.trim());
  const debouncedLinkedPersonFilter = useDebouncedValue(linkedPersonFilter.trim());
  const leadershipFilters = useMemo(
    () => ({
      query: debouncedLeaderFilter.length >= 3 ? debouncedLeaderFilter : undefined,
      coordenador_id: coordinatorFilter,
      territorio_id: territoryFilter,
    }),
    [coordinatorFilter, debouncedLeaderFilter, territoryFilter],
  );
  const hierarchyFilters = useMemo(
    () => ({
      pessoa_query:
        debouncedLinkedPersonFilter.length >= 3 ? debouncedLinkedPersonFilter : undefined,
      lideranca_superior_id: superiorFilter,
      papel_subordinado: roleFilter,
    }),
    [debouncedLinkedPersonFilter, roleFilter, superiorFilter],
  );
  const leadersQuery = useQuery({
    queryKey: ['cadastro', 'liderancas', 'table', leadershipFilters],
    queryFn: () => listarLiderancas(leadershipFilters),
  });
  const hierarchyQuery = useQuery({
    queryKey: ['cadastro', 'hierarquia', 'table', hierarchyFilters],
    queryFn: () => listarHierarquia(hierarchyFilters),
  });
  const leadershipOptionsQuery = useQuery({
    queryKey: ['cadastro', 'liderancas', 'options'],
    queryFn: () => listarLiderancas(),
  });
  const hierarchyOptionsQuery = useQuery({
    queryKey: ['cadastro', 'hierarquia', 'options'],
    queryFn: () => listarHierarquia(),
  });
  const peopleQuery = useQuery({
    queryKey: ['cadastro', 'pessoas', 'leadership-options'],
    queryFn: () => listarPessoas({ page: 1, page_size: 100 }),
  });
  const leaders = useMemo(() => leadershipOptionsQuery.data ?? [], [leadershipOptionsQuery.data]);
  const peopleById = useMemo(
    () => new Map((peopleQuery.data?.items ?? []).map((person) => [person.id, person])),
    [peopleQuery.data],
  );
  const leaderPersonIds = useMemo(
    () => new Set((leadersQuery.data ?? []).map((leader) => leader.pessoa_id)),
    [leadersQuery.data],
  );
  const leadersById = useMemo(
    () => new Map((leadersQuery.data ?? []).map((leader) => [leader.id, leader])),
    [leadersQuery.data],
  );
  const activelyLinkedPersonIds = useMemo(
    () =>
      new Set(
        (hierarchyOptionsQuery.data ?? [])
          .filter((item) => item.ativo)
          .map((item) => item.pessoa_subordinada_id),
      ),
    [hierarchyOptionsQuery.data],
  );
  const territoryOptions = useMemo(() => {
    const territories = new Map<number, string>();
    leaders.forEach((leader) =>
      (leader.territorios ?? []).forEach((territory) =>
        territories.set(territory.id, territory.nome),
      ),
    );
    return Array.from(territories, ([value, label]) => ({ value, label })).sort((a, b) =>
      a.label.localeCompare(b.label, 'pt-BR'),
    );
  }, [leaders]);
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
      setLinkModalOpen(false);
      linkForm.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['cadastro', 'hierarquia'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const createLeadershipMutation = useMutation({
    mutationFn: ({ pessoa_id, ...payload }: LeadershipForm) =>
      definirLideranca(pessoa_id, {
        ...payload,
        coordenador_id: payload.coordenador_id ?? null,
        apelido_campanha: payload.apelido_campanha?.trim() || null,
      }),
    onSuccess: async () => {
      AppToast.success('Liderança criada.');
      setLeadershipModalOpen(false);
      leadershipForm.resetFields();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['cadastro', 'liderancas'] }),
        queryClient.invalidateQueries({ queryKey: ['cadastro', 'pessoas'] }),
      ]);
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const statusMutation = useMutation({
    mutationFn: ({ id, ativo }: { id: number; ativo: boolean }) =>
      alterarStatusHierarquia(id, ativo),
    onSuccess: async (_, variables) => {
      AppToast.success(variables.ativo ? 'Vínculo ativado.' : 'Vínculo inativado.');
      await queryClient.invalidateQueries({ queryKey: ['cadastro', 'hierarquia'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const deleteLeadershipMutation = useMutation({
    mutationFn: excluirLideranca,
    onSuccess: async () => {
      AppToast.success('Liderança excluída.');
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['cadastro', 'liderancas'] }),
        queryClient.invalidateQueries({ queryKey: ['cadastro', 'hierarquia'] }),
      ]);
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const deleteHierarchyMutation = useMutation({
    mutationFn: excluirHierarquia,
    onSuccess: async () => {
      AppToast.success('Vínculo excluído.');
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
            {item.pessoa_nome_completo || peopleById.get(id)?.nome_completo || `Pessoa #${id}`}
            {item.apelido_campanha ? ` (${item.apelido_campanha})` : ''}
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
      render: (id: number | null, item) =>
        id ? item.coordenador_nome_completo || `Liderança #${id}` : 'Raiz da estrutura',
    },
    {
      title: 'Territórios',
      dataIndex: 'territorios',
      render: (values: Array<{ id: number; nome: string }> = []) =>
        values.length
          ? values.map((territory) => <Tag key={territory.id}>{territory.nome}</Tag>)
          : 'Não vinculado',
    },
    {
      title: 'Tags',
      dataIndex: 'tags',
      render: (values: Array<{ id: number; nome: string; cor: string | null }> = []) =>
        values.length
          ? values.map((tag) => (
              <Tag key={tag.id} color={tag.cor || undefined} style={{ marginBottom: 6 }}>
                {tag.nome}
              </Tag>
            ))
          : 'Sem tags',
    },
    {
      title: 'Status',
      dataIndex: 'ativo',
      render: (active: boolean) => (
        <Tag color={active ? 'success' : 'default'}>{active ? 'Ativa' : 'Inativa'}</Tag>
      ),
    },
    ...(canDelete
      ? [
          {
            title: 'Ação',
            key: 'action',
            width: 90,
            render: (_: unknown, item: Lideranca) => (
              <Popconfirm
                title="Excluir liderança"
                description="Deseja realmente excluir este registro?"
                okText="Sim"
                cancelText="Não"
                okButtonProps={{ danger: true }}
                onConfirm={() => deleteLeadershipMutation.mutate(item.id)}
              >
                <Button
                  danger
                  aria-label="Excluir liderança"
                  icon={<DeleteOutlined />}
                  loading={
                    deleteLeadershipMutation.isPending &&
                    deleteLeadershipMutation.variables === item.id
                  }
                />
              </Popconfirm>
            ),
          },
        ]
      : []),
  ];

  const hierarchyColumns: TableProps<Hierarquia>['columns'] = [
    {
      title: 'Superior',
      dataIndex: 'lideranca_superior_id',
      render: (id: number, item) => {
        const leader = leadersById.get(id);
        return (
          item.lideranca_superior_nome ||
          leader?.pessoa_nome_completo ||
          (leader ? peopleById.get(leader.pessoa_id)?.nome_completo : null) ||
          `Liderança #${id}`
        );
      },
    },
    {
      title: 'Pessoa vinculada',
      dataIndex: 'pessoa_subordinada_id',
      render: (id: number, item) =>
        item.pessoa_subordinada_nome || peopleById.get(id)?.nome_completo || `Pessoa #${id}`,
    },
    {
      title: 'Papel',
      dataIndex: 'papel_subordinado',
      render: (value: string) => <Tag color="blue">{value}</Tag>,
    },
    {
      title: 'Desde',
      dataIndex: 'data_inicio',
      render: (value: string) => formatDate(value),
    },
    {
      title: 'Status',
      dataIndex: 'ativo',
      render: (active: boolean, item) => (
        <Switch
          checked={active}
          checkedChildren="Ativo"
          unCheckedChildren="Inativo"
          loading={statusMutation.isPending && statusMutation.variables?.id === item.id}
          onChange={(checked) => statusMutation.mutate({ id: item.id, ativo: checked })}
        />
      ),
    },
    ...(canDelete
      ? [
          {
            title: 'Ação',
            key: 'action',
            width: 90,
            render: (_: unknown, item: Hierarquia) => (
              <Popconfirm
                title="Excluir vínculo"
                description="Deseja realmente excluir este registro?"
                okText="Sim"
                cancelText="Não"
                okButtonProps={{ danger: true }}
                onConfirm={() => deleteHierarchyMutation.mutate(item.id)}
              >
                <Button
                  danger
                  aria-label="Excluir vínculo"
                  icon={<DeleteOutlined />}
                  loading={
                    deleteHierarchyMutation.isPending &&
                    deleteHierarchyMutation.variables === item.id
                  }
                />
              </Popconfirm>
            ),
          },
        ]
      : []),
  ];

  return (
    <div>
      <PageHeader
        title="Lideranças"
        description="Coordenadores, líderes e rede operacional de campo."
        breadcrumbs={[{ label: 'Início', to: '/dashboard' }, { label: 'Lideranças' }]}
        actions={
          <Button
            type="primary"
            icon={<CrownOutlined />}
            onClick={() => setLeadershipModalOpen(true)}
          >
            Adicionar liderança
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
          <Statistic
            title="Pessoas vinculadas"
            value={(hierarchyOptionsQuery.data ?? []).filter((item) => item.ativo).length}
          />
        </Card>
      </Space>
      <Card title="Lideranças cadastradas" style={{ marginBottom: 20 }}>
        <Space wrap style={{ marginBottom: 16 }}>
          <Input
            allowClear
            placeholder="Buscar por liderança (mín. 3 caracteres)"
            value={leaderFilter}
            onChange={(event) => setLeaderFilter(event.target.value)}
            style={{ width: 240 }}
          />
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="Filtrar por coordenador"
            value={coordinatorFilter}
            onChange={setCoordinatorFilter}
            style={{ width: 240 }}
            options={leaders
              .filter((leader) =>
                ['coordenador_geral', 'coordenador_territorial'].includes(leader.tipo_lideranca),
              )
              .map((leader) => ({
                value: leader.id,
                label: leader.pessoa_nome_completo || `Liderança #${leader.id}`,
              }))}
          />
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="Filtrar por território"
            value={territoryFilter}
            onChange={setTerritoryFilter}
            style={{ width: 240 }}
            options={territoryOptions}
          />
        </Space>
        <Table
          rowKey="id"
          columns={leaderColumns}
          dataSource={leadersQuery.data ?? []}
          loading={leadersQuery.isFetching}
          pagination={{ defaultPageSize: 10, showSizeChanger: true }}
          scroll={{ x: 760 }}
        />
      </Card>
      <Card
        title="Eleitores/Liderados"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setLinkModalOpen(true)}>
            Vincular pessoa
          </Button>
        }
      >
        <Space wrap style={{ marginBottom: 16 }}>
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="Filtrar por superior"
            value={superiorFilter}
            onChange={setSuperiorFilter}
            style={{ width: 240 }}
            options={leaders.map((leader) => ({
              value: leader.id,
              label: leader.pessoa_nome_completo || `Liderança #${leader.id}`,
            }))}
          />
          <Input
            allowClear
            placeholder="Buscar pessoa vinculada (mín. 3 caracteres)"
            value={linkedPersonFilter}
            onChange={(event) => setLinkedPersonFilter(event.target.value)}
            style={{ width: 240 }}
          />
          <Select
            allowClear
            placeholder="Filtrar por papel"
            value={roleFilter}
            onChange={setRoleFilter}
            style={{ width: 200 }}
            options={[
              { value: 'lider', label: 'Líder' },
              { value: 'liderado', label: 'Liderado' },
              { value: 'apoiador', label: 'Apoiador' },
              { value: 'eleitor', label: 'Eleitor' },
            ]}
          />
        </Space>
        <Table
          rowKey="id"
          columns={hierarchyColumns}
          dataSource={hierarchyQuery.data ?? []}
          loading={hierarchyQuery.isFetching}
          pagination={{ defaultPageSize: 10, showSizeChanger: true }}
          scroll={{ x: 680 }}
        />
      </Card>
      <Modal
        open={linkModalOpen}
        title="Vincular pessoa à liderança"
        okText="Criar vínculo"
        confirmLoading={createMutation.isPending}
        onCancel={() => setLinkModalOpen(false)}
        onOk={() => linkForm.validateFields().then((values) => createMutation.mutate(values))}
      >
        <Form form={linkForm} layout="vertical">
          <Form.Item
            name="lideranca_superior_id"
            label="Liderança superior"
            rules={[{ required: true }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              options={leaders.map((item) => {
                const nome =
                  item.pessoa_nome_completo ||
                  peopleById.get(item.pessoa_id)?.nome_completo ||
                  `Liderança #${item.id}`;
                return {
                  value: item.id,
                  label: item.apelido_campanha ? `${nome} (${item.apelido_campanha})` : nome,
                };
              })}
            />
          </Form.Item>
          <Form.Item name="pessoa_subordinada_id" label="Pessoa" rules={[{ required: true }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={(peopleQuery.data?.items ?? [])
                .filter((item) => !activelyLinkedPersonIds.has(item.id))
                .map((item: PessoaListItem) => ({
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
      <Modal
        open={leadershipModalOpen}
        title="Adicionar liderança"
        okText="Criar liderança"
        confirmLoading={createLeadershipMutation.isPending}
        onCancel={() => setLeadershipModalOpen(false)}
        onOk={() =>
          leadershipForm.validateFields().then((values) => createLeadershipMutation.mutate(values))
        }
      >
        <Form
          form={leadershipForm}
          layout="vertical"
          initialValues={{
            tipo_lideranca: 'coordenador_geral',
            coordenador_id: null,
            apelido_campanha: 'Coordenação geral',
            ativo: true,
          }}
        >
          <Form.Item name="pessoa_id" label="Pessoa" rules={[{ required: true }]}>
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="Selecione a pessoa"
              options={(peopleQuery.data?.items ?? [])
                .filter((person) => !leaderPersonIds.has(person.id))
                .map((person) => ({ value: person.id, label: person.nome_completo }))}
            />
          </Form.Item>
          <Form.Item name="tipo_lideranca" label="Tipo de liderança" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'coordenador_geral', label: 'Coordenador geral' },
                { value: 'coordenador_territorial', label: 'Coordenador territorial' },
                { value: 'lider', label: 'Líder' },
                { value: 'sublider', label: 'Sublíder' },
              ]}
            />
          </Form.Item>
          <Form.Item name="coordenador_id" label="Coordenador">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="Sem coordenador (raiz da estrutura)"
              options={leaders
                .filter((leader) =>
                  ['coordenador_geral', 'coordenador_territorial'].includes(leader.tipo_lideranca),
                )
                .map((leader) => {
                  const nome =
                    leader.pessoa_nome_completo ||
                    peopleById.get(leader.pessoa_id)?.nome_completo ||
                    `Liderança #${leader.id}`;
                  return {
                    value: leader.id,
                    label: leader.apelido_campanha ? `${nome} (${leader.apelido_campanha})` : nome,
                  };
                })}
            />
          </Form.Item>
          <Form.Item name="apelido_campanha" label="Apelido de campanha">
            <Input maxLength={120} />
          </Form.Item>
          <Form.Item name="ativo" label="Liderança ativa" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
