import { MoreOutlined, PlusOutlined } from '@ant-design/icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Dropdown, Form, Input, Popconfirm, Select, Space, Tag, Typography } from 'antd';
import type { TableProps } from 'antd';
import { useState } from 'react';

import { BaseTable } from '@/components/data/BaseTable';
import { AppToast } from '@/components/feedback/AppToast';
import { BaseModal } from '@/components/feedback/BaseModal';
import { BaseFilterBar, type FilterValues } from '@/components/form/BaseFilterBar';
import { BaseForm } from '@/components/form/BaseForm';
import { PageHeader } from '@/components/layout/PageHeader';
import { listarPessoas } from '@/modules/cadastro/pessoas-service';
import type { Pessoa } from '@/modules/cadastro/types';
import { normalizeApiError } from '@/services/api/api-error';

import styles from './CadastroPage.module.css';

interface PessoaForm {
  nome: string;
  telefone: string;
  bairro: string;
  lideranca?: string;
}

export function CadastroPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<FilterValues>({});
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm<PessoaForm>();

  const pessoasQuery = useQuery({
    queryKey: ['pessoas', filters],
    queryFn: () => listarPessoas(filters),
  });

  const columns: TableProps<Pessoa>['columns'] = [
    {
      title: 'Pessoa',
      dataIndex: 'nome',
      key: 'nome',
      render: (nome: string, pessoa) => (
        <div className={styles.personCell}>
          <span className={styles.personAvatar}>
            {nome
              .split(' ')
              .slice(0, 2)
              .map((part) => part[0])
              .join('')}
          </span>
          <div>
            <strong>{nome}</strong>
            <Typography.Text type="secondary">{pessoa.telefone}</Typography.Text>
          </div>
        </div>
      ),
    },
    { title: 'Bairro', dataIndex: 'bairro', key: 'bairro' },
    { title: 'Liderança', dataIndex: 'lideranca', key: 'lideranca' },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: Pessoa['status']) => (
        <Tag color={status === 'ativo' ? 'success' : 'default'}>
          {status === 'ativo' ? 'Ativo' : 'Inativo'}
        </Tag>
      ),
    },
    { title: 'Atualização', dataIndex: 'atualizadoEm', key: 'atualizadoEm' },
    {
      title: '',
      key: 'actions',
      width: 48,
      fixed: 'right',
      render: (_, pessoa) => (
        <Dropdown
          trigger={['click']}
          menu={{
            items: [
              { key: 'view', label: 'Ver detalhes' },
              { key: 'edit', label: 'Editar cadastro' },
              {
                key: 'delete',
                danger: true,
                label: (
                  <Popconfirm
                    title="Remover cadastro?"
                    description={`Esta ação removeria ${pessoa.nome}.`}
                    onConfirm={() => AppToast.success('Ação demonstrativa concluída.')}
                  >
                    <span>Remover</span>
                  </Popconfirm>
                ),
              },
            ],
          }}
        >
          <Button type="text" icon={<MoreOutlined />} aria-label={`Ações de ${pessoa.nome}`} />
        </Dropdown>
      ),
    },
  ];

  const handleCreate = async () => {
    const values = await form.validateFields();
    AppToast.success(`${values.nome} foi adicionado à base.`);
    setModalOpen(false);
    form.resetFields();
    await queryClient.invalidateQueries({ queryKey: ['pessoas'] });
  };

  return (
    <div className={styles.page}>
      <PageHeader
        title="Pessoas e eleitores"
        description="Gerencie a base de contatos e os vínculos territoriais da campanha."
        breadcrumbs={[
          { label: 'Início', to: '/dashboard' },
          { label: 'Cadastro' },
          { label: 'Pessoas e eleitores' },
        ]}
        actions={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            Nova pessoa
          </Button>
        }
      />

      <BaseFilterBar
        initialValues={filters}
        loading={pessoasQuery.isFetching}
        onFilter={setFilters}
        onClear={() => setFilters({})}
      />

      <div className={styles.tableCard}>
        <div className={styles.tableHeading}>
          <div>
            <strong>Base de pessoas</strong>
            <Typography.Text type="secondary">
              {pessoasQuery.data?.total ?? 0} registros encontrados
            </Typography.Text>
          </div>
          <Button>Exportar</Button>
        </div>
        <BaseTable<Pessoa>
          rowKey="id"
          columns={columns}
          dataSource={pessoasQuery.data?.items ?? []}
          loading={pessoasQuery.isPending}
          error={pessoasQuery.error ? normalizeApiError(pessoasQuery.error).message : null}
          onRetry={() => pessoasQuery.refetch()}
          pagination={{
            pageSize: 10,
            total: pessoasQuery.data?.total,
            showSizeChanger: false,
          }}
        />
      </div>

      <BaseModal
        isOpen={modalOpen}
        title="Nova pessoa"
        okText="Salvar cadastro"
        cancelText="Cancelar"
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
      >
        <BaseForm<PessoaForm> form={form} className={styles.modalForm}>
          <Form.Item
            name="nome"
            label="Nome completo"
            rules={[{ required: true, message: 'Informe o nome completo.' }]}
          >
            <Input placeholder="Digite o nome" />
          </Form.Item>
          <Space.Compact block>
            <Form.Item
              name="telefone"
              label="Telefone"
              rules={[{ required: true, message: 'Informe o telefone.' }]}
              className={styles.compactField}
            >
              <Input placeholder="(00) 00000-0000" />
            </Form.Item>
            <Form.Item
              name="bairro"
              label="Bairro"
              rules={[{ required: true, message: 'Informe o bairro.' }]}
              className={styles.compactField}
            >
              <Input placeholder="Bairro" />
            </Form.Item>
          </Space.Compact>
          <Form.Item name="lideranca" label="Liderança responsável">
            <Select
              allowClear
              placeholder="Selecione uma liderança"
              options={[
                { value: 'Carlos Mendes', label: 'Carlos Mendes' },
                { value: 'Juliana Rocha', label: 'Juliana Rocha' },
                { value: 'Fernanda Reis', label: 'Fernanda Reis' },
              ]}
            />
          </Form.Item>
        </BaseForm>
      </BaseModal>
    </div>
  );
}
