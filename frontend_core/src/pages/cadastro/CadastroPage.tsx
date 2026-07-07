import { MoreOutlined, PlusOutlined, SearchOutlined, UserOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  Dropdown,
  Form,
  Input,
  Popconfirm,
  Select,
  Space,
  Tag,
  Typography,
} from 'antd';
import type { TableProps } from 'antd';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { BaseTable } from '@/components/data/BaseTable';
import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import { TerritorySelect } from '@/components/territorios/TerritorySelect';
import {
  inativarPessoa,
  listarEstadosCivis,
  listarLiderancas,
  listarPessoas,
  listarTags,
  listarTiposPessoa,
} from '@/modules/cadastro/pessoas-service';
import type { PessoaFilters, PessoaListItem } from '@/modules/cadastro/types';
import { normalizeApiError } from '@/services/api/api-error';

import styles from './CadastroPage.module.css';
import { PessoaWizard } from './PessoaWizard';

export function CadastroPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form] = Form.useForm<PessoaFilters>();
  const [filters, setFilters] = useState<PessoaFilters>({ page: 1, page_size: 10 });
  const [wizardOpen, setWizardOpen] = useState(false);

  const pessoasQuery = useQuery({
    queryKey: ['cadastro', 'pessoas', filters],
    queryFn: () => listarPessoas(filters),
  });
  const tiposQuery = useQuery({ queryKey: ['cadastro', 'tipos'], queryFn: listarTiposPessoa });
  const estadosCivisQuery = useQuery({
    queryKey: ['cadastro', 'estados-civis'],
    queryFn: listarEstadosCivis,
  });
  const tagsQuery = useQuery({ queryKey: ['cadastro', 'tags'], queryFn: listarTags });
  const liderancasQuery = useQuery({
    queryKey: ['cadastro', 'liderancas'],
    queryFn: listarLiderancas,
  });
  const deactivateMutation = useMutation({
    mutationFn: inativarPessoa,
    onSuccess: async () => {
      AppToast.success('Cadastro inativado.');
      await queryClient.invalidateQueries({ queryKey: ['cadastro', 'pessoas'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const columns: TableProps<PessoaListItem>['columns'] = [
    {
      title: 'Pessoa',
      dataIndex: 'nome_completo',
      key: 'nome_completo',
      render: (name: string, person) => (
        <button
          type="button"
          className={styles.personButton}
          onClick={() => navigate(`/cadastro/pessoas/${person.id}`)}
        >
          <span className={styles.personAvatar}>
            {name
              .split(' ')
              .slice(0, 2)
              .map((part) => part[0])
              .join('')}
          </span>
          <span>
            <strong>{name}</strong>
            <Typography.Text type="secondary">{person.telefone || 'Sem telefone'}</Typography.Text>
          </span>
        </button>
      ),
    },
    {
      title: 'Documento',
      dataIndex: 'cpf',
      key: 'cpf',
      render: (value: string | null) => value || '—',
    },
    {
      title: 'Classificação',
      dataIndex: 'tipos',
      key: 'tipos',
      render: (values: string[]) =>
        values.length ? values.slice(0, 3).map((value) => <Tag key={value}>{value}</Tag>) : '—',
    },
    {
      title: 'Liderança',
      dataIndex: 'lideranca_id',
      key: 'lideranca_id',
      render: (value: number | null) => (value ? `#${value}` : <Tag color="warning">Pendente</Tag>),
    },
    {
      title: 'Status',
      dataIndex: 'ativo',
      key: 'ativo',
      render: (active: boolean) => (
        <Tag color={active ? 'success' : 'default'}>{active ? 'Ativo' : 'Inativo'}</Tag>
      ),
    },
    {
      title: '',
      key: 'actions',
      width: 52,
      fixed: 'right',
      render: (_, person) => (
        <Dropdown
          trigger={['click']}
          menu={{
            items: [
              {
                key: 'view',
                label: 'Ver detalhes',
                onClick: () => navigate(`/cadastro/pessoas/${person.id}`),
              },
              {
                key: 'deactivate',
                danger: true,
                disabled: !person.ativo,
                label: (
                  <Popconfirm
                    title="Inativar cadastro?"
                    description="O histórico será preservado."
                    onConfirm={() => deactivateMutation.mutate(person.id)}
                  >
                    <span>Inativar</span>
                  </Popconfirm>
                ),
              },
            ],
          }}
        >
          <Button
            type="text"
            icon={<MoreOutlined />}
            aria-label={`Ações de ${person.nome_completo}`}
          />
        </Dropdown>
      ),
    },
  ];

  return (
    <div className={styles.page}>
      <PageHeader
        title="Pessoas e eleitores"
        description="Cadastros, contatos, vínculos de liderança e segmentação da campanha."
        breadcrumbs={[
          { label: 'Início', to: '/dashboard' },
          { label: 'Cadastro' },
          { label: 'Pessoas e eleitores' },
        ]}
        actions={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setWizardOpen(true)}>
            Nova pessoa
          </Button>
        }
      />

      <Card size="small">
        <Form
          form={form}
          layout="inline"
          onFinish={(values) =>
            setFilters({ ...values, page: 1, page_size: filters.page_size ?? 10 })
          }
          className={styles.filters}
        >
          <Form.Item name="query" className={styles.searchField}>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="Nome, documento ou telefone"
            />
          </Form.Item>
          <Form.Item name="tipo_id">
            <Select
              allowClear
              placeholder="Tipo"
              options={tiposQuery.data?.map((item) => ({ value: item.id, label: item.nome }))}
              style={{ width: 150 }}
            />
          </Form.Item>
          <Form.Item name="lideranca_id">
            <Select
              allowClear
              placeholder="Liderança"
              options={liderancasQuery.data?.map((item) => ({
                value: item.id,
                label: item.apelido_campanha || `Liderança #${item.id}`,
              }))}
              style={{ width: 170 }}
            />
          </Form.Item>
          <Form.Item name="tag_id">
            <Select
              allowClear
              placeholder="Tag"
              options={tagsQuery.data?.map((item) => ({ value: item.id, label: item.nome }))}
              style={{ width: 140 }}
            />
          </Form.Item>
          <Form.Item name="territorio_id">
            <TerritorySelect style={{ width: 220 }} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={pessoasQuery.isFetching}>
                Filtrar
              </Button>
              <Button
                onClick={() => {
                  form.resetFields();
                  setFilters({ page: 1, page_size: 10 });
                }}
              >
                Limpar
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <div className={styles.tableCard}>
        <div className={styles.tableHeading}>
          <div>
            <strong>Base de pessoas</strong>
            <Typography.Text type="secondary">
              {pessoasQuery.data?.total ?? 0} registros encontrados
            </Typography.Text>
          </div>
          <Space>
            <Button onClick={() => navigate('/cadastro/indicacoes')}>Rede de indicações</Button>
            <Button icon={<UserOutlined />} onClick={() => navigate('/cadastro/validacoes')}>
              Cadastros pendentes
            </Button>
          </Space>
        </div>
        <BaseTable<PessoaListItem>
          rowKey="id"
          columns={columns}
          dataSource={pessoasQuery.data?.items ?? []}
          loading={pessoasQuery.isPending}
          error={pessoasQuery.error ? normalizeApiError(pessoasQuery.error).message : null}
          onRetry={() => pessoasQuery.refetch()}
          pagination={{
            current: filters.page,
            pageSize: filters.page_size,
            total: pessoasQuery.data?.total,
            showSizeChanger: true,
            onChange: (page, pageSize) =>
              setFilters((current) => ({ ...current, page, page_size: pageSize })),
          }}
        />
      </div>

      <PessoaWizard
        open={wizardOpen}
        tipos={tiposQuery.data ?? []}
        liderancas={liderancasQuery.data ?? []}
        estadosCivis={estadosCivisQuery.data ?? []}
        onClose={() => setWizardOpen(false)}
        onCreated={(id) => {
          void queryClient.invalidateQueries({ queryKey: ['cadastro', 'pessoas'] });
          navigate(`/cadastro/pessoas/${id}`);
        }}
      />
    </div>
  );
}
