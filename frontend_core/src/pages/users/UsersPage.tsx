import { DeleteOutlined, EnvironmentOutlined, KeyOutlined, PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  Checkbox,
  Collapse,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import type { TableProps } from 'antd';
import { useState } from 'react';

import { BaseTable } from '@/components/data/BaseTable';
import { AppToast } from '@/components/feedback/AppToast';
import { BaseModal } from '@/components/feedback/BaseModal';
import { PageHeader } from '@/components/layout/PageHeader';
import type { TerritorialAccess } from '@/modules/auth/types';
import {
  createUser,
  deleteUser,
  listProfiles,
  listUsers,
  replaceTerritorialAccess,
  resetUserPassword,
  updateUser,
} from '@/modules/users/user-service';
import type {
  TerritorialAccessInput,
  UserCreateInput,
  UserRecord,
  UserUpdateInput,
} from '@/modules/users/types';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';

import styles from '../tenants/TenantPages.module.css';

type UserFormValues = UserCreateInput & UserUpdateInput;
type ScopeFormValue = {
  tipo_escopo: TerritorialAccess['tipo_escopo'];
  identificador?: number;
  pode_administrar?: boolean;
};

const scopeLabels: Record<TerritorialAccess['tipo_escopo'], string> = {
  global: 'Global',
  estado: 'Estado',
  municipio: 'Município',
  bairro: 'Bairro',
  zona_eleitoral: 'Zona eleitoral',
  secao_eleitoral: 'Seção eleitoral',
  territorio: 'Território operacional',
};

const scopeIdFields = {
  estado: 'codigo_uf_ibge',
  municipio: 'codigo_municipio_ibge',
  bairro: 'bairro_id',
  zona_eleitoral: 'zona_eleitoral_id',
  secao_eleitoral: 'secao_eleitoral_id',
  territorio: 'territorio_id',
} as const;

export function UsersPage() {
  const queryClient = useQueryClient();
  const permissions = useSessionStore((state) => state.user?.permissions ?? []);
  const isSaasManager = useSessionStore(
    (state) => state.user?.profiles.includes('gestor_saas') ?? false,
  );
  const [filters, setFilters] = useState<{ query?: string; status?: string }>({});
  const [editing, setEditing] = useState<UserRecord | null>(null);
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [territorialUser, setTerritorialUser] = useState<UserRecord | null>(null);
  const [userForm] = Form.useForm<UserFormValues>();
  const [scopeForm] = Form.useForm<{ acessos: ScopeFormValue[] }>();

  const users = useQuery({
    queryKey: ['users', filters],
    queryFn: () => listUsers(filters),
  });
  const profiles = useQuery({ queryKey: ['access-profiles'], queryFn: listProfiles });

  const saveUser = useMutation({
    mutationFn: (values: UserFormValues) => {
      if (editing) {
        const update: UserUpdateInput = {
          nome: values.nome,
          email: values.email,
          telefone: values.telefone,
          pessoa_id: values.pessoa_id,
          status: values.status,
          perfil_ids: values.perfil_ids,
        };
        return updateUser(editing.id, update);
      }
      return createUser(values);
    },
    onSuccess: async () => {
      AppToast.success(editing ? 'Usuário atualizado.' : 'Usuário criado.');
      setUserModalOpen(false);
      setEditing(null);
      userForm.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const saveScopes = useMutation({
    mutationFn: (values: { acessos: ScopeFormValue[] }) => {
      if (!territorialUser) throw new Error('Usuário não selecionado.');
      return replaceTerritorialAccess(territorialUser.id, (values.acessos ?? []).map(scopeToApi));
    },
    onSuccess: async () => {
      AppToast.success('Acessos territoriais atualizados.');
      setTerritorialUser(null);
      scopeForm.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const openCreate = () => {
    setEditing(null);
    userForm.resetFields();
    userForm.setFieldsValue({ status: 'ativo', perfil_ids: [] });
    setUserModalOpen(true);
  };

  const openEdit = (user: UserRecord) => {
    setEditing(user);
    userForm.setFieldsValue({
      nome: user.nome,
      email: user.email,
      telefone: user.telefone ?? undefined,
      status: user.status,
      perfil_ids: user.perfis.map((profile) => profile.id),
    });
    setUserModalOpen(true);
  };

  const openTerritorial = (user: UserRecord) => {
    setTerritorialUser(user);
    scopeForm.setFieldsValue({
      acessos: user.acessos_territoriais.map(scopeFromApi),
    });
  };

  const handleResetPassword = async (user: UserRecord) => {
    try {
      const temporaryPassword = await resetUserPassword(user.id);
      Modal.info({
        title: 'Senha temporária emitida',
        content: (
          <Space direction="vertical">
            <Typography.Text>
              Entregue esta senha ao usuário por um canal seguro. Ela não será exibida novamente.
            </Typography.Text>
            <Typography.Text code copyable>
              {temporaryPassword}
            </Typography.Text>
          </Space>
        ),
      });
    } catch (error) {
      AppToast.error(normalizeApiError(error).message);
    }
  };

  const handleDelete = async (user: UserRecord) => {
    try {
      await deleteUser(user.id);
      AppToast.success('Usuário excluído.');
      await queryClient.invalidateQueries({ queryKey: ['users'] });
    } catch (error) {
      AppToast.error(normalizeApiError(error).message);
    }
  };

  const columns: TableProps<UserRecord>['columns'] = [
    {
      title: 'Usuário',
      key: 'usuario',
      render: (_, user) => (
        <Space direction="vertical" size={0}>
          <strong>{user.nome}</strong>
          <Typography.Text type="secondary">{user.email}</Typography.Text>
        </Space>
      ),
    },
    {
      title: 'Perfis',
      key: 'perfis',
      render: (_, user) => user.perfis.map((profile) => <Tag key={profile.id}>{profile.nome}</Tag>),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      render: (value: UserRecord['status']) => (
        <Tag color={value === 'ativo' ? 'success' : value === 'bloqueado' ? 'error' : 'default'}>
          {value}
        </Tag>
      ),
    },
    {
      title: 'Ações',
      key: 'actions',
      render: (_, user) => (
        <Space wrap>
          {permissions.includes('usuarios.editar') && (
            <Button onClick={() => openEdit(user)}>Editar</Button>
          )}
          {permissions.includes('usuarios.administrar') && (
            <>
              <Button icon={<EnvironmentOutlined />} onClick={() => openTerritorial(user)}>
                Territórios
              </Button>
              <Button icon={<KeyOutlined />} onClick={() => void handleResetPassword(user)}>
                Redefinir senha
              </Button>
            </>
          )}
          {permissions.includes('usuarios.excluir') && (
            <Popconfirm
              title="Excluir este usuário?"
              description="A conta será inativada e todas as sessões serão revogadas."
              onConfirm={() => void handleDelete(user)}
            >
              <Button danger icon={<DeleteOutlined />}>
                Excluir
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  const usersTab = (
    <div className={styles.page}>
      <Card size="small">
        <div className={styles.filters}>
          <Input.Search
            allowClear
            placeholder="Nome ou e-mail"
            onSearch={(query) => setFilters((value) => ({ ...value, query: query || undefined }))}
          />
          <Select
            allowClear
            placeholder="Status"
            options={['ativo', 'inativo', 'bloqueado', 'pendente'].map((value) => ({
              value,
              label: value,
            }))}
            onChange={(status) => setFilters((value) => ({ ...value, status }))}
          />
        </div>
      </Card>
      <Card>
        <BaseTable
          rowKey="id"
          columns={columns}
          dataSource={users.data?.items ?? []}
          loading={users.isPending}
          error={users.error ? normalizeApiError(users.error).message : null}
          onRetry={() => users.refetch()}
          pagination={{ pageSize: 20, total: users.data?.total }}
        />
      </Card>
    </div>
  );

  const visibleProfiles = (profiles.data ?? []).filter(
    (profile) => profile.codigo !== 'gestor_saas' || isSaasManager,
  );

  const profilesTab = (
    <Card loading={profiles.isPending}>
      <Collapse
        items={visibleProfiles.map((profile) => ({
          key: profile.id,
          label: (
            <Space>
              <strong>{profile.nome}</strong>
              <Tag>{profile.codigo}</Tag>
            </Space>
          ),
          children: (
            <Space wrap>
              {profile.permissoes.map((permission) => (
                <Tag key={permission.id} color="blue">
                  {permission.codigo}
                </Tag>
              ))}
            </Space>
          ),
        }))}
      />
    </Card>
  );

  return (
    <div className={styles.page}>
      <PageHeader
        title="Usuários e perfis"
        description="Administre contas, papéis, permissões e escopos territoriais."
        actions={
          permissions.includes('usuarios.criar') ? (
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              Novo usuário
            </Button>
          ) : undefined
        }
      />
      <Tabs
        items={[
          { key: 'users', label: 'Usuários', children: usersTab },
          { key: 'profiles', label: 'Perfis e permissões', children: profilesTab },
        ]}
      />

      <BaseModal
        isOpen={userModalOpen}
        title={editing ? 'Editar usuário' : 'Novo usuário'}
        confirmLoading={saveUser.isPending}
        onOk={() => userForm.validateFields().then((values) => saveUser.mutate(values))}
        onCancel={() => setUserModalOpen(false)}
      >
        <Form form={userForm} layout="vertical" className={styles.form}>
          <Form.Item name="nome" label="Nome" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="E-mail" rules={[{ required: true }, { type: 'email' }]}>
            <Input />
          </Form.Item>
          {!editing && (
            <Form.Item name="senha" label="Senha inicial" rules={[{ required: true }, { min: 12 }]}>
              <Input.Password />
            </Form.Item>
          )}
          <Form.Item name="telefone" label="Telefone">
            <Input />
          </Form.Item>
          <Form.Item
            name="perfil_ids"
            label="Perfis"
            rules={[{ required: true, type: 'array', min: 1 }]}
          >
            <Select
              mode="multiple"
              options={visibleProfiles.map((profile) => ({
                value: profile.id,
                label: profile.nome,
              }))}
            />
          </Form.Item>
          {editing && (
            <Form.Item name="status" label="Status">
              <Select
                options={['ativo', 'inativo', 'bloqueado', 'pendente'].map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </Form.Item>
          )}
        </Form>
      </BaseModal>

      <BaseModal
        isOpen={Boolean(territorialUser)}
        title={`Acessos territoriais — ${territorialUser?.nome ?? ''}`}
        confirmLoading={saveScopes.isPending}
        onOk={() => scopeForm.validateFields().then((values) => saveScopes.mutate(values))}
        onCancel={() => setTerritorialUser(null)}
      >
        <Form form={scopeForm} layout="vertical">
          <Form.List name="acessos">
            {(fields, { add, remove }) => (
              <Space direction="vertical" style={{ width: '100%' }}>
                {fields.map((field) => (
                  <Space key={field.key} align="start" wrap>
                    <Form.Item
                      {...field}
                      name={[field.name, 'tipo_escopo']}
                      rules={[{ required: true }]}
                    >
                      <Select
                        style={{ width: 180 }}
                        placeholder="Escopo"
                        options={Object.entries(scopeLabels).map(([value, label]) => ({
                          value,
                          label,
                        }))}
                      />
                    </Form.Item>
                    <Form.Item
                      noStyle
                      shouldUpdate={(before, after) =>
                        before.acessos?.[field.name]?.tipo_escopo !==
                        after.acessos?.[field.name]?.tipo_escopo
                      }
                    >
                      {({ getFieldValue }) =>
                        getFieldValue(['acessos', field.name, 'tipo_escopo']) !== 'global' ? (
                          <Form.Item
                            name={[field.name, 'identificador']}
                            rules={[{ required: true }]}
                          >
                            <InputNumber min={1} placeholder="ID" />
                          </Form.Item>
                        ) : null
                      }
                    </Form.Item>
                    <Form.Item name={[field.name, 'pode_administrar']} valuePropName="checked">
                      <Checkbox>Administrar</Checkbox>
                    </Form.Item>
                    <Button danger onClick={() => remove(field.name)}>
                      Remover
                    </Button>
                  </Space>
                ))}
                <Button type="dashed" onClick={() => add({ pode_administrar: false })}>
                  Adicionar escopo
                </Button>
              </Space>
            )}
          </Form.List>
        </Form>
      </BaseModal>
    </div>
  );
}

function scopeFromApi(access: TerritorialAccess): ScopeFormValue {
  const field = access.tipo_escopo === 'global' ? null : scopeIdFields[access.tipo_escopo];
  return {
    tipo_escopo: access.tipo_escopo,
    identificador: field ? access[field] : undefined,
    pode_administrar: access.pode_administrar,
  };
}

function scopeToApi(access: ScopeFormValue): TerritorialAccessInput {
  const result: TerritorialAccessInput = {
    tipo_escopo: access.tipo_escopo,
    pode_administrar: Boolean(access.pode_administrar),
  };
  if (access.tipo_escopo !== 'global') {
    const field = scopeIdFields[access.tipo_escopo];
    Object.assign(result, { [field]: access.identificador });
  }
  return result;
}
