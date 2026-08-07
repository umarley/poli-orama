import {
  CheckCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  PlusOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  ColorPicker,
  Descriptions,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { AppToast } from '@/components/feedback/AppToast';
import { RemotePersonSelect } from '@/components/forms/RemotePersonSelect';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  atualizarTag,
  atualizarComunidade,
  criarComunidade,
  criarNucleo,
  criarTag,
  listarComunidades,
  listarNucleos,
  listarPapeisComunidade,
  listarParentescos,
  listarPessoasComunidade,
  listarPessoasNucleo,
  listarPessoasTag,
  listarTags,
  removerPessoaTag,
  removerPessoaComunidade,
  removerPessoaNucleo,
  vincularComunidade,
  vincularNucleo,
  vincularTag,
} from '@/modules/cadastro/pessoas-service';
import type { Comunidade, NucleoFamiliar, TagCadastro } from '@/modules/cadastro/types';
import { getTenantConfiguration } from '@/modules/tenants/tenant-service';
import { getCommunityTerminologyLabels } from '@/modules/tenants/tenant-preferences';
import { listarTerritorios } from '@/modules/territorios/territorios-service';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';
import { formatInteger } from '@/utils/number-format';

type Entity = 'tag' | 'community' | 'nucleus';
type Dialog =
  | { mode: 'create'; entity: Entity }
  | { mode: 'edit'; entity: 'tag'; item: TagCadastro }
  | { mode: 'edit'; entity: 'community'; item: Comunidade }
  | { mode: 'link'; entity: Entity; id: number }
  | null;

type DialogValues = Record<string, string | number | boolean | null | undefined>;

function formatDate(value: string | null): string {
  if (!value) return '—';
  const [year, month, day] = value.split('T')[0].split('-');
  return year && month && day ? `${day}/${month}/${year}` : value;
}

