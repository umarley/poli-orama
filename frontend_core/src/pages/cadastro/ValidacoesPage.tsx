import { CheckOutlined, CloseOutlined, TeamOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Card, Form, Modal, Select, Space, Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { AppToast } from '@/components/feedback/AppToast';
import { LocalizedStatistic as Statistic } from '@/components/data/LocalizedStatistic';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  criarHierarquia,
  listarLiderancas,
  listarPessoas,
  listarValidacoes,
  resolverValidacao,
} from '@/modules/cadastro/pessoas-service';
import type { Lideranca, ValidacaoCadastro } from '@/modules/cadastro/types';
import { normalizeApiError } from '@/services/api/api-error';

function formatLeadershipLabel(
  leadership: Pick<Lideranca, 'id' | 'pessoa_id' | 'pessoa_nome_completo' | 'apelido_campanha'>,
  personName?: string,
): string {
  const name =
    leadership.pessoa_nome_completo?.trim() || personName?.trim() || `Liderança #${leadership.id}`;
  const nickname = leadership.apelido_campanha?.trim();
  return nickname ? `${name} (${nickname})` : name;
}

export function ValidacoesPage() {
  const queryClient = useQueryClient();
  const [assigning, setAssigning] = useState<ValidacaoCadastro | null>(null);
  const [form] = Form.useForm<{ lideranca_id: number }>();
  const validationsQuery = useQuery({
    queryKey: ['cadastro', 'validacoes', 'pendente'],
    queryFn: () => listarValidacoes('pendente'),
  });
  const peopleQuery = useQuery({
    queryKey: ['cadastro', 'pessoas', 'validation-options'],
    queryFn: () => listarPessoas({ page: 1, page_size: 100, incluir_inativos: true }),
  });
  const leadersQuery = useQuery({
    queryKey: ['cadastro', 'liderancas'],
    queryFn: () => listarLiderancas(),
  });
  const peopleById = useMemo(
    () => new Map((peopleQuery.data?.items ?? []).map((person) => [person.id, person])),
    [peopleQuery.data],
  );
  const resolveMutation = useMutation({
    mutationFn: ({
      item,
      status,
    }: {
      item: ValidacaoCadastro;
      status: 'aprovado' | 'rejeitado' | 'em_revisao';
    }) => resolverValidacao(item.id, status),
    onSuccess: async () => {
      AppToast.success('Validação atualizada.');
      await queryClient.invalidateQueries({ queryKey: ['cadastro', 'validacoes'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const assignMutation = useMutation({
    mutationFn: async ({ lideranca_id }: { lideranca_id: number }) => {
      if (!assigning) return;
      await criarHierarquia({
        lideranca_superior_id: lideranca_id,
        pessoa_subordinada_id: assigning.pessoa_id,
        papel_subordinado: 'liderado',
        data_inicio: new Date().toISOString().slice(0, 10),
        data_fim: null,
        ativo: true,
      });
      await resolverValidacao(assigning.id, 'aprovado', 'Liderança atribuída.');
    },
    onSuccess: async () => {
      AppToast.success('Liderança atribuída e cadastro aprovado.');
      setAssigning(null);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['cadastro'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const confirmReject = (item: ValidacaoCadastro) => {
    Modal.confirm({
      title: 'Rejeitar cadastro',
      content: 'Tem certeza de que deseja rejeitar este cadastro?',
      okText: 'Sim, rejeitar',
      cancelText: 'Cancelar',
      okButtonProps: { danger: true },
      onOk: () => resolveMutation.mutateAsync({ item, status: 'rejeitado' }),
    });
  };

  return (
    <div>
      <PageHeader
        title="Validação de cadastros"
        description="Pendências, cadastros sem liderança e registros que exigem revisão."
        breadcrumbs={[{ label: 'Cadastro', to: '/cadastro' }, { label: 'Validações pendentes' }]}
      />
      <Space size={16} wrap style={{ marginBottom: 20 }}>
        <Card loading={validationsQuery.isPending}>
          <Statistic title="Cadastros para validar" value={validationsQuery.data?.length ?? 0} />
        </Card>
      </Space>
      <Card>
        <Table<ValidacaoCadastro>
          rowKey="id"
          dataSource={validationsQuery.data ?? []}
          loading={validationsQuery.isPending}
          pagination={{ pageSize: 20 }}
          columns={[
            {
              title: 'Pessoa',
              dataIndex: 'pessoa_id',
              render: (id: number, item) => (
                <div>
                  <Link to={`/cadastro/pessoas/${id}`}>
                    {item.pessoa_nome || peopleById.get(id)?.nome_completo || `Pessoa #${id}`}
                  </Link>
                  <Typography.Text type="secondary" style={{ display: 'block' }}>
                    Cadastro #{id}
                  </Typography.Text>
                </div>
              ),
            },
            {
              title: 'Pendência',
              dataIndex: 'motivo',
              render: (value: string) => (
                <Tag color={value === 'sem_lider' ? 'warning' : 'blue'}>
                  {value.replaceAll('_', ' ')}
                </Tag>
              ),
            },
            { title: 'Observação', dataIndex: 'observacao', render: (value) => value || '—' },
            {
              title: 'Criado em',
              dataIndex: 'criado_em',
              render: (value: string) => dayjs(value).format('DD/MM/YYYY HH:mm:ss'),
            },
            {
              title: 'Ações',
              render: (_, item) => (
                <Space wrap>
                  <Button
                    size="small"
                    type="primary"
                    icon={<CheckOutlined />}
                    onClick={() => resolveMutation.mutate({ item, status: 'aprovado' })}
                  >
                    Aprovar
                  </Button>
                  <Button size="small" icon={<TeamOutlined />} onClick={() => setAssigning(item)}>
                    Atribuir líder
                  </Button>
                  <Button
                    size="small"
                    danger
                    icon={<CloseOutlined />}
                    onClick={() => confirmReject(item)}
                  >
                    Rejeitar
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>
      <Modal
        open={Boolean(assigning)}
        title="Atribuir liderança responsável"
        okText="Atribuir e aprovar"
        confirmLoading={assignMutation.isPending}
        onCancel={() => setAssigning(null)}
        onOk={() => form.validateFields().then((values) => assignMutation.mutate(values))}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="lideranca_id" label="Liderança" rules={[{ required: true }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={(leadersQuery.data ?? []).map((item) => ({
                value: item.id,
                label: formatLeadershipLabel(item, peopleById.get(item.pessoa_id)?.nome_completo),
              }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
