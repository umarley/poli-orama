import { EditOutlined, LinkOutlined, PlusOutlined, StopOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
} from 'antd';
import { useState } from 'react';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  atualizarTag,
  criarComunidade,
  criarNucleo,
  criarTag,
  listarComunidades,
  listarNucleos,
  listarTags,
  vincularComunidade,
  vincularNucleo,
  vincularTag,
} from '@/modules/cadastro/pessoas-service';
import type { Comunidade, NucleoFamiliar, TagCadastro } from '@/modules/cadastro/types';
import { normalizeApiError } from '@/services/api/api-error';

type Entity = 'tag' | 'community' | 'nucleus';
type Dialog =
  | { mode: 'create'; entity: Entity }
  | { mode: 'edit'; entity: 'tag'; item: TagCadastro }
  | { mode: 'link'; entity: Entity; id: number }
  | null;

type DialogValues = Record<string, string | number | boolean | null | undefined>;

export function SegmentacaoPage() {
  const queryClient = useQueryClient();
  const [dialog, setDialog] = useState<Dialog>(null);
  const [form] = Form.useForm<DialogValues>();
  const tagsQuery = useQuery({ queryKey: ['cadastro', 'tags'], queryFn: listarTags });
  const communitiesQuery = useQuery({
    queryKey: ['cadastro', 'comunidades'],
    queryFn: listarComunidades,
  });
  const nucleiQuery = useQuery({ queryKey: ['cadastro', 'nucleos'], queryFn: listarNucleos });

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
      if (dialog.entity === 'community' && dialog.mode === 'create') {
        await criarComunidade({
          nome: String(values.nome),
          tipo: (values.tipo as string) || null,
          descricao: (values.descricao as string) || null,
          lider_responsavel_id: null,
          municipio_id: null,
          territorio_id: values.territorio_id ? Number(values.territorio_id) : null,
        });
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
        cor: next.item.cor,
        categoria: next.item.categoria,
        descricao: next.item.descricao,
      });
    }
  };

  const actionButtons = (entity: Entity, id: number) => (
    <Button type="link" icon={<LinkOutlined />} onClick={() => open({ mode: 'link', entity, id })}>
      Vincular pessoa
    </Button>
  );

  return (
    <div>
      <PageHeader
        title="Segmentação"
        description="Tags, comunidades e núcleos familiares da base de pessoas."
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
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => open({ mode: 'create', entity: 'tag' })}
                    style={{ marginBottom: 16 }}
                  >
                    Nova tag
                  </Button>
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
                        render: (_, item) => (
                          <Space>
                            {actionButtons('tag', item.id)}
                            <Button
                              type="link"
                              icon={<EditOutlined />}
                              onClick={() => open({ mode: 'edit', entity: 'tag', item })}
                            >
                              Editar
                            </Button>
                            {item.ativo ? (
                              <Button
                                type="link"
                                danger
                                icon={<StopOutlined />}
                                onClick={() =>
                                  atualizarTag(item.id, { ativo: false }).then(() =>
                                    queryClient.invalidateQueries({
                                      queryKey: ['cadastro', 'tags'],
                                    }),
                                  )
                                }
                              >
                                Inativar
                              </Button>
                            ) : null}
                          </Space>
                        ),
                      },
                    ]}
                  />
                </>
              ),
            },
            {
              key: 'communities',
              label: `Comunidades (${communitiesQuery.data?.length ?? 0})`,
              children: (
                <>
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => open({ mode: 'create', entity: 'community' })}
                    style={{ marginBottom: 16 }}
                  >
                    Nova comunidade
                  </Button>
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
                        render: (value) => (value ? `#${value}` : '—'),
                      },
                      { title: 'Ações', render: (_, item) => actionButtons('community', item.id) },
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
                  <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => open({ mode: 'create', entity: 'nucleus' })}
                    style={{ marginBottom: 16 }}
                  >
                    Novo núcleo
                  </Button>
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
                        render: (value) => value ?? 0,
                      },
                      {
                        title: 'Pessoa de referência',
                        dataIndex: 'pessoa_referencia_id',
                        render: (value) => (value ? `Pessoa #${value}` : '—'),
                      },
                      { title: 'Ações', render: (_, item) => actionButtons('nucleus', item.id) },
                    ]}
                  />
                </>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        open={Boolean(dialog)}
        title={dialog?.mode === 'link' ? 'Vincular pessoa' : 'Cadastrar item'}
        okText="Salvar"
        confirmLoading={mutation.isPending}
        onCancel={() => setDialog(null)}
        onOk={() => form.validateFields().then((values) => mutation.mutate(values))}
      >
        <Form form={form} layout="vertical">
          {dialog?.mode === 'link' ? (
            <>
              <Form.Item name="pessoa_id" label="ID da pessoa" rules={[{ required: true }]}>
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
              {dialog.entity === 'community' ? (
                <Form.Item name="papel" label="Papel na comunidade">
                  <Input />
                </Form.Item>
              ) : null}
              {dialog.entity === 'nucleus' ? (
                <>
                  <Form.Item name="parentesco" label="Parentesco">
                    <Input />
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
                  <Form.Item name="cor" label="Cor hexadecimal">
                    <Input placeholder="#1677ff" />
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
                  <Form.Item name="territorio_id" label="ID do território">
                    <InputNumber min={1} style={{ width: '100%' }} />
                  </Form.Item>
                </>
              ) : null}
              {dialog?.entity === 'nucleus' ? (
                <Form.Item name="pessoa_referencia_id" label="ID da pessoa de referência">
                  <InputNumber min={1} style={{ width: '100%' }} />
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
