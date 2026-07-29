import { CloseOutlined, EditOutlined, PlusOutlined, SaveOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Descriptions,
  Form,
  Input,
  InputNumber,
  List,
  Modal,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
} from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { AttachmentsPanel } from '@/components/arquivos/AttachmentsPanel';
import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  addAgendaItem,
  addInvitation,
  addLeadership,
  addParticipant,
  cancelEvent,
  createDemand,
  getEvent,
  recordAttendance,
  updateEvent,
} from '@/modules/agenda/agenda-service';
import { buscarPessoas, listarLiderancas } from '@/modules/cadastro/pessoas-service';
import { listDemandCatalog } from '@/modules/demandas/demandas-service';
import { listarTerritorios } from '@/modules/territorios/territorios-service';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';

type ModalKind = 'edit' | 'participant' | 'leadership' | 'invitation' | 'agenda' | 'demand';

export function EventDetailPage() {
  const { id } = useParams();
  const eventId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const permissions = useSessionStore((state) => state.user?.permissions ?? []);
  const [modal, setModal] = useState<ModalKind | null>(null);
  const [personQuery, setPersonQuery] = useState('');
  const [form] = Form.useForm();
  const event = useQuery({
    queryKey: ['agenda', 'evento', eventId],
    queryFn: () => getEvent(eventId),
    enabled: eventId > 0,
  });
  const people = useQuery({
    queryKey: ['cadastro', 'pessoas', 'event-detail', personQuery],
    queryFn: () => buscarPessoas(personQuery),
    enabled: personQuery.trim().length >= 2,
  });
  const leaderships = useQuery({
    queryKey: ['cadastro', 'liderancas', 'event-detail'],
    queryFn: () => listarLiderancas(),
  });
  const territories = useQuery({
    queryKey: ['territorios', 'event-detail'],
    queryFn: () => listarTerritorios(),
  });
  const demandCategories = useQuery({
    queryKey: ['demandas', 'catalogo', 'categorias'],
    queryFn: () => listDemandCatalog('categorias'),
  });
  const demandPriorities = useQuery({
    queryKey: ['demandas', 'catalogo', 'prioridades'],
    queryFn: () => listDemandCatalog('prioridades'),
  });
  const refresh = async () => queryClient.invalidateQueries({ queryKey: ['agenda'] });
  const closeModal = () => {
    setModal(null);
    form.resetFields();
  };
  const action = useMutation({
    mutationFn: async (values: Record<string, unknown>) => {
      if (modal === 'edit') return updateEvent(eventId, values);
      if (modal === 'participant') {
        return addParticipant(eventId, values as { pessoa_id: number; papel?: string });
      }
      if (modal === 'leadership') {
        return addLeadership(eventId, values as { lideranca_id: number; papel?: string });
      }
      if (modal === 'invitation') {
        return addInvitation(
          eventId,
          values as {
            direcao: 'recebido' | 'emitido';
            origem?: string;
            pessoa_indicou_id?: number;
            status: 'pendente' | 'aceito' | 'recusado' | 'confirmado';
            descricao?: string;
          },
        );
      }
      if (modal === 'agenda') {
        return addAgendaItem(
          eventId,
          values as { titulo: string; descricao?: string; encaminhamento?: string },
        );
      }
      return createDemand(
        eventId,
        values as {
          titulo: string;
          descricao: string;
          pessoa_solicitante_id?: number;
          territorio_id?: number;
          categoria_demanda_id?: number;
          prioridade_demanda_id?: number;
        },
      );
    },
    onSuccess: async () => {
      AppToast.success('Registro salvo.');
      closeModal();
      await refresh();
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const cancellation = useMutation({
    mutationFn: (reason: string) => cancelEvent(eventId, reason),
    onSuccess: async () => {
      AppToast.success('Evento cancelado.');
      await refresh();
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const attendance = useMutation({
    mutationFn: (values: Record<string, unknown>) =>
      recordAttendance(eventId, {
        presenca_parlamentar: Boolean(values.presenca_parlamentar),
        presenca_representante: Boolean(values.presenca_representante),
        nome_representante: (values.nome_representante as string) || null,
        numero_lideres_presentes: (values.numero_lideres_presentes as number) ?? null,
        numero_convidados: (values.numero_convidados as number) ?? null,
        numero_estimado_presentes: (values.numero_estimado_presentes as number) ?? null,
        observacao: (values.observacao as string) || null,
      }),
    onSuccess: async () => {
      AppToast.success('Presença registrada.');
      await refresh();
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  if (event.error) {
    return <Alert type="error" showIcon message={normalizeApiError(event.error).message} />;
  }
  const item = event.data;
  const personOptions = (people.data ?? []).map((person) => ({
    value: person.id,
    label: person.nome_completo,
  }));
  const openEdit = () => {
    form.setFieldsValue({
      titulo: item?.titulo,
      descricao: item?.descricao,
      local_nome: item?.local_nome,
      territorio_id: item?.territorio_id,
    });
    setModal('edit');
  };
  return (
    <div>
      <PageHeader
        title={item?.titulo || `Evento #${eventId}`}
        description={
          item
            ? `${dayjs(item.data_inicio).format('DD/MM/YYYY HH:mm')} · ${item.local_nome || 'Local a definir'}`
            : 'Carregando evento'
        }
        breadcrumbs={[
          { label: 'Início', to: '/dashboard' },
          { label: 'Agenda', to: '/agenda' },
          { label: `#${eventId}` },
        ]}
        actions={
          <Space>
            {permissions.includes('agenda.editar') && (
              <Button icon={<EditOutlined />} onClick={openEdit}>
                Editar
              </Button>
            )}
            {permissions.includes('agenda.editar') &&
              item?.status_evento_codigo !== 'cancelado' && (
                <Button
                  danger
                  icon={<CloseOutlined />}
                  onClick={() =>
                    Modal.confirm({
                      title: 'Cancelar evento',
                      content: (
                        <Input.TextArea id="cancel-event-reason" placeholder="Informe o motivo" />
                      ),
                      onOk: () => {
                        const input =
                          document.querySelector<HTMLTextAreaElement>('#cancel-event-reason');
                        if (!input?.value.trim()) {
                          AppToast.error('Informe o motivo.');
                          return Promise.reject();
                        }
                        cancellation.mutate(input.value);
                      },
                    })
                  }
                >
                  Cancelar
                </Button>
              )}
          </Space>
        }
      />
      {item?.status_evento_codigo === 'cancelado' && (
        <Alert
          type="error"
          showIcon
          message={`Evento cancelado: ${item.motivo_cancelamento}`}
          style={{ marginBottom: 16 }}
        />
      )}
      <Tabs
        items={[
          {
            key: 'data',
            label: 'Dados',
            children: (
              <Card>
                <Descriptions column={{ xs: 1, md: 2 }}>
                  <Descriptions.Item label="Tipo">{item?.tipo_evento_nome}</Descriptions.Item>
                  <Descriptions.Item label="Status">
                    <Tag>{item?.status_evento_nome}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="Responsável">
                    {item?.responsavel_nome}
                  </Descriptions.Item>
                  <Descriptions.Item label="Território">
                    {item?.territorio_nome || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Início">
                    {item && dayjs(item.data_inicio).format('DD/MM/YYYY HH:mm')}
                  </Descriptions.Item>
                  <Descriptions.Item label="Fim">
                    {item?.data_fim ? dayjs(item.data_fim).format('DD/MM/YYYY HH:mm') : '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Descrição" span={2}>
                    {item?.descricao || '—'}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            ),
          },
          {
            key: 'participants',
            label: `Participantes (${item?.participantes.length ?? 0})`,
            children: (
              <Card
                extra={
                  <Button icon={<PlusOutlined />} onClick={() => setModal('participant')}>
                    Adicionar
                  </Button>
                }
              >
                <Table
                  rowKey="id"
                  dataSource={item?.participantes ?? []}
                  columns={[
                    { title: 'Pessoa', dataIndex: 'nome' },
                    { title: 'Papel', dataIndex: 'papel' },
                    {
                      title: 'Presente',
                      dataIndex: 'presente',
                      render: (value) => (value == null ? 'Não informado' : value ? 'Sim' : 'Não'),
                    },
                    { title: 'Observação', dataIndex: 'observacao' },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: 'leaderships',
            label: `Lideranças (${item?.liderancas.length ?? 0})`,
            children: (
              <Card
                extra={
                  <Button icon={<PlusOutlined />} onClick={() => setModal('leadership')}>
                    Adicionar
                  </Button>
                }
              >
                <Table
                  rowKey="lideranca_id"
                  dataSource={item?.liderancas ?? []}
                  columns={[
                    { title: 'Liderança', dataIndex: 'nome' },
                    { title: 'Tipo', dataIndex: 'tipo_lideranca' },
                    { title: 'Papel no evento', dataIndex: 'papel' },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: 'invitations',
            label: `Convites (${item?.convites.length ?? 0})`,
            children: (
              <Card
                extra={
                  <Button icon={<PlusOutlined />} onClick={() => setModal('invitation')}>
                    Registrar
                  </Button>
                }
              >
                <Table
                  rowKey="id"
                  dataSource={item?.convites ?? []}
                  columns={[
                    { title: 'Direção', dataIndex: 'direcao' },
                    { title: 'Origem', dataIndex: 'origem' },
                    { title: 'Indicação', dataIndex: 'pessoa_indicou_nome' },
                    { title: 'Status', dataIndex: 'status' },
                    { title: 'Descrição', dataIndex: 'descricao' },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: 'agenda',
            label: `Pautas (${item?.pautas.length ?? 0})`,
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} lg={16}>
                  <Card
                    extra={
                      <Button icon={<PlusOutlined />} onClick={() => setModal('agenda')}>
                        Nova pauta
                      </Button>
                    }
                  >
                    <List
                      dataSource={item?.pautas ?? []}
                      renderItem={(agendaItem) => (
                        <List.Item>
                          <List.Item.Meta
                            title={agendaItem.titulo}
                            description={
                              <>
                                <div>{agendaItem.descricao}</div>
                                <strong>Encaminhamento: </strong>
                                {agendaItem.encaminhamento || '—'}
                              </>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  </Card>
                </Col>
                <Col xs={24} lg={8}>
                  <Card title="Temas sugeridos">
                    <List
                      dataSource={item?.insights ?? []}
                      renderItem={(insight) => (
                        <List.Item>
                          <Tag>{insight.tipo}</Tag>
                          {insight.tema} ({insight.frequencia})
                        </List.Item>
                      )}
                    />
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'attachments',
            label: 'Anexos',
            children: (
              <AttachmentsPanel
                entity="evento"
                entityId={eventId}
                allowedTypeCodes={['convite', 'pauta', 'imagem', 'pdf']}
                canEdit={permissions.includes('agenda.editar')}
              />
            ),
          },
          {
            key: 'attendance',
            label: 'Presença',
            children: (
              <Card>
                <Form
                  key={item?.presenca?.id ?? 'presenca-vazia'}
                  layout="vertical"
                  initialValues={item?.presenca ?? {}}
                  onFinish={(values) => attendance.mutate(values)}
                >
                  <Space>
                    <Form.Item name="presenca_parlamentar" valuePropName="checked">
                      <Checkbox>Parlamentar presente</Checkbox>
                    </Form.Item>
                    <Form.Item name="presenca_representante" valuePropName="checked">
                      <Checkbox>Representante presente</Checkbox>
                    </Form.Item>
                  </Space>
                  <Row gutter={12}>
                    <Col xs={24} md={8}>
                      <Form.Item name="nome_representante" label="Representante">
                        <Input />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={5}>
                      <Form.Item name="numero_lideres_presentes" label="Lideranças">
                        <InputNumber min={0} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={5}>
                      <Form.Item name="numero_convidados" label="Convidados">
                        <InputNumber min={0} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={6}>
                      <Form.Item name="numero_estimado_presentes" label="Total estimado">
                        <InputNumber min={0} style={{ width: '100%' }} />
                      </Form.Item>
                    </Col>
                  </Row>
                  <Form.Item name="observacao" label="Observação">
                    <Input.TextArea />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" icon={<SaveOutlined />}>
                    Salvar presença
                  </Button>
                </Form>
              </Card>
            ),
          },
          {
            key: 'demands',
            label: `Demandas (${item?.demandas.length ?? 0})`,
            children: (
              <Card
                extra={
                  permissions.includes('demandas.criar') && (
                    <Button icon={<PlusOutlined />} onClick={() => setModal('demand')}>
                      Criar demanda
                    </Button>
                  )
                }
              >
                <Table
                  rowKey="id"
                  dataSource={item?.demandas ?? []}
                  columns={[
                    { title: 'Título', dataIndex: 'titulo' },
                    { title: 'Descrição', dataIndex: 'descricao' },
                    { title: 'Status', dataIndex: 'status' },
                    { title: 'Prioridade', dataIndex: 'prioridade' },
                  ]}
                />
              </Card>
            ),
          },
        ]}
      />
      <Modal
        open={modal !== null}
        title={modalTitle(modal)}
        okText="Salvar"
        confirmLoading={action.isPending}
        onCancel={closeModal}
        onOk={() => form.validateFields().then((values) => action.mutate(values))}
      >
        <Form form={form} layout="vertical">
          {modal === 'edit' && (
            <>
              <Form.Item name="titulo" label="Título" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="descricao" label="Descrição">
                <Input.TextArea />
              </Form.Item>
              <Form.Item name="local_nome" label="Local">
                <Input />
              </Form.Item>
              <Form.Item name="territorio_id" label="Território">
                <Select
                  allowClear
                  options={(territories.data ?? []).map((territory) => ({
                    value: territory.id,
                    label: territory.nome,
                  }))}
                />
              </Form.Item>
            </>
          )}
          {modal === 'participant' && (
            <>
              <PersonSelect onSearch={setPersonQuery} options={personOptions} name="pessoa_id" />
              <Form.Item name="papel" label="Papel">
                <Input />
              </Form.Item>
              <Form.Item name="observacao" label="Observação">
                <Input.TextArea />
              </Form.Item>
            </>
          )}
          {modal === 'leadership' && (
            <>
              <Form.Item name="lideranca_id" label="Liderança" rules={[{ required: true }]}>
                <Select
                  options={(leaderships.data ?? []).map((leader) => ({
                    value: leader.id,
                    label: leader.apelido_campanha || `Liderança #${leader.id}`,
                  }))}
                />
              </Form.Item>
              <Form.Item name="papel" label="Papel no evento">
                <Input />
              </Form.Item>
            </>
          )}
          {modal === 'invitation' && (
            <>
              <Form.Item name="direcao" label="Direção" initialValue="recebido">
                <Select options={[{ value: 'recebido' }, { value: 'emitido' }]} />
              </Form.Item>
              <Form.Item name="origem" label="Origem">
                <Input />
              </Form.Item>
              <PersonSelect
                onSearch={setPersonQuery}
                options={personOptions}
                name="pessoa_indicou_id"
                required={false}
                label="Quem indicou"
              />
              <Form.Item name="categoria_demanda_id" label="Categoria" rules={[{ required: true }]}>
                <Select
                  options={(demandCategories.data ?? []).map((category) => ({
                    value: category.id,
                    label: category.nome,
                  }))}
                />
              </Form.Item>
              <Form.Item name="prioridade_demanda_id" label="Prioridade">
                <Select
                  allowClear
                  options={(demandPriorities.data ?? []).map((priority) => ({
                    value: priority.id,
                    label: priority.nome,
                  }))}
                />
              </Form.Item>
              <Form.Item name="status" label="Status" initialValue="pendente">
                <Select
                  options={['pendente', 'aceito', 'recusado', 'confirmado'].map((value) => ({
                    value,
                  }))}
                />
              </Form.Item>
              <Form.Item name="descricao" label="Descrição">
                <Input.TextArea />
              </Form.Item>
            </>
          )}
          {modal === 'agenda' && (
            <>
              <Form.Item name="titulo" label="Tema" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="descricao" label="Descrição">
                <Input.TextArea />
              </Form.Item>
              <Form.Item name="encaminhamento" label="Encaminhamento">
                <Input.TextArea />
              </Form.Item>
            </>
          )}
          {modal === 'demand' && (
            <>
              <Form.Item name="titulo" label="Título" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="descricao" label="Descrição" rules={[{ required: true }]}>
                <Input.TextArea />
              </Form.Item>
              <PersonSelect
                onSearch={setPersonQuery}
                options={personOptions}
                name="pessoa_solicitante_id"
                required={false}
                label="Solicitante"
              />
              <Form.Item name="territorio_id" label="Território">
                <Select
                  allowClear
                  options={(territories.data ?? []).map((territory) => ({
                    value: territory.id,
                    label: territory.nome,
                  }))}
                />
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>
      <Button type="link" onClick={() => navigate('/agenda')}>
        Voltar à agenda
      </Button>
    </div>
  );
}

function modalTitle(kind: ModalKind | null) {
  const titles: Record<ModalKind, string> = {
    edit: 'Editar evento',
    participant: 'Adicionar participante',
    leadership: 'Adicionar liderança',
    invitation: 'Registrar convite',
    agenda: 'Registrar pauta',
    demand: 'Criar demanda a partir do evento',
  };
  return kind ? titles[kind] : '';
}

function PersonSelect({
  onSearch,
  options,
  name,
  required = true,
  label = 'Pessoa',
}: {
  onSearch: (value: string) => void;
  options: Array<{ value: number; label: string }>;
  name: string;
  required?: boolean;
  label?: string;
}) {
  return (
    <Form.Item name={name} label={label} rules={required ? [{ required: true }] : []}>
      <Select
        showSearch
        allowClear={!required}
        filterOption={false}
        onSearch={onSearch}
        options={options}
        notFoundContent="Digite ao menos dois caracteres"
      />
    </Form.Item>
  );
}
