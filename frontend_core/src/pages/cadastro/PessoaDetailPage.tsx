import { ArrowLeftOutlined, EditOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Form,
  Input,
  List,
  Modal,
  Space,
  Spin,
  Switch,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  atualizarContato,
  atualizarDocumento,
  atualizarEndereco,
  atualizarPessoa,
  obterPessoa,
} from '@/modules/cadastro/pessoas-service';
import type { PessoaContato, PessoaDocumento, PessoaEndereco } from '@/modules/cadastro/types';
import { normalizeApiError } from '@/services/api/api-error';

type Editor =
  | { type: 'person' }
  | { type: 'document'; item: PessoaDocumento }
  | { type: 'contact'; item: PessoaContato }
  | { type: 'address'; item: PessoaEndereco };

type EditValues = Record<string, string | number | boolean | null | undefined>;

export function PessoaDetailPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const params = useParams();
  const personId = Number(params.id);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [form] = Form.useForm<EditValues>();
  const personQuery = useQuery({
    queryKey: ['cadastro', 'pessoa', personId],
    queryFn: () => obterPessoa(personId),
    enabled: Number.isInteger(personId),
  });
  const saveMutation = useMutation({
    mutationFn: async (values: EditValues) => {
      if (!editor) return;
      if (editor.type === 'person') await atualizarPessoa(personId, values);
      if (editor.type === 'document') await atualizarDocumento(personId, editor.item.id, values);
      if (editor.type === 'contact') await atualizarContato(personId, editor.item.id, values);
      if (editor.type === 'address')
        await atualizarEndereco(personId, editor.item.id, {
          principal: values.principal,
          endereco: {
            cep: values.cep,
            logradouro: values.logradouro,
            numero: values.numero,
            complemento: values.complemento,
            bairro_texto: values.bairro_texto,
          },
        });
    },
    onSuccess: async () => {
      AppToast.success('Dados atualizados.');
      setEditor(null);
      await queryClient.invalidateQueries({ queryKey: ['cadastro', 'pessoa', personId] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const openEditor = (next: Editor) => {
    const person = personQuery.data;
    setEditor(next);
    if (!person) return;
    if (next.type === 'person') {
      form.setFieldsValue({
        nome_completo: person.nome_completo,
        nome_social: person.nome_social,
        apelido: person.apelido,
        estado_civil: person.estado_civil,
        observacoes: person.observacoes,
      });
    } else if (next.type === 'address') {
      form.setFieldsValue({
        cep: next.item.endereco.cep,
        logradouro: next.item.endereco.logradouro,
        numero: next.item.endereco.numero,
        complemento: next.item.endereco.complemento,
        bairro_texto: next.item.endereco.bairro_texto,
        principal: next.item.principal,
      });
    } else if (next.type === 'document') {
      form.setFieldsValue({
        numero: next.item.numero,
        orgao_emissor: next.item.orgao_emissor,
        uf_emissor: next.item.uf_emissor,
      });
    } else {
      form.setFieldsValue({
        valor: next.item.valor,
        principal: next.item.principal,
        observacao: next.item.observacao,
      });
    }
  };

  if (personQuery.isPending) return <Spin size="large" />;
  if (personQuery.error || !personQuery.data) {
    return (
      <Alert
        type="error"
        showIcon
        message="Não foi possível carregar o cadastro"
        description={normalizeApiError(personQuery.error).message}
      />
    );
  }
  const person = personQuery.data;
  const noItems = (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Nenhum vínculo registrado" />
  );

  return (
    <div>
      <PageHeader
        title={person.nome_social || person.nome_completo}
        description={`Cadastro #${person.id} · ${person.ativo ? 'Ativo' : 'Inativo'}`}
        breadcrumbs={[{ label: 'Pessoas', to: '/cadastro' }, { label: person.nome_completo }]}
        actions={
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/cadastro')}>
              Voltar
            </Button>
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={() => openEditor({ type: 'person' })}
            >
              Editar dados
            </Button>
          </Space>
        }
      />
      <Card>
        <Tabs
          items={[
            {
              key: 'dados',
              label: 'Dados',
              children: (
                <Descriptions column={{ xs: 1, md: 2 }} bordered size="small">
                  <Descriptions.Item label="Nome completo">
                    {person.nome_completo}
                  </Descriptions.Item>
                  <Descriptions.Item label="Nome social">
                    {person.nome_social || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Apelido">{person.apelido || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Nascimento">
                    {person.data_nascimento || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Estado civil">
                    {person.estado_civil || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Tipos">
                    {person.tipos.map((item) => (
                      <Tag key={item.id}>{item.nome}</Tag>
                    ))}
                  </Descriptions.Item>
                  <Descriptions.Item label="Observações" span={2}>
                    {person.observacoes || '—'}
                  </Descriptions.Item>
                </Descriptions>
              ),
            },
            {
              key: 'contatos',
              label: `Contatos (${person.contatos.length})`,
              children: (
                <List
                  dataSource={person.contatos}
                  locale={{ emptyText: noItems }}
                  renderItem={(item) => (
                    <List.Item
                      actions={[
                        <Button
                          key="edit"
                          type="link"
                          onClick={() => openEditor({ type: 'contact', item })}
                        >
                          Editar
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        title={
                          <Space>
                            {item.valor}
                            {item.principal ? <Tag color="blue">Principal</Tag> : null}
                          </Space>
                        }
                        description={item.tipo_contato}
                      />
                    </List.Item>
                  )}
                />
              ),
            },
            {
              key: 'documentos',
              label: `Documentos (${person.documentos.length})`,
              children: (
                <List
                  dataSource={person.documentos}
                  locale={{ emptyText: noItems }}
                  renderItem={(item) => (
                    <List.Item
                      actions={[
                        <Button
                          key="edit"
                          type="link"
                          onClick={() => openEditor({ type: 'document', item })}
                        >
                          Editar
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        title={item.numero}
                        description={item.tipo_documento.toUpperCase()}
                      />
                    </List.Item>
                  )}
                />
              ),
            },
            {
              key: 'enderecos',
              label: `Endereços (${person.enderecos.length})`,
              children: (
                <List
                  dataSource={person.enderecos}
                  locale={{ emptyText: noItems }}
                  renderItem={(item) => (
                    <List.Item
                      actions={[
                        <Button
                          key="edit"
                          type="link"
                          onClick={() => openEditor({ type: 'address', item })}
                        >
                          Editar
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        title={`${item.endereco.logradouro || 'Endereço'} ${item.endereco.numero || ''}`}
                        description={`${item.tipo} · ${item.endereco.bairro_texto || 'Bairro não informado'}`}
                      />
                    </List.Item>
                  )}
                />
              ),
            },
            {
              key: 'eleitor',
              label: 'Eleitor',
              children: person.eleitor ? (
                <Descriptions bordered size="small">
                  <Descriptions.Item label="Título">
                    {person.eleitor.titulo_eleitor || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Zona">
                    {person.eleitor.zona_eleitoral_id || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Seção">
                    {person.eleitor.secao_eleitoral_id || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Situação">
                    {person.eleitor.situacao_titulo || '—'}
                  </Descriptions.Item>
                </Descriptions>
              ) : (
                noItems
              ),
            },
            {
              key: 'vinculos',
              label: 'Vínculos',
              children: (
                <Space direction="vertical" size="large" style={{ width: '100%' }}>
                  <section>
                    <Typography.Title level={5}>Liderança</Typography.Title>
                    {person.hierarquia.length
                      ? person.hierarquia.map((item) => (
                          <Tag key={item.id} color="blue">
                            {item.papel_subordinado} de #{item.lideranca_superior_id}
                          </Tag>
                        ))
                      : noItems}
                  </section>
                  <section>
                    <Typography.Title level={5}>Indicações</Typography.Title>
                    {person.indicacoes.length
                      ? person.indicacoes.map((item) => (
                          <Tag key={item.id}>Origem: {item.origem || 'não informada'}</Tag>
                        ))
                      : noItems}
                  </section>
                </Space>
              ),
            },
            {
              key: 'segmentacao',
              label: 'Tags e comunidades',
              children: (
                <Descriptions bordered size="small" column={1}>
                  <Descriptions.Item label="Tags">
                    {person.tags.map((item) => (
                      <Tag key={item.id}>{item.nome}</Tag>
                    ))}
                  </Descriptions.Item>
                  <Descriptions.Item label="Comunidades">
                    {person.comunidades.map((item) => (
                      <Tag key={item.id}>{item.nome}</Tag>
                    ))}
                  </Descriptions.Item>
                  <Descriptions.Item label="Núcleos familiares">
                    {person.nucleos_familiares.map((item) => (
                      <Tag key={item.id}>{item.nome}</Tag>
                    ))}
                  </Descriptions.Item>
                </Descriptions>
              ),
            },
            {
              key: 'historico',
              label: 'Histórico',
              children: (
                <Descriptions column={1} bordered size="small">
                  <Descriptions.Item label="Criado em">{person.criado_em}</Descriptions.Item>
                  <Descriptions.Item label="Atualizado em">
                    {person.atualizado_em}
                  </Descriptions.Item>
                  <Descriptions.Item label="Completude">
                    {person.completude_cadastral
                      ? `${person.completude_cadastral}%`
                      : 'Não calculada'}
                  </Descriptions.Item>
                </Descriptions>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        open={Boolean(editor)}
        title="Editar cadastro"
        okText="Salvar"
        cancelText="Cancelar"
        confirmLoading={saveMutation.isPending}
        onCancel={() => setEditor(null)}
        onOk={() => form.validateFields().then((values) => saveMutation.mutate(values))}
      >
        <Form form={form} layout="vertical" requiredMark={false}>
          {editor?.type === 'person' ? (
            <>
              <Form.Item name="nome_completo" label="Nome completo" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="nome_social" label="Nome social">
                <Input />
              </Form.Item>
              <Form.Item name="apelido" label="Apelido">
                <Input />
              </Form.Item>
              <Form.Item name="estado_civil" label="Estado civil">
                <Input />
              </Form.Item>
              <Form.Item name="observacoes" label="Observações">
                <Input.TextArea rows={3} />
              </Form.Item>
            </>
          ) : null}
          {editor?.type === 'document' ? (
            <>
              <Form.Item name="numero" label="Número" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="orgao_emissor" label="Órgão emissor">
                <Input />
              </Form.Item>
              <Form.Item name="uf_emissor" label="UF">
                <Input maxLength={2} />
              </Form.Item>
            </>
          ) : null}
          {editor?.type === 'contact' ? (
            <>
              <Form.Item name="valor" label="Contato" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="principal" label="Principal" valuePropName="checked">
                <Switch />
              </Form.Item>
              <Form.Item name="observacao" label="Observação">
                <Input />
              </Form.Item>
            </>
          ) : null}
          {editor?.type === 'address' ? (
            <>
              <Form.Item name="cep" label="CEP">
                <Input />
              </Form.Item>
              <Form.Item name="logradouro" label="Logradouro">
                <Input />
              </Form.Item>
              <Form.Item name="numero" label="Número">
                <Input />
              </Form.Item>
              <Form.Item name="complemento" label="Complemento">
                <Input />
              </Form.Item>
              <Form.Item name="bairro_texto" label="Bairro">
                <Input />
              </Form.Item>
              <Form.Item name="principal" label="Principal" valuePropName="checked">
                <Switch />
              </Form.Item>
            </>
          ) : null}
        </Form>
      </Modal>
    </div>
  );
}
