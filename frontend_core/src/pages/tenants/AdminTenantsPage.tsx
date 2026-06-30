import { EditOutlined, PlusOutlined, PoweroffOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Card, Form, Input, Select, Space, Tag } from 'antd';
import type { TableProps } from 'antd';
import { useState } from 'react';

import { BaseTable } from '@/components/data/BaseTable';
import { AppToast } from '@/components/feedback/AppToast';
import { BaseModal } from '@/components/feedback/BaseModal';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  activateTenant,
  createTenant,
  listPlans,
  listTenants,
  updateTenant,
} from '@/modules/tenants/tenant-service';
import type { TenantInput, TenantRecord, TenantStatus } from '@/modules/tenants/types';
import { normalizeApiError } from '@/services/api/api-error';

import styles from './TenantPages.module.css';

const statusLabels: Record<TenantStatus, string> = {
  pendente: 'Pendente',
  ativo: 'Ativo',
  suspenso: 'Suspenso',
  cancelado: 'Cancelado',
  trial: 'Trial',
  inadimplente: 'Inadimplente',
};

export function AdminTenantsPage() {
  const client = useQueryClient();
  const [filters, setFilters] = useState<{ query?: string; status?: string; plano_id?: number }>(
    {},
  );
  const [editing, setEditing] = useState<TenantRecord | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm<TenantInput>();
  const plans = useQuery({ queryKey: ['plans'], queryFn: listPlans });
  const tenants = useQuery({
    queryKey: ['tenants', filters],
    queryFn: () => listTenants(filters),
  });

  const save = useMutation({
    mutationFn: (values: TenantInput) =>
      editing ? updateTenant(editing.id, values) : createTenant(values),
    onSuccess: async () => {
      AppToast.success(editing ? 'Tenant atualizado.' : 'Tenant criado como pendente.');
      setModalOpen(false);
      setEditing(null);
      form.resetFields();
      await client.invalidateQueries({ queryKey: ['tenants'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const activate = useMutation({
    mutationFn: activateTenant,
    onSuccess: async () => {
      AppToast.success('Tenant ativado.');
      await client.invalidateQueries({ queryKey: ['tenants'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue({ status: 'pendente', tem_mandato: false });
    setModalOpen(true);
  };
  const openEdit = (tenant: TenantRecord) => {
    setEditing(tenant);
    form.setFieldsValue(tenant);
    setModalOpen(true);
  };

  const columns: TableProps<TenantRecord>['columns'] = [
    { title: 'Tenant', dataIndex: 'nome', key: 'nome' },
    { title: 'Slug', dataIndex: 'slug', key: 'slug' },
    { title: 'Plano', key: 'plano', render: (_, row) => row.plano?.nome ?? 'Sem plano' },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (value: TenantStatus) => (
        <Tag color={value === 'ativo' ? 'success' : value === 'suspenso' ? 'error' : 'warning'}>
          {statusLabels[value]}
        </Tag>
      ),
    },
    {
      title: 'Ações',
      key: 'actions',
      render: (_, row) => (
        <Space>
          <Button icon={<EditOutlined />} onClick={() => openEdit(row)}>
            Editar
          </Button>
          {['pendente', 'trial', 'suspenso'].includes(row.status) && (
            <Button
              icon={<PoweroffOutlined />}
              loading={activate.isPending}
              onClick={() => activate.mutate(row.id)}
            >
              Ativar
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className={styles.page}>
      <PageHeader
        title="Administração de tenants"
        description="Crie, ative, suspenda e associe planos às operações."
        actions={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Novo tenant
          </Button>
        }
      />
      <Card size="small">
        <div className={styles.filters}>
          <Input.Search
            allowClear
            placeholder="Nome ou slug"
            onSearch={(query) => setFilters((value) => ({ ...value, query: query || undefined }))}
          />
          <Select
            allowClear
            placeholder="Status"
            options={Object.entries(statusLabels).map(([value, label]) => ({ value, label }))}
            onChange={(status) => setFilters((value) => ({ ...value, status }))}
          />
          <Select
            allowClear
            placeholder="Plano"
            options={plans.data?.map((plan) => ({ value: plan.id, label: plan.nome }))}
            onChange={(plano_id) => setFilters((value) => ({ ...value, plano_id }))}
          />
        </div>
      </Card>
      <Card className={styles.card}>
        <BaseTable
          rowKey="id"
          columns={columns}
          dataSource={tenants.data?.items ?? []}
          loading={tenants.isPending}
          error={tenants.error ? normalizeApiError(tenants.error).message : null}
          onRetry={() => tenants.refetch()}
          pagination={{ pageSize: 20, total: tenants.data?.total }}
        />
      </Card>
      <BaseModal
        isOpen={modalOpen}
        title={editing ? 'Editar tenant' : 'Novo tenant'}
        confirmLoading={save.isPending}
        onOk={() => form.validateFields().then((values) => save.mutate(values))}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical" className={styles.form}>
          <Form.Item name="nome" label="Nome" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="slug"
            label="Slug"
            rules={[{ required: true }, { pattern: /^[a-z0-9]+(?:-[a-z0-9]+)*$/ }]}
          >
            <Input />
          </Form.Item>
          {!editing && (
            <>
              <Form.Item name="documento" label="CPF/CNPJ">
                <Input />
              </Form.Item>
              <Form.Item name="tem_mandato" label="Mandato atual">
                <Select
                  options={[
                    { value: false, label: 'Não' },
                    { value: true, label: 'Sim' },
                  ]}
                />
              </Form.Item>
            </>
          )}
          <Form.Item name="plano_assinatura_id" label="Plano">
            <Select
              allowClear
              options={plans.data?.map((plan) => ({ value: plan.id, label: plan.nome }))}
            />
          </Form.Item>
          <Form.Item name="status" label="Status">
            <Select
              options={Object.entries(statusLabels).map(([value, label]) => ({ value, label }))}
            />
          </Form.Item>
        </Form>
      </BaseModal>
    </div>
  );
}
