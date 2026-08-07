import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  MergeCellsOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Descriptions,
  Drawer,
  Empty,
  Flex,
  Grid,
  Modal,
  Radio,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
} from 'antd';
import dayjs from 'dayjs';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  listarDuplicidades,
  mesclarDuplicidade,
  obterPreviewMerge,
  resolverDuplicidade,
} from '@/modules/cadastro/pessoas-service';
import type {
  CampoMergePessoa,
  CriterioDuplicidade,
  PessoaDetalhe,
  PessoaMergePreview,
  StatusDuplicidade,
  SuspeitaDuplicidade,
} from '@/modules/cadastro/types';
import { normalizeApiError } from '@/services/api/api-error';

import styles from './DuplicidadesPage.module.css';

const criterioLabels: Record<CriterioDuplicidade, string> = {
  cpf: 'CPF',
  telefone: 'Telefone',
  email: 'E-mail',
  titulo_eleitor: 'Título eleitoral',
  nome_data_nascimento: 'Nome e nascimento',
  fuzzy: 'Similaridade',
};

const statusConfig: Record<StatusDuplicidade, { label: string; color: string }> = {
  pendente: { label: 'Pendente', color: 'warning' },
  confirmada: { label: 'Confirmada', color: 'processing' },
  descartada: { label: 'Descartada', color: 'default' },
  mesclada: { label: 'Mesclada', color: 'success' },
};

const fieldLabels: Record<CampoMergePessoa, string> = {
  nome_completo: 'Nome completo',
  nome_social: 'Nome social',
  apelido: 'Apelido',
  sexo: 'Sexo',
  data_nascimento: 'Data de nascimento',
  estado_civil: 'Estado civil',
  escolaridade_id: 'Escolaridade',
  profissao_id: 'Profissão',
  religiao_id: 'Religião',
  observacoes: 'Observações',
};

const sexLabels: Record<string, string> = {
  M: 'Masculino',
  F: 'Feminino',
  O: 'Outro',
  N: 'Não informado',
};

function displayValue(field: CampoMergePessoa, value: unknown): string {
  if (value === null || value === undefined || value === '') return 'Não informado';
  if (field === 'data_nascimento' && typeof value === 'string') {
    return dayjs(value).format('DD/MM/YYYY');
  }
  if (field === 'sexo' && typeof value === 'string') return sexLabels[value] ?? value;
  return String(value);
}

function personName(item: SuspeitaDuplicidade, side: 'a' | 'b') {
  return side === 'a'
    ? item.pessoa_nome || `Cadastro #${item.pessoa_id}`
    : item.pessoa_duplicada_nome || `Cadastro #${item.pessoa_duplicada_id}`;
}

function PersonCard({
  person,
  selected,
  onSelect,
}: {
  person: PessoaDetalhe;
  selected: boolean;
  onSelect: () => void;
}) {
  const cpf = person.documentos.find((item) => item.tipo_documento === 'cpf')?.numero;
  const title = person.eleitor?.titulo_eleitor;
  const contacts = person.contatos.slice(0, 3);

  return (
    <Card
      className={`${styles.personCard} ${selected ? styles.personCardSelected : ''}`}
      onClick={onSelect}
      title={
        <div className={styles.personTitle}>
          <Radio checked={selected} onChange={onSelect} />
          <span className={styles.personTitleText}>{person.nome_completo}</span>
        </div>
      }
      extra={
        <Link
          to={`/cadastro/pessoas/${person.id}`}
          target="_blank"
          onClick={(event) => event.stopPropagation()}
        >
          Abrir cadastro
        </Link>
      }
    >
      <Descriptions size="small" column={1} colon={false}>
        <Descriptions.Item label="Cadastro">#{person.id}</Descriptions.Item>
        <Descriptions.Item label="Nascimento">
          {person.data_nascimento ? dayjs(person.data_nascimento).format('DD/MM/YYYY') : '—'}
        </Descriptions.Item>
        <Descriptions.Item label="CPF">{cpf || '—'}</Descriptions.Item>
        <Descriptions.Item label="Título eleitoral">{title || '—'}</Descriptions.Item>
      </Descriptions>
      <div className={styles.dataList}>
        <Typography.Text type="secondary">Contatos</Typography.Text>
        {contacts.length > 0 ? (
          contacts.map((contact) => (
            <div className={styles.dataLine} key={contact.id}>
              <Typography.Text>{contact.tipo_contato.replaceAll('_', ' ')}</Typography.Text>
              <Typography.Text className={styles.dataValue}>{contact.valor}</Typography.Text>
            </div>
          ))
        ) : (
          <Typography.Text type="secondary">Nenhum contato</Typography.Text>
        )}
      </div>
      <Space wrap style={{ marginTop: 14 }}>
        <Tag>{person.documentos.length} documento(s)</Tag>
        <Tag>{person.enderecos.length} endereço(s)</Tag>
        <Tag>{person.tags.length} tag(s)</Tag>
      </Space>
    </Card>
  );
}