export function SegmentacaoPage() {
  const queryClient = useQueryClient();
  const profiles = useSessionStore((state) => state.user?.profiles ?? []);
  const canManageSegmentation = profiles.some((profile) =>
    ['gestor_saas', 'gestor', 'coordenador_territorial'].includes(profile),
  );
  const [dialog, setDialog] = useState<Dialog>(null);
  const [viewedTag, setViewedTag] = useState<TagCadastro | null>(null);
  const [viewedCommunity, setViewedCommunity] = useState<Comunidade | null>(null);
  const [viewedNucleus, setViewedNucleus] = useState<NucleoFamiliar | null>(null);
  const [form] = Form.useForm<DialogValues>();
  const configurationQuery = useQuery({
    queryKey: ['tenant-configuration'],
    queryFn: getTenantConfiguration,
  });
  const communityTerms = getCommunityTerminologyLabels(configurationQuery.data);
  const tagsQuery = useQuery({ queryKey: ['cadastro', 'tags'], queryFn: listarTags });
  const tagStatusMutation = useMutation({
    mutationFn: ({ id, ativo }: { id: number; ativo: boolean }) => atualizarTag(id, { ativo }),
    onSuccess: async (_, variables) => {
      AppToast.success(variables.ativo ? 'Tag ativada.' : 'Tag inativada.');
      await queryClient.invalidateQueries({ queryKey: ['cadastro', 'tags'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const tagPeopleQuery = useQuery({
    queryKey: ['cadastro', 'tags', viewedTag?.id, 'pessoas'],
    queryFn: () => listarPessoasTag(viewedTag!.id),
    enabled: Boolean(viewedTag),
  });
  const removeTagPersonMutation = useMutation({
    mutationFn: ({ tagId, personId }: { tagId: number; personId: number }) =>
      removerPessoaTag(tagId, personId),
    onSuccess: async () => {
      AppToast.success('Vínculo removido.');
      await queryClient.invalidateQueries({
        queryKey: ['cadastro', 'tags', viewedTag?.id, 'pessoas'],
      });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const communitiesQuery = useQuery({
    queryKey: ['cadastro', 'comunidades'],
    queryFn: listarComunidades,
  });
  const communityRolesQuery = useQuery({
    queryKey: ['cadastro', 'comunidades', 'papeis'],
    queryFn: listarPapeisComunidade,
  });
  const communityPeopleQuery = useQuery({
    queryKey: ['cadastro', 'comunidades', viewedCommunity?.id, 'pessoas'],
    queryFn: () => listarPessoasComunidade(viewedCommunity!.id),
    enabled: Boolean(viewedCommunity),
  });
  const removeCommunityPersonMutation = useMutation({
    mutationFn: ({ communityId, personId }: { communityId: number; personId: number }) =>
      removerPessoaComunidade(communityId, personId),
    onSuccess: async () => {
      AppToast.success('Vínculo removido.');
      await queryClient.invalidateQueries({
        queryKey: ['cadastro', 'comunidades', viewedCommunity?.id, 'pessoas'],
      });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const territoriesQuery = useQuery({
    queryKey: ['territorios', 'segmentacao-options'],
    queryFn: () => listarTerritorios(false),
  });
  const nucleiQuery = useQuery({ queryKey: ['cadastro', 'nucleos'], queryFn: listarNucleos });
  const kinshipQuery = useQuery({
    queryKey: ['cadastro', 'nucleos', 'parentescos'],
    queryFn: listarParentescos,
  });
  const nucleusPeopleQuery = useQuery({
    queryKey: ['cadastro', 'nucleos', viewedNucleus?.id, 'pessoas'],
    queryFn: () => listarPessoasNucleo(viewedNucleus!.id),
    enabled: Boolean(viewedNucleus),
  });
  const removeNucleusPersonMutation = useMutation({
    mutationFn: ({ nucleusId, personId }: { nucleusId: number; personId: number }) =>
      removerPessoaNucleo(nucleusId, personId),
    onSuccess: async () => {
      AppToast.success('Vínculo removido.');
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ['cadastro', 'nucleos', viewedNucleus?.id, 'pessoas'],
        }),
        queryClient.invalidateQueries({ queryKey: ['cadastro', 'nucleos'] }),
      ]);
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const mutation = useMutation({
    mutationFn: async (values: DialogValues) => {
      if (!dialog) return;
      if (dialog.mode === 'link') {
        const personId = Number(values.pessoa_id);
        if (dialog.entity === 'tag') await vincularTag(dialog.id, personId);
        if (dialog.entity === 'community')
          await vincularComunidade(dialog.id, personId, values.papel as string | undefined);
        if (dialog.entity === 'nucleus')
          await vincularNucleo(
            dialog.id,
            personId,
            values.parentesco as string | undefined,
            values.observacao as string | undefined,
          );
        return;
      }
      if (dialog.entity === 'tag') {
        const payload = {
          nome: String(values.nome),
          cor: (values.cor as string) || null,
          categoria: (values.categoria as string) || null,
          descricao: (values.descricao as string) || null,
        };
        if (dialog.mode === 'edit') await atualizarTag(dialog.item.id, payload);
        else await criarTag(payload);
      }
      if (dialog.entity === 'community') {
        const payload = {
          nome: String(values.nome),
          tipo: (values.tipo as string) || null,
          descricao: (values.descricao as string) || null,
          lider_responsavel_id: null,
          codigo_municipio_ibge: null,
          territorio_id: values.territorio_id ? Number(values.territorio_id) : null,
        };
        if (dialog.mode === 'edit') await atualizarComunidade(dialog.item.id, payload);
        else await criarComunidade(payload);
      }
      if (dialog.entity === 'nucleus' && dialog.mode === 'create') {
        await criarNucleo({
          nome: String(values.nome),
          pessoa_referencia_id: values.pessoa_referencia_id
            ? Number(values.pessoa_referencia_id)
            : null,
          endereco_id: null,
        });
      }
    },
    onSuccess: async () => {
      AppToast.success(dialog?.mode === 'link' ? 'Pessoa vinculada.' : 'Cadastro salvo.');
      setDialog(null);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['cadastro'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const open = (next: Dialog) => {
    setDialog(next);
    form.resetFields();
    if (next?.mode === 'edit') {
      form.setFieldsValue({
        nome: next.item.nome,
        cor: next.entity === 'tag' ? next.item.cor : undefined,
        categoria: next.entity === 'tag' ? next.item.categoria : undefined,
        tipo: next.entity === 'community' ? next.item.tipo : undefined,
        territorio_id: next.entity === 'community' ? next.item.territorio_id : undefined,
        descricao: next.item.descricao,
      });
    }
  };

  return (
    <div>
      <PageHeader
        title="Segmentação"
        description={`Tags, ${communityTerms.pluralLower} e núcleos familiares da base de pessoas.`}
        breadcrumbs={[{ label: 'Cadastro', to: '/cadastro' }, { label: 'Segmentação' }]}
      />
      <Card>
        <Tabs
          items={[
            {
              key: 'tags',
              label: `Tags (${tagsQuery.data?.length ?? 0})`,
              children: (
                <>
                  {canManageSegmentation && (
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => open({ mode: 'create', entity: 'tag' })}
                      style={{ marginBottom: 16 }}
                    >
                      Nova tag
                    </Button>
                  )}
                  <Table<TagCadastro>
                    rowKey="id"
                    dataSource={tagsQuery.data ?? []}
                    loading={tagsQuery.isPending}
                    pagination={false}
                    columns={[
                      {
                        title: 'Tag',
                        dataIndex: 'nome',
                        render: (name: string, item) => (
                          <Tag color={item.cor || 'blue'}>{name}</Tag>
                        ),
                      },
                      {
                        title: 'Categoria',
                        dataIndex: 'categoria',
                        render: (value) => value || '—',
                      },
                      {
                        title: 'Status',
                        dataIndex: 'ativo',
                        render: (active: boolean) => (
                          <Tag color={active ? 'success' : 'default'}>
                            {active ? 'Ativa' : 'Inativa'}
                          </Tag>
                        ),
                      },
                      {
                        title: 'Ações',
                        render: (_, item) =>
                          canManageSegmentation ? (
                            <Space>
                              <Button
                                type="link"
                                icon={<EyeOutlined />}
                                onClick={() => setViewedTag(item)}
                              >
                                Visualizar
                              </Button>
                              <Button
                                type="link"
                                icon={<EditOutlined />}
                                onClick={() => open({ mode: 'edit', entity: 'tag', item })}
                              >
                                Editar
                              </Button>
                              <Button
                                type="link"
                                danger={item.ativo}
                                icon={item.ativo ? <StopOutlined /> : <CheckCircleOutlined />}
                                loading={
                                  tagStatusMutation.isPending &&
                                  tagStatusMutation.variables?.id === item.id
                                }
                                onClick={() =>
                                  tagStatusMutation.mutate({ id: item.id, ativo: !item.ativo })
                                }
                              >
                                {item.ativo ? 'Inativar' : 'Ativar'}
                              </Button>
                            </Space>
                          ) : null,
                      },
                    ]}
                  />
                </>
              ),
            },
            {
              key: 'communities',
              label: `${communityTerms.plural} (${communitiesQuery.data?.length ?? 0})`,
              children: (
                <>
                  {canManageSegmentation && (
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => open({ mode: 'create', entity: 'community' })}
                      style={{ marginBottom: 16 }}
                    >
                      Nova {communityTerms.singular}
                    </Button>
                  )}
                  <Table<Comunidade>
                    rowKey="id"
                    dataSource={communitiesQuery.data ?? []}
                    loading={communitiesQuery.isPending}
                    pagination={false}
                    columns={[
                      { title: 'Nome', dataIndex: 'nome' },
                      { title: 'Tipo', dataIndex: 'tipo', render: (value) => value || '—' },
                      {
                        title: 'Território',
                        dataIndex: 'territorio_id',
                        render: (value) =>
                          value
                            ? territoriesQuery.data?.find((territory) => territory.id === value)
                                ?.nome || `#${value}`
                            : '—',
                      },
                      {
                        title: 'Ações',
                        render: (_, item) =>
                          canManageSegmentation ? (
                            <Space>
                              <Button
                                type="link"
                                icon={<EyeOutlined />}
                                onClick={() => setViewedCommunity(item)}
                              >
                                Visualizar
                              </Button>
                              <Button
                                type="link"
                                icon={<EditOutlined />}
                                onClick={() => open({ mode: 'edit', entity: 'community', item })}
                              >
                                Editar
                              </Button>
                            </Space>
                          ) : null,
                      },
                    ]}
                  />
                </>
              ),
            },
            {
              key: 'nuclei',
              label: `Núcleos familiares (${nucleiQuery.data?.length ?? 0})`,
              children: (
                <>
                  {canManageSegmentation && (
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => open({ mode: 'create', entity: 'nucleus' })}
                      style={{ marginBottom: 16 }}
                    >
                      Novo núcleo
                    </Button>
                  )}
                  <Table<NucleoFamiliar>
                    rowKey="id"
                    dataSource={nucleiQuery.data ?? []}
                    loading={nucleiQuery.isPending}
                    pagination={false}
                    columns={[
                      {
                        title: 'Nome',
                        dataIndex: 'nome',
                        render: (value, item) => value || `Núcleo #${item.id}`,
                      },
                      {
                        title: 'Membros',
                        dataIndex: 'quantidade_membros',
                        render: (value) => formatInteger(value),
                      },
                      {
                        title: 'Pessoa de referência',
                        dataIndex: 'pessoa_referencia_id',
                        render: (value, item) => {
                          if (!value) return '—';
                          return (
                            <Link to={`/cadastro/pessoas/${value}`}>
                              {item.pessoa_referencia_nome || `Pessoa #${value}`}
                            </Link>
                          );
                        },
                      },
                      {
                        title: 'Ações',
                        render: (_, item) =>
                          canManageSegmentation ? (
                            <Button
                              type="link"
                              icon={<EyeOutlined />}
                              onClick={() => setViewedNucleus(item)}
                            >
                              Visualizar
                            </Button>
                          ) : null,
                      },
                    ]}
                  />
                </>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        open={Boolean(viewedTag)}
        title="Detalhes da tag"
        width={720}
        footer={null}
        onCancel={() => setViewedTag(null)}
      >
        {viewedTag ? (
          <>
            <Descriptions
              bordered
              size="small"
              column={1}
              items={[
                {
                  key: 'nome',
                  label: 'Tag',
                  children: <Tag color={viewedTag.cor || 'blue'}>{viewedTag.nome}</Tag>,
                },
                { key: 'categoria', label: 'Categoria', children: viewedTag.categoria || '—' },
                { key: 'descricao', label: 'Descrição', children: viewedTag.descricao || '—' },
                {
                  key: 'status',
                  label: 'Status',
                  children: viewedTag.ativo ? 'Ativa' : 'Inativa',
                },
              ]}
              style={{ marginBottom: 20 }}
            />
            <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 12 }}>
              <Typography.Title level={5} style={{ margin: 0 }}>
                Pessoas vinculadas
              </Typography.Title>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => open({ mode: 'link', entity: 'tag', id: viewedTag.id })}
              >
                Vincular pessoa
              </Button>
            </Space>
            <Table
              rowKey="id"
              size="small"
              loading={tagPeopleQuery.isPending}
              dataSource={tagPeopleQuery.data ?? []}
              pagination={{ defaultPageSize: 5, showSizeChanger: true }}
              columns={[
                { title: 'Nome', dataIndex: 'nome_completo' },
                {
                  title: 'Data de nascimento',
                  dataIndex: 'data_nascimento',
                  render: (value: string | null) => formatDate(value),
                },
                {
                  title: 'Ação',
                  width: 90,
                  render: (_, person) => (
                    <Popconfirm
                      title="Remover vínculo"
                      description="Confirma a remoção desta pessoa da tag?"
                      okText="Sim"
                      cancelText="Não"
                      okButtonProps={{ danger: true }}
                      onConfirm={() =>
                        removeTagPersonMutation.mutate({
                          tagId: viewedTag.id,
                          personId: person.id,
                        })
                      }
                    >
                      <Button
                        danger
                        aria-label={`Remover ${person.nome_completo}`}
                        icon={<DeleteOutlined />}
                        loading={
                          removeTagPersonMutation.isPending &&
                          removeTagPersonMutation.variables?.personId === person.id
                        }
                      />
                    </Popconfirm>
                  ),
                },
              ]}
            />
          </>
        ) : null}
      </Modal>

      <Modal
        open={Boolean(viewedNucleus)}
        title="Detalhes do núcleo familiar"
        width={800}
        footer={null}
        onCancel={() => setViewedNucleus(null)}
      >
        {viewedNucleus ? (
          <>
            <Descriptions
              bordered
              size="small"
              column={1}
              items={[
                {
                  key: 'nome',
                  label: 'Nome',
                  children: viewedNucleus.nome || `Núcleo #${viewedNucleus.id}`,
                },
                {
                  key: 'referencia',
                  label: 'Pessoa de referência',
                  children: viewedNucleus.pessoa_referencia_id
                    ? viewedNucleus.pessoa_referencia_nome ||
                      `Pessoa #${viewedNucleus.pessoa_referencia_id}`
                    : '—',
                },
                {
                  key: 'quantidade',
                  label: 'Quantidade de membros',
                  children: formatInteger(viewedNucleus.quantidade_membros),
                },
              ]}
              style={{ marginBottom: 20 }}
            />
            <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 12 }}>
              <Typography.Title level={5} style={{ margin: 0 }}>
                Pessoas vinculadas
              </Typography.Title>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => open({ mode: 'link', entity: 'nucleus', id: viewedNucleus.id })}
              >
                Vincular pessoa
              </Button>
            </Space>
            <Table
              rowKey="id"
              size="small"
              loading={nucleusPeopleQuery.isPending}
              dataSource={nucleusPeopleQuery.data ?? []}
              pagination={{ defaultPageSize: 5, showSizeChanger: true }}
              columns={[
                { title: 'Nome', dataIndex: 'nome_completo' },
                {
                  title: 'Data de nascimento',
                  dataIndex: 'data_nascimento',
                  render: (value: string | null) => formatDate(value),
                },
                {
                  title: 'Grau de parentesco',
                  dataIndex: 'parentesco',
                  render: (value: string | null) =>
                    kinshipQuery.data?.find((kinship) => kinship.codigo === value)?.nome ||
                    value ||
                    '—',
                },
                {
                  title: 'Ação',
                  width: 90,
                  render: (_, person) => (
                    <Popconfirm
                      title="Remover vínculo"
                      description="Confirma a remoção desta pessoa do núcleo familiar?"
                      okText="Sim"
                      cancelText="Não"
                      okButtonProps={{ danger: true }}
                      onConfirm={() =>
                        removeNucleusPersonMutation.mutate({
                          nucleusId: viewedNucleus.id,
                          personId: person.id,
                        })
                      }
                    >
                      <Button
                        danger
                        aria-label={`Remover ${person.nome_completo}`}
                        icon={<DeleteOutlined />}
                        loading={
                          removeNucleusPersonMutation.isPending &&
                          removeNucleusPersonMutation.variables?.personId === person.id
                        }
                      />
                    </Popconfirm>
                  ),
                },
              ]}
            />
          </>
        ) : null}
      </Modal>

      <Modal
        open={Boolean(viewedCommunity)}
        title={`Detalhes da ${communityTerms.singular}`}
        width={780}
        footer={null}
        onCancel={() => setViewedCommunity(null)}
      >
        {viewedCommunity ? (
          <>
            <Descriptions
              bordered
              size="small"
              column={1}
              items={[
                { key: 'nome', label: 'Nome', children: viewedCommunity.nome },
                { key: 'tipo', label: 'Tipo', children: viewedCommunity.tipo || '—' },
                {
                  key: 'territorio',
                  label: 'Território',
                  children: viewedCommunity.territorio_id
                    ? territoriesQuery.data?.find(
                        (territory) => territory.id === viewedCommunity.territorio_id,
                      )?.nome || `#${viewedCommunity.territorio_id}`
                    : '—',
                },
                {
                  key: 'descricao',
                  label: 'Descrição',
                  children: viewedCommunity.descricao || '—',
                },
              ]}
              style={{ marginBottom: 20 }}
            />
            <Space style={{ width: '100%', justifyContent: 'space-between', marginBottom: 12 }}>
              <Typography.Title level={5} style={{ margin: 0 }}>
                Pessoas vinculadas
              </Typography.Title>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => open({ mode: 'link', entity: 'community', id: viewedCommunity.id })}
              >
                Vincular pessoa
              </Button>
            </Space>
            <Table
              rowKey="id"
              size="small"
              loading={communityPeopleQuery.isPending}
              dataSource={communityPeopleQuery.data ?? []}
              pagination={{ defaultPageSize: 5, showSizeChanger: true }}
              columns={[
                { title: 'Nome', dataIndex: 'nome_completo' },
                {
                  title: 'Data de nascimento',
                  dataIndex: 'data_nascimento',
                  render: (value: string | null) => formatDate(value),
                },
                {
                  title: 'Papel',
                  dataIndex: 'papel',
                  render: (value: string | null) =>
                    communityRolesQuery.data?.find((role) => role.codigo === value)?.nome ||
                    value ||
                    '—',
                },
                {
                  title: 'Ação',
                  width: 90,
                  render: (_, person) => (
                    <Popconfirm
                      title="Remover vínculo"
                      description={`Confirma a remoção desta pessoa da ${communityTerms.singular}?`}
                      okText="Sim"
                      cancelText="Não"
                      okButtonProps={{ danger: true }}
                      onConfirm={() =>
                        removeCommunityPersonMutation.mutate({
                          communityId: viewedCommunity.id,
                          personId: person.id,
                        })
                      }
                    >
                      <Button
                        danger
                        aria-label={`Remover ${person.nome_completo}`}
                        icon={<DeleteOutlined />}
                        loading={
                          removeCommunityPersonMutation.isPending &&
                          removeCommunityPersonMutation.variables?.personId === person.id
                        }
                      />
                    </Popconfirm>
                  ),
                },
              ]}
            />
          </>
        ) : null}
      </Modal>

      <Modal
        open={Boolean(dialog)}
        zIndex={1100}
        title={
          dialog?.mode === 'link'
            ? 'Vincular pessoa'
            : dialog?.mode === 'edit' && dialog.entity === 'community'
              ? `Editar ${communityTerms.singular}`
              : dialog?.mode === 'edit'
                ? 'Editar item'
                : 'Cadastrar item'
        }
        okText="Salvar"
        confirmLoading={mutation.isPending}
        onCancel={() => setDialog(null)}
        onOk={() => form.validateFields().then((values) => mutation.mutate(values))}
      >
        <Form form={form} layout="vertical">
          {dialog?.mode === 'link' ? (
            <>
              <Form.Item name="pessoa_id" label="Pessoa" rules={[{ required: true }]}>
                <RemotePersonSelect
                  excludeIds={
                    dialog.entity === 'tag'
                      ? (tagPeopleQuery.data ?? []).map((person) => person.id)
                      : dialog.entity === 'community'
                        ? (communityPeopleQuery.data ?? []).map((person) => person.id)
                        : (nucleusPeopleQuery.data ?? []).map((person) => person.id)
                  }
                />
              </Form.Item>
              {dialog.entity === 'community' ? (
                <Form.Item name="papel" label={`Papel na ${communityTerms.singular}`}>
                  <Select
                    allowClear
                    loading={communityRolesQuery.isPending}
                    placeholder="Selecione o papel"
                    options={(communityRolesQuery.data ?? []).map((role) => ({
                      value: role.codigo,
                      label: role.nome,
                    }))}
                  />
                </Form.Item>
              ) : null}
              {dialog.entity === 'nucleus' ? (
                <>
                  <Form.Item name="parentesco" label="Parentesco">
                    <Select
                      allowClear
                      showSearch
                      optionFilterProp="label"
                      loading={kinshipQuery.isPending}
                      placeholder="Selecione o parentesco"
                      options={(kinshipQuery.data ?? []).map((kinship) => ({
                        value: kinship.codigo,
                        label: kinship.nome,
                      }))}
                    />
                  </Form.Item>
                  <Form.Item name="observacao" label="Observação/justificativa">
                    <Input />
                  </Form.Item>
                </>
              ) : null}
            </>
          ) : (
            <>
              <Form.Item name="nome" label="Nome" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              {dialog?.entity === 'tag' ? (
                <>
                  <Form.Item
                    name="cor"
                    label="Cor hexadecimal"
                    getValueFromEvent={(color) => color?.toHexString()}
                  >
                    <ColorPicker allowClear disabledAlpha disabledFormat format="hex" showText />
                  </Form.Item>
                  <Form.Item name="categoria" label="Categoria">
                    <Input />
                  </Form.Item>
                </>
              ) : null}
              {dialog?.entity === 'community' ? (
                <>
                  <Form.Item name="tipo" label="Tipo">
                    <Select
                      allowClear
                      options={[
                        'religiosa',
                        'profissional',
                        'territorial',
                        'politica',
                        'social',
                        'esportiva',
                        'cultural',
                        'outra',
                      ].map((value) => ({ value, label: value }))}
                    />
                  </Form.Item>
                  <Form.Item name="territorio_id" label="Território">
                    <Select
                      allowClear
                      showSearch
                      optionFilterProp="label"
                      loading={territoriesQuery.isPending}
                      placeholder="Selecione um território"
                      options={(territoriesQuery.data ?? []).map((territory) => ({
                        value: territory.id,
                        label: territory.nome,
                      }))}
                    />
                  </Form.Item>
                </>
              ) : null}
              {dialog?.entity === 'nucleus' ? (
                <Form.Item
                  name="pessoa_referencia_id"
                  label="Pessoa referência"
                  rules={[{ required: true }]}
                >
                  <RemotePersonSelect />
                </Form.Item>
              ) : null}
              <Form.Item name="descricao" label="Descrição">
                <Input.TextArea rows={3} />
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>
    </div>
  );
}
