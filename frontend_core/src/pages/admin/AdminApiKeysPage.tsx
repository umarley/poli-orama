import { CopyOutlined, PlusOutlined, StopOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Alert, Button, Card, Form, Input, Popconfirm, Select, Space, Tag, Typography } from 'antd';
import type { TableProps } from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';

import { BaseTable } from '@/components/data/BaseTable';
import { AppToast } from '@/components/feedback/AppToast';
import { BaseModal } from '@/components/feedback/BaseModal';
import { PageHeader } from '@/components/layout/PageHeader';
import { createApiKey, listApiKeys, revokeApiKey } from '@/modules/auth/api-key-service';
import type { ApiKeyCreated, ApiKeyInput, ApiKeyRecord } from '@/modules/auth/api-key-types';
import { listTenants } from '@/modules/tenants/tenant-service';
import { normalizeApiError } from '@/services/api/api-error';

import styles from '../tenants/TenantPages.module.css';

function formatDate(value: string | null) {
  return value ? dayjs(value).format('DD/MM/YYYY HH:mm') : '—';
}

export function AdminApiKeysPage() {
  const client = useQueryClient();
  const [filters, setFilters] = useState<{ query?: string; tenant_id?: number }>({});
  const [modalOpen, setModalOpen] = useState(false);
  const [createdKey, setCreatedKey] = useState<ApiKeyCreated | null>(null);
  const [form] = Form.useForm<ApiKeyInput>();

  const tenants = useQuery({
    queryKey: ['tenants', { page_size: 100 }],
    queryFn: () => listTenants({}),
  });
  const keys = useQuery({
    queryKey: ['api-keys', filters],
    queryFn: () => listApiKeys(filters),
  });

  const save = useMutation({
    mutationFn: createApiKey,
    onSuccess: async (created) => {
      AppToast.success('Chave de integração criada.');
      setModalOpen(false);
      form.resetFields();
      setCreatedKey(created);
      await client.invalidateQueries({ queryKey: ['api-keys'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const revoke = useMutation({
    mutationFn: revokeApiKey,
    onSuccess: async () => {
      AppToast.success('Chave de integração revogada.');
      await client.invalidateQueries({ queryKey: ['api-keys'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const tenantOptions = (tenants.data?.items ?? []).map((item) => ({
    value: item.id,
    label: `${item.nome} (${item.slug})`,
  }));

  const copyToken = async () => {
    if (!createdKey?.token) return;
    await navigator.clipboard.writeText(createdKey.token);
    AppToast.success('Chave copiada.');
  };

  const columns: TableProps<ApiKeyRecord>['columns'] = [
    { title: 'Nome', dataIndex: 'nome', key: 'nome' },
    {
      title: 'Tenant',
      key: 'tenant',
      render: (_, row) => `${row.tenant_nome} (${row.tenant_slug})`,
    },
    {
      title: 'Prefixo',
      dataIndex: 'token_prefix',
      key: 'token_prefix',
      render: (value: string) => <Typography.Text code>{value}…</Typography.Text>,
    },
    {
      title: 'Status',
      dataIndex: 'ativo',
      key: 'ativo',
      render: (ativo: boolean, row) => (
        <Tag color={ativo && !row.revogada_em ? 'success' : 'error'}>
          {ativo && !row.revogada_em ? 'Ativa' : 'Revogada'}
        </Tag>
      ),
    },
    {
      title: 'Último uso',
      dataIndex: 'ultimo_uso_em',
      key: 'ultimo_uso_em',
      render: formatDate,
    },
    {
      title: 'Criada em',
      dataIndex: 'criado_em',
      key: 'criado_em',
      render: formatDate,
    },
    {
      title: 'Ações',
      key: 'actions',
      render: (_, row) =>
        row.ativo && !row.revogada_em ? (
          <Popconfirm
            title="Revogar esta chave?"
            description="Sites que usam esta chave deixarão de autenticar imediatamente."
            okText="Revogar"
            okButtonProps={{ danger: true }}
            onConfirm={() => revoke.mutate(row.id)}
          >
            <Button danger icon={<StopOutlined />} loading={revoke.isPending}>
              Revogar
            </Button>
          </Popconfirm>
        ) : null,
    },
  ];

  return (
    <div className={styles.page}>
      <PageHeader
        title="Token de integração"
        description="Emita chaves para sites externos cadastrarem pessoas na base do tenant associado."
        actions={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              form.resetFields();
              setModalOpen(true);
            }}
          >
            Nova chave
          </Button>
        }
      />
      <Card size="small">
        <div className={styles.filters}>
          <Input.Search
            allowClear
            placeholder="Nome, tenant ou slug"
            onSearch={(query) => setFilters((value) => ({ ...value, query: query || undefined }))}
          />
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="Tenant"
            options={tenantOptions}
            onChange={(tenant_id) => setFilters((value) => ({ ...value, tenant_id }))}
          />
        </div>
      </Card>
      <Card className={styles.card}>
        <BaseTable
          rowKey="id"
          columns={columns}
          dataSource={keys.data?.items ?? []}
          loading={keys.isPending}
          error={keys.error ? normalizeApiError(keys.error).message : null}
          onRetry={() => keys.refetch()}
          pagination={{ pageSize: 20, total: keys.data?.total }}
        />
      </Card>
      <BaseModal
        isOpen={modalOpen}
        title="Nova chave de integração"
        confirmLoading={save.isPending}
        okText="Gerar chave"
        onOk={() => form.validateFields().then((values) => save.mutate(values))}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="tenant_id"
            label="Tenant"
            rules={[{ required: true, message: 'Selecione o tenant que receberá os cadastros.' }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="Selecione o tenant"
              loading={tenants.isPending}
              options={tenantOptions}
            />
          </Form.Item>
          <Form.Item
            name="nome"
            label="Nome da chave"
            rules={[{ required: true, min: 2, message: 'Informe um nome para identificar a chave.' }]}
          >
            <Input placeholder="Ex.: Site oficial da campanha" maxLength={120} />
          </Form.Item>
        </Form>
      </BaseModal>
      <BaseModal
        isOpen={createdKey !== null}
        title="Chave gerada"
        okText="Copiar e fechar"
        cancelText="Fechar"
        onOk={async () => {
          await copyToken();
          setCreatedKey(null);
        }}
        onCancel={() => setCreatedKey(null)}
      >
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="Copie agora. O valor completo não será exibido novamente."
          description="Use esta chave no cabeçalho Authorization: Bearer do POST /api/v1/cadastro/pessoas."
        />
        <Space.Compact style={{ width: '100%' }}>
          <Input.TextArea readOnly autoSize value={createdKey?.token} />
          <Button icon={<CopyOutlined />} onClick={() => void copyToken()}>
            Copiar
          </Button>
        </Space.Compact>
      </BaseModal>
    </div>
  );
}
