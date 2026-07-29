import {
  MessageOutlined,
  PhoneOutlined,
  PlusOutlined,
  SendOutlined,
  UserSwitchOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  Empty,
  Form,
  Input,
  List,
  Modal,
  Select,
  Space,
  Tag,
  Timeline,
  Typography,
} from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';

import { AppToast } from '@/components/feedback/AppToast';
import {
  listarCanaisComunicacao,
  listarInteracoesPessoa,
  listarTiposInteracao,
  registrarInteracaoPessoa,
} from '@/modules/comunicacao/comunicacao-service';
import type { InteracaoInput } from '@/modules/comunicacao/types';
import { normalizeApiError } from '@/services/api/api-error';

interface Props {
  pessoaId: number;
  canCreate: boolean;
}

export function PersonInteractionsPanel({ pessoaId, canCreate }: Props) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm<InteracaoInput>();
  const interactions = useQuery({
    queryKey: ['comunicacao', 'pessoa', pessoaId, 'interacoes'],
    queryFn: () => listarInteracoesPessoa(pessoaId),
  });
  const types = useQuery({
    queryKey: ['comunicacao', 'tipos-interacao'],
    queryFn: listarTiposInteracao,
  });
  const channels = useQuery({
    queryKey: ['comunicacao', 'canais'],
    queryFn: listarCanaisComunicacao,
  });
  const createMutation = useMutation({
    mutationFn: (values: InteracaoInput) => registrarInteracaoPessoa(pessoaId, values),
    onSuccess: async () => {
      AppToast.success('Interação registrada.');
      setOpen(false);
      form.resetFields();
      await queryClient.invalidateQueries({
        queryKey: ['comunicacao', 'pessoa', pessoaId, 'interacoes'],
      });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  if (interactions.isError) {
    return (
      <Alert
        type="error"
        showIcon
        message="Não foi possível carregar as interações."
        description={normalizeApiError(interactions.error).message}
        action={<Button onClick={() => interactions.refetch()}>Tentar novamente</Button>}
      />
    );
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card
        size="small"
        title="Histórico de interações"
        extra={
          canCreate ? (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                form.setFieldsValue({ direcao: 'saida' });
                setOpen(true);
              }}
            >
              Registrar interação
            </Button>
          ) : null
        }
      >
        <List
          loading={interactions.isPending}
          dataSource={interactions.data ?? []}
          locale={{
            emptyText: (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="Nenhuma interação registrada"
              />
            ),
          }}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                avatar={iconFor(item.canal_comunicacao_nome)}
                title={
                  <Space wrap>
                    <Typography.Text strong>
                      {item.assunto || 'Interação sem assunto'}
                    </Typography.Text>
                    <Tag color={item.direcao === 'entrada' ? 'green' : 'blue'}>
                      {item.direcao === 'entrada' ? 'Entrada' : 'Saída'}
                    </Tag>
                    {item.tipo_interacao_nome ? <Tag>{item.tipo_interacao_nome}</Tag> : null}
                  </Space>
                }
                description={
                  <Space direction="vertical" size={2}>
                    <Typography.Text type="secondary">
                      {dayjs(item.data_interacao).format('DD/MM/YYYY HH:mm')} ·{' '}
                      {item.canal_comunicacao_nome || 'Canal não informado'}
                    </Typography.Text>
                    {item.conteudo ? (
                      <Typography.Paragraph>{item.conteudo}</Typography.Paragraph>
                    ) : null}
                    {item.resultado ? (
                      <Typography.Text type="secondary">
                        Resultado: {item.resultado}
                      </Typography.Text>
                    ) : null}
                  </Space>
                }
              />
            </List.Item>
          )}
        />
      </Card>
      <Timeline
        items={(interactions.data ?? []).slice(0, 5).map((item) => ({
          children: `${dayjs(item.data_interacao).format('DD/MM')} · ${
            item.assunto || item.tipo_interacao_nome || 'Interação registrada'
          }`,
        }))}
      />

      <Modal
        open={open}
        title="Registrar interação"
        okText="Registrar"
        cancelText="Cancelar"
        confirmLoading={createMutation.isPending}
        onCancel={() => setOpen(false)}
        onOk={() => form.validateFields().then((values) => createMutation.mutate(values))}
      >
        <Form form={form} layout="vertical" requiredMark={false}>
          <Form.Item name="direcao" label="Direção" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'saida', label: 'Saída' },
                { value: 'entrada', label: 'Entrada' },
              ]}
            />
          </Form.Item>
          <Form.Item name="tipo_interacao_id" label="Tipo">
            <Select
              allowClear
              loading={types.isPending}
              options={(types.data ?? []).map((item) => ({
                value: item.id,
                label: item.nome,
              }))}
            />
          </Form.Item>
          <Form.Item name="canal_comunicacao_id" label="Canal">
            <Select
              allowClear
              loading={channels.isPending}
              options={(channels.data ?? []).map((item) => ({
                value: item.id,
                label: item.nome,
              }))}
            />
          </Form.Item>
          <Form.Item name="assunto" label="Assunto" rules={[{ max: 180 }]}>
            <Input />
          </Form.Item>
          <Form.Item name="conteudo" label="Resumo da interação" rules={[{ required: true }]}>
            <Input.TextArea rows={4} />
          </Form.Item>
          <Form.Item name="resultado" label="Resultado/encaminhamento" rules={[{ max: 120 }]}>
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

function iconFor(channel: string | null) {
  const normalized = channel?.toLowerCase() ?? '';
  if (normalized.includes('telefone')) return <PhoneOutlined />;
  if (normalized.includes('whatsapp') || normalized.includes('mensagem'))
    return <MessageOutlined />;
  if (normalized.includes('e-mail') || normalized.includes('email')) return <SendOutlined />;
  return <UserSwitchOutlined />;
}