function MergeReview({
  preview,
  principalId,
  choices,
  onPrincipalChange,
  onChoiceChange,
}: {
  preview: PessoaMergePreview;
  principalId: number;
  choices: Partial<Record<CampoMergePessoa, number>>;
  onPrincipalChange: (id: number) => void;
  onChoiceChange: (field: CampoMergePessoa, personId: number) => void;
}) {
  return (
    <>
      <Alert
        type="info"
        showIcon
        message="Escolha o cadastro principal"
        description="Ele permanecerá ativo. Vínculos e dados não repetidos do outro cadastro serão incorporados automaticamente."
      />
      <div className={styles.peopleGrid}>
        <PersonCard
          person={preview.pessoa_a}
          selected={principalId === preview.pessoa_a.id}
          onSelect={() => onPrincipalChange(preview.pessoa_a.id)}
        />
        <PersonCard
          person={preview.pessoa_b}
          selected={principalId === preview.pessoa_b.id}
          onSelect={() => onPrincipalChange(preview.pessoa_b.id)}
        />
      </div>

      <div>
        <div className={styles.sectionHeading}>
          <Typography.Title level={5} style={{ margin: 0 }}>
            Resolver campos conflitantes
          </Typography.Title>
          <Typography.Text type="secondary">
            {preview.conflitos.length} diferença(s)
          </Typography.Text>
        </div>
        {preview.conflitos.length > 0 ? (
          <Table
            className={styles.comparisonTable}
            style={{ marginTop: 12 }}
            rowKey="campo"
            pagination={false}
            scroll={{ x: 760 }}
            dataSource={preview.conflitos}
            columns={[
              {
                title: 'Campo',
                dataIndex: 'campo',
                width: 170,
                render: (field: CampoMergePessoa) => fieldLabels[field],
              },
              {
                title: preview.pessoa_a.nome_completo,
                render: (_, conflict) => (
                  <label className={styles.choice}>
                    <Radio
                      checked={
                        (choices[conflict.campo] ?? preview.pessoa_a.id) === preview.pessoa_a.id
                      }
                      onChange={() => onChoiceChange(conflict.campo, preview.pessoa_a.id)}
                    />
                    <span className={styles.choiceValue}>
                      {displayValue(conflict.campo, conflict.valor_principal)}
                    </span>
                  </label>
                ),
              },
              {
                title: preview.pessoa_b.nome_completo,
                render: (_, conflict) => (
                  <label className={styles.choice}>
                    <Radio
                      checked={
                        (choices[conflict.campo] ?? preview.pessoa_a.id) === preview.pessoa_b.id
                      }
                      onChange={() => onChoiceChange(conflict.campo, preview.pessoa_b.id)}
                    />
                    <span className={styles.choiceValue}>
                      {displayValue(conflict.campo, conflict.valor_origem)}
                    </span>
                  </label>
                ),
              },
            ]}
          />
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="Não há diferenças nos campos básicos. Os vínculos ainda serão consolidados."
          />
        )}
      </div>
    </>
  );
}

