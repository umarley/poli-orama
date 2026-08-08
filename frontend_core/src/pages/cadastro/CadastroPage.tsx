import {
  MergeCellsOutlined,
  MoreOutlined,
  PlusOutlined,
  SearchOutlined,
  UserOutlined,
} from '@ant-design/icons';
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
import { useMemo, useState } from 'react';
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
import type { Lideranca, PessoaFilters, PessoaListItem } from '@/modules/cadastro/types';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';
import { formatInteger } from '@/utils/number-format';

import styles from './CadastroPage.module.css';
import { PessoaWizard } from './PessoaWizard';

function formatDocument(value: string | null): string {
  if (!value) return '—';
  const digits = value.replace(/\D/g, '');
  if (digits.length === 11) {
    return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`;
  }
  return value;
}

function formatPhone(value: string | null): string {
  if (!value) return 'Sem telefone';
  const digits = value.replace(/\D/g, '');
  const localDigits = digits.startsWith('55') && digits.length > 11 ? digits.slice(2) : digits;
  if (localDigits.length === 10) {
    return `(${localDigits.slice(0, 2)}) ${localDigits.slice(2, 6)}-${localDigits.slice(6)}`;
  }
  if (localDigits.length === 11) {
    return `(${localDigits.slice(0, 2)}) ${localDigits.slice(2, 7)}-${localDigits.slice(7)}`;
  }
  return value;
}

function formatLeadershipLabel(
  leadership: Pick<Lideranca, 'id' | 'pessoa_nome_completo' | 'apelido_campanha'>,
): string {
  const name = leadership.pessoa_nome_completo?.trim() || `Liderança #${leadership.id}`;
  const nickname = leadership.apelido_campanha?.trim();
  return nickname ? `${name} (${nickname})` : name;
}

export function CadastroPage() {
  const profiles = useSessionStore((state) => state.user?.profiles ?? []);
  const canMergeDuplicates = profiles.some((profile) =>
    ['gestor', 'gestor_saas'].includes(profile),
  );
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
    queryFn: () => listarLiderancas(),
  });
  const lideresResponsaveisQuery = useQuery({
    queryKey: ['cadastro', 'liderancas', { tipo_lideranca: 'lider' }],
    queryFn: () => listarLiderancas({ tipo_lideranca: 'lider' }),
  });
  const nomesLiderancas = useMemo(
    () =>
      new Map(
        liderancasQuery.data?.map((lideranca) => [
          lideranca.id,
          formatLeadershipLabel(lideranca),
        ]) ?? [],
      ),
    [liderancasQuery.data],
  );
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
            <Typography.Text type="secondary">{formatPhone(person.telefone)}</Typography.Text>
          </span>
        </button>
      ),
    },
    {
      title: 'Documento',
      dataIndex: 'cpf',
      key: 'cpf',
      render: (value: string | null) => formatDocument(value),
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
      render: (value: number | null) =>
        value ? (
          nomesLiderancas.get(value) || 'Liderança não encontrada'
        ) : (
          <Tag color="warning">Sem liderança</Tag>
        ),
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
                label: formatLeadershipLabel(item),
              }))}
              style={{ width: 280 }}
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
              {formatInteger(pessoasQuery.data?.total)} registros encontrados
            </Typography.Text>
          </div>
          <Space>
            <Button onClick={() => navigate('/cadastro/indicacoes')}>Rede de indicações</Button>
            <Button icon={<UserOutlined />} onClick={() => navigate('/cadastro/validacoes')}>
              Cadastros pendentes
            </Button>
            {canMergeDuplicates ? (
              <Button
                icon={<MergeCellsOutlined />}
                onClick={() => navigate('/cadastro/duplicidades')}
              >
                Duplicidades
              </Button>
            ) : null}
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
        liderancas={lideresResponsaveisQuery.data ?? []}
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