export function DuplicidadesPage() {
  const queryClient = useQueryClient();
  const screens = Grid.useBreakpoint();
  const [status, setStatus] = useState<StatusDuplicidade>('pendente');
  const [selected, setSelected] = useState<SuspeitaDuplicidade | null>(null);
  const [principalId, setPrincipalId] = useState<number | null>(null);
  const [choices, setChoices] = useState<Partial<Record<CampoMergePessoa, number>>>({});
  const [confirmed, setConfirmed] = useState(false);

  const duplicatesQuery = useQuery({
    queryKey: ['cadastro', 'duplicidades', status],
    queryFn: () => listarDuplicidades(status),
  });
  const previewQuery = useQuery({
    queryKey: ['cadastro', 'duplicidades', selected?.id, 'preview'],
    queryFn: () => obterPreviewMerge(selected!.id),
    enabled: Boolean(selected),
    retry: false,
  });

  const resolveMutation = useMutation({
    mutationFn: ({
      item,
      decision,
    }: {
      item: SuspeitaDuplicidade;
      decision: 'duplicado' | 'falso_positivo' | 'pendente';
    }) => resolverDuplicidade(item.id, decision),
    onSuccess: async (_, variables) => {
      AppToast.success(
        variables.decision === 'falso_positivo'
          ? 'Suspeita descartada como falso positivo.'
          : 'Duplicidade confirmada para análise.',
      );
      if (variables.item.id === selected?.id && variables.decision === 'falso_positivo') {
        setSelected(null);
      }
      await queryClient.invalidateQueries({ queryKey: ['cadastro', 'duplicidades'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const mergeMutation = useMutation({
    mutationFn: async () => {
      const preview = previewQuery.data;
      const effectivePrincipalId = principalId ?? preview?.pessoa_a.id;
      if (!selected || !preview || !effectivePrincipalId) {
        throw new Error('Seleção de merge incompleta.');
      }
      const sourceId =
        effectivePrincipalId === preview.pessoa_a.id ? preview.pessoa_b.id : preview.pessoa_a.id;
      const sourceFields = preview.conflitos
        .filter((conflict) => (choices[conflict.campo] ?? preview.pessoa_a.id) === sourceId)
        .map((conflict) => conflict.campo);
      return mesclarDuplicidade(selected.id, {
        pessoa_principal_id: effectivePrincipalId,
        campos_origem: sourceFields,
        confirmar: true,
      });
    },
    onSuccess: async (result) => {
      AppToast.success(
        `Cadastros mesclados. O cadastro #${result.pessoa_principal.id} foi mantido.`,
      );
      setSelected(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['cadastro', 'duplicidades'] }),
        queryClient.invalidateQueries({ queryKey: ['cadastro', 'pessoas'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
      ]);
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const counts = useMemo(
    () => ({ visible: duplicatesQuery.data?.length ?? 0 }),
    [duplicatesQuery.data],
  );

  const discard = (item: SuspeitaDuplicidade) => {
    Modal.confirm({
      title: 'Descartar suspeita?',
      content:
        'Os dois cadastros serão mantidos separados e esta ocorrência sairá da fila pendente.',
      okText: 'Descartar como falso positivo',
      cancelText: 'Cancelar',
      onOk: () => resolveMutation.mutateAsync({ item, decision: 'falso_positivo' }),
    });
  };

  const openReview = (item: SuspeitaDuplicidade) => {
    setSelected(item);
    setPrincipalId(null);
    setChoices({});
    setConfirmed(false);
  };

  const preview = previewQuery.data;
  const effectivePrincipalId = principalId ?? preview?.pessoa_a.id ?? null;

  return (
    <div className={styles.page}>
      <PageHeader
        title="Duplicidades de pessoas"
        description="Revise cadastros suspeitos, escolha os dados corretos e faça a consolidação com segurança."
        breadcrumbs={[{ label: 'Cadastro', to: '/cadastro' }, { label: 'Duplicidades' }]}
      />

      <Card>
        <div className={styles.toolbar}>
          <Select<StatusDuplicidade>
            aria-label="Filtrar por situação"
            value={status}
            onChange={setStatus}
            style={{ minWidth: 220 }}
            options={Object.entries(statusConfig).map(([value, config]) => ({
              value: value as StatusDuplicidade,
              label: config.label,
            }))}
          />
          <Space>
            <Typography.Text type="secondary">{counts.visible} ocorrência(s)</Typography.Text>
            <Button
              icon={<ReloadOutlined />}
              loading={duplicatesQuery.isFetching}
              onClick={() => duplicatesQuery.refetch()}
            >
              Atualizar
            </Button>
          </Space>
        </div>

        {duplicatesQuery.isError ? (
          <Alert
            type="error"
            showIcon
            message="Não foi possível carregar as duplicidades"
            description={normalizeApiError(duplicatesQuery.error).message}
          />
        ) : (
          <Table<SuspeitaDuplicidade>
            rowKey="id"
            loading={duplicatesQuery.isPending}
            dataSource={duplicatesQuery.data ?? []}
            pagination={{ pageSize: 20, hideOnSinglePage: true }}
            scroll={{ x: 900 }}
            locale={{ emptyText: 'Nenhuma ocorrência nesta situação.' }}
            columns={[
              {
                title: 'Cadastros comparados',
                render: (_, item) => (
                  <div className={styles.pairCell}>
                    <div className={styles.pairLine}>
                      <Link to={`/cadastro/pessoas/${item.pessoa_id}`}>
                        {personName(item, 'a')}
                      </Link>
                      <Typography.Text type="secondary">#{item.pessoa_id}</Typography.Text>
                    </div>
                    <Typography.Text type="secondary">comparado com</Typography.Text>
                    <div className={styles.pairLine}>
                      <Link to={`/cadastro/pessoas/${item.pessoa_duplicada_id}`}>
                        {personName(item, 'b')}
                      </Link>
                      <Typography.Text type="secondary">
                        #{item.pessoa_duplicada_id}
                      </Typography.Text>
                    </div>
                  </div>
                ),
              },
              {
                title: 'Critério',
                dataIndex: 'criterio',
                render: (criterion: CriterioDuplicidade) => (
                  <Tag color="blue">{criterioLabels[criterion]}</Tag>
                ),
              },
              {
                title: 'Similaridade',
                dataIndex: 'score_similaridade',
                align: 'center',
                render: (value: string | null) => (value ? `${Number(value).toFixed(0)}%` : '—'),
              },
              {
                title: 'Situação',
                dataIndex: 'status',
                render: (value: StatusDuplicidade) => (
                  <Tag color={statusConfig[value].color}>{statusConfig[value].label}</Tag>
                ),
              },
              {
                title: 'Identificada em',
                dataIndex: 'criado_em',
                render: (value: string) => dayjs(value).format('DD/MM/YYYY HH:mm'),
              },
              {
                title: 'Ações',
                fixed: 'right',
                width: 300,
                render: (_, item) =>
                  item.status === 'pendente' || item.status === 'confirmada' ? (
                    <Space wrap>
                      <Button
                        type="primary"
                        size="small"
                        icon={<MergeCellsOutlined />}
                        onClick={() => openReview(item)}
                      >
                        Analisar merge
                      </Button>
                      {item.status === 'pendente' ? (
                        <Button
                          size="small"
                          icon={<CheckCircleOutlined />}
                          loading={resolveMutation.isPending}
                          onClick={() => resolveMutation.mutate({ item, decision: 'duplicado' })}
                        >
                          Confirmar
                        </Button>
                      ) : null}
                      <Button
                        size="small"
                        icon={<CloseCircleOutlined />}
                        onClick={() => discard(item)}
                      >
                        Descartar
                      </Button>
                    </Space>
                  ) : (
                    <Typography.Text type="secondary">Ocorrência encerrada</Typography.Text>
                  ),
              },
            ]}
          />
        )}
      </Card>

      <Drawer
        open={Boolean(selected)}
        destroyOnHidden
        width={screens.lg ? 1080 : '100%'}
        title={
          <Space>
            <SafetyCertificateOutlined />
            Merge assistido
            {selected ? <Typography.Text type="secondary">#{selected.id}</Typography.Text> : null}
          </Space>
        }
        onClose={() => setSelected(null)}
        extra={
          <Space>
            <Button onClick={() => setSelected(null)}>Cancelar</Button>
            <Button
              type="primary"
              icon={<MergeCellsOutlined />}
              disabled={!preview || !effectivePrincipalId || !confirmed}
              loading={mergeMutation.isPending}
              onClick={() => mergeMutation.mutate()}
            >
              Confirmar merge
            </Button>
          </Space>
        }
      >
        <div className={styles.drawerContent}>
          {selected ? (
            <Alert
              type="warning"
              showIcon
              message={`Suspeita por ${criterioLabels[selected.criterio]}`}
              description="O merge inativa o cadastro de origem e não pode ser desfeito automaticamente. A operação ficará registrada na auditoria."
            />
          ) : null}

          {previewQuery.isPending ? (
            <Flex justify="center" style={{ padding: 48 }}>
              <Spin size="large" tip="Carregando os dois cadastros..." />
            </Flex>
          ) : previewQuery.isError ? (
            <Alert
              type="error"
              showIcon
              message="Não foi possível preparar o merge"
              description={normalizeApiError(previewQuery.error).message}
              action={<Button onClick={() => previewQuery.refetch()}>Tentar novamente</Button>}
            />
          ) : preview && effectivePrincipalId ? (
            <>
              <MergeReview
                preview={preview}
                principalId={effectivePrincipalId}
                choices={choices}
                onPrincipalChange={setPrincipalId}
                onChoiceChange={(field, personId) =>
                  setChoices((current) => ({ ...current, [field]: personId }))
                }
              />
              <div className={styles.confirmBox}>
                <Checkbox
                  checked={confirmed}
                  onChange={(event) => setConfirmed(event.target.checked)}
                >
                  Revisei os dados, escolhi o cadastro principal e estou ciente de que o cadastro de
                  origem será inativado.
                </Checkbox>
              </div>
            </>
          ) : null}
        </div>
      </Drawer>
    </div>
  );
}
