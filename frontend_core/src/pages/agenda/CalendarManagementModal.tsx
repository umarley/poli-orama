import {
  DeleteOutlined,
  EditOutlined,
  GoogleOutlined,
  PlusOutlined,
  SyncOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Checkbox,
  Form,
  Input,
  List,
  Modal,
  Popconfirm,
  Select,
  Space,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { useEffect, useMemo, useState } from 'react';

import { AppToast } from '@/components/feedback/AppToast';
import { env } from '@/config/env';
import {
  createCalendar,
  deleteCalendar,
  linkGoogleCalendar,
  listCalendarMembers,
  listCalendars,
  listGoogleCalendars,
  removeCalendarMember,
  saveCalendarMember,
  startGoogleOAuth,
  syncGoogleCalendar,
  unlinkGoogleCalendar,
  updateCalendar,
} from '@/modules/agenda/agenda-service';
import type {
  CalendarMember,
  CampaignCalendar,
  CampaignCalendarInput,
  GoogleCalendarLink,
} from '@/modules/agenda/types';
import { listUsers } from '@/modules/users/user-service';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';

const fronts = [
  ['juventude', 'Juventude'],
  ['sindicalista', 'Sindicalista'],
  ['cultura', 'Cultura'],
  ['engenharia', 'Engenharia'],
  ['saude', 'Saúde'],
  ['educacao', 'Educação'],
  ['dobradas', 'Dobradas'],
] as const;

const permissionOptions: Array<[keyof CalendarMember, string]> = [
  ['pode_visualizar', 'Visualizar'],
  ['pode_criar', 'Criar'],
  ['pode_editar', 'Editar'],
  ['pode_alterar_classificacao', 'Alterar classificação'],
  ['pode_excluir', 'Excluir'],
  ['pode_administrar_usuarios', 'Administrar usuários'],
  ['pode_administrar_agenda', 'Administrar agenda'],
];

interface Props {
  open: boolean;
  onClose: () => void;
}

type MemberForm = Omit<CalendarMember, 'nome' | 'email'>;
type GoogleForm = {
  google_calendar_id: string;
  direcao: GoogleCalendarLink['direcao'];
};

export function CalendarManagementModal({ open, onClose }: Props) {
  const queryClient = useQueryClient();
  const globalPermissions = useSessionStore((state) => state.user?.permissions ?? []);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [editing, setEditing] = useState<CampaignCalendar | 'new' | null>(null);
  const [googleReady, setGoogleReady] = useState(false);
  const [calendarForm] = Form.useForm<CampaignCalendarInput>();
  const [memberForm] = Form.useForm<MemberForm>();
  const [googleForm] = Form.useForm<GoogleForm>();
  const calendars = useQuery({
    queryKey: ['agenda', 'agendas'],
    queryFn: listCalendars,
    enabled: open,
  });
  const selected =
    calendars.data?.find((calendar) => calendar.id === selectedId) ?? calendars.data?.[0] ?? null;
  const members = useQuery({
    queryKey: ['agenda', 'agenda-usuarios', selected?.id],
    queryFn: () => listCalendarMembers(selected!.id),
    enabled: Boolean(open && selected && selected.permissoes.includes('administrar_usuarios')),
  });
  const users = useQuery({
    queryKey: ['users', 'agenda-members'],
    queryFn: () => listUsers({ status: 'ativo' }),
    enabled: Boolean(open && selected?.permissoes.includes('administrar_usuarios')),
  });
  const googleCalendars = useQuery({
    queryKey: ['agenda', 'google-calendarios', googleReady],
    queryFn: listGoogleCalendars,
    enabled: open && googleReady,
    retry: false,
  });

  useEffect(() => {
    const listener = (event: MessageEvent) => {
      if (event.origin !== new URL(env.apiUrl, window.location.origin).origin) return;
      if (event.data?.type !== 'google-calendar-oauth') return;
      if (event.data.success) {
        setGoogleReady(true);
        AppToast.success(event.data.message);
      } else {
        AppToast.error(event.data.message || 'Não foi possível conectar a conta Google.');
      }
    };
    window.addEventListener('message', listener);
    return () => window.removeEventListener('message', listener);
  }, []);

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['agenda'] });
  };
  const saveCalendar = useMutation({
    mutationFn: (values: CampaignCalendarInput) =>
      editing === 'new' ? createCalendar(values) : updateCalendar(editing!.id, values),
    onSuccess: async (item) => {
      setEditing(null);
      setSelectedId(item.id);
      AppToast.success('Agenda salva.');
      await refresh();
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const saveMember = useMutation({
    mutationFn: (values: MemberForm) => saveCalendarMember(selected!.id, values),
    onSuccess: async () => {
      memberForm.resetFields();
      AppToast.success('Permissões atualizadas.');
      await queryClient.invalidateQueries({
        queryKey: ['agenda', 'agenda-usuarios', selected?.id],
      });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const googleLink = useMutation({
    mutationFn: (values: GoogleForm) => {
      const item = googleCalendars.data?.find((option) => option.id === values.google_calendar_id);
      if (!item) throw new Error('Selecione uma agenda Google.');
      return linkGoogleCalendar(selected!.id, {
        ...values,
        google_calendar_nome: item.nome,
      });
    },
    onSuccess: async () => {
      AppToast.success('Agenda Google vinculada.');
      await refresh();
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const sync = useMutation({
    mutationFn: () => syncGoogleCalendar(selected!.id),
    onSuccess: async (summary) => {
      AppToast.success(
        `Sincronização concluída: ${summary.enviados} enviados, ${summary.importados} importados e ${summary.atualizados} atualizados.`,
      );
      if (summary.erros.length) AppToast.error(summary.erros[0]);
      await refresh();
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const canCreate = globalPermissions.includes('agenda.administrar');
  const canManage = selected?.permissoes.includes('administrar_agenda') ?? false;
  const userOptions = useMemo(
    () =>
      (users.data?.items ?? []).map((user) => ({
        value: user.id,
        label: `${user.nome} (${user.email})`,
      })),
    [users.data],
  );

  const editCalendar = (calendar: CampaignCalendar | 'new') => {
    setEditing(calendar);
    if (calendar === 'new') {
      calendarForm.setFieldsValue({
        natureza_candidato: 'rede',
        frente_comunidade: 'juventude',
        tipo_agenda: 'agenda_candidato',
        visibilidade: 'publica',
        cor: '#1677ff',
      });
    } else {
      calendarForm.setFieldsValue({
        nome: calendar.nome,
        descricao: calendar.descricao ?? undefined,
        natureza_candidato: calendar.natureza_candidato,
        frente_comunidade: calendar.frente_comunidade,
        tipo_agenda: calendar.tipo_agenda,
        visibilidade: calendar.visibilidade,
        cor: calendar.cor,
      });
    }
  };

  const connectGoogle = async () => {
    try {
      const { authorization_url } = await startGoogleOAuth();
      window.open(authorization_url, 'google-calendar-oauth', 'width=560,height=720');
    } catch (error) {
      AppToast.error(normalizeApiError(error).message);
    }
  };

  return (
    <Modal open={open} title="Gerenciar agendas" width={1050} footer={null} onCancel={onClose}>
      <Space align="start" size="large" style={{ width: '100%' }}>
        <div style={{ width: 300 }}>
          {canCreate && (
            <Button block type="dashed" icon={<PlusOutlined />} onClick={() => editCalendar('new')}>
              Nova agenda
            </Button>
          )}
          <List
            loading={calendars.isPending}
            dataSource={calendars.data ?? []}
            renderItem={(calendar) => (
              <List.Item
                style={{
                  cursor: 'pointer',
                  background: selected?.id === calendar.id ? '#f5f5f5' : undefined,
                }}
                onClick={() => setSelectedId(calendar.id)}
              >
                <List.Item.Meta
                  avatar={<span style={{ color: calendar.cor, fontSize: 24 }}>●</span>}
                  title={calendar.nome}
                  description={calendar.visibilidade === 'publica' ? 'Pública' : 'Restrita'}
                />
              </List.Item>
            )}
          />
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          {!selected ? (
            <Typography.Text type="secondary">Selecione uma agenda.</Typography.Text>
          ) : (
            <Tabs
              items={[
                {
                  key: 'dados',
                  label: 'Classificação',
                  children: (
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Typography.Title level={4}>{selected.nome}</Typography.Title>
                      <Space wrap>
                        <Tag color={selected.cor}>
                          {fronts.find(([key]) => key === selected.frente_comunidade)?.[1]}
                        </Tag>
                        <Tag>{selected.natureza_candidato}</Tag>
                        <Tag>{selected.tipo_agenda.replaceAll('_', ' ')}</Tag>
                        <Tag>{selected.visibilidade}</Tag>
                      </Space>
                      <Typography.Paragraph>
                        {selected.descricao || 'Sem descrição.'}
                      </Typography.Paragraph>
                      {canManage && (
                        <Space>
                          <Button icon={<EditOutlined />} onClick={() => editCalendar(selected)}>
                            Editar agenda
                          </Button>
                          {!selected.padrao && selected.permissoes.includes('excluir') && (
                            <Popconfirm
                              title="Excluir esta agenda?"
                              description="A agenda só pode ser excluída quando não possui compromissos."
                              onConfirm={async () => {
                                try {
                                  await deleteCalendar(selected.id);
                                  setSelectedId(null);
                                  AppToast.success('Agenda excluída.');
                                  await refresh();
                                } catch (error) {
                                  AppToast.error(normalizeApiError(error).message);
                                }
                              }}
                            >
                              <Button danger icon={<DeleteOutlined />}>
                                Excluir agenda
                              </Button>
                            </Popconfirm>
                          )}
                        </Space>
                      )}
                    </Space>
                  ),
                },
                ...(selected.permissoes.includes('administrar_usuarios')
                  ? [
                      {
                        key: 'usuarios',
                        label: (
                          <span>
                            <TeamOutlined /> Usuários
                          </span>
                        ),
                        children: (
                          <>
                            <Form
                              form={memberForm}
                              layout="vertical"
                              onFinish={(values) => saveMember.mutate(values)}
                            >
                              <Form.Item
                                name="usuario_id"
                                label="Pessoa autorizada"
                                rules={[{ required: true }]}
                              >
                                <Select showSearch optionFilterProp="label" options={userOptions} />
                              </Form.Item>
                              <Space wrap>
                                {permissionOptions.map(([key, label]) => (
                                  <Form.Item
                                    key={key}
                                    name={key}
                                    valuePropName="checked"
                                    initialValue={key === 'pode_visualizar'}
                                  >
                                    <Checkbox>{label}</Checkbox>
                                  </Form.Item>
                                ))}
                              </Space>
                              <Button
                                htmlType="submit"
                                type="primary"
                                loading={saveMember.isPending}
                              >
                                Salvar acesso
                              </Button>
                            </Form>
                            <List
                              dataSource={members.data ?? []}
                              renderItem={(member) => (
                                <List.Item
                                  actions={[
                                    <Popconfirm
                                      key="remove"
                                      title="Remover este acesso?"
                                      onConfirm={async () => {
                                        await removeCalendarMember(selected.id, member.usuario_id);
                                        await queryClient.invalidateQueries({
                                          queryKey: ['agenda', 'agenda-usuarios', selected.id],
                                        });
                                      }}
                                    >
                                      <Button type="text" danger icon={<DeleteOutlined />} />
                                    </Popconfirm>,
                                  ]}
                                >
                                  <List.Item.Meta title={member.nome} description={member.email} />
                                </List.Item>
                              )}
                            />
                          </>
                        ),
                      },
                    ]
                  : []),
                ...(globalPermissions.includes('agenda.integrar_google') && canManage
                  ? [
                      {
                        key: 'google',
                        label: (
                          <span>
                            <GoogleOutlined /> Google Agenda
                          </span>
                        ),
                        children: (
                          <Space direction="vertical" style={{ width: '100%' }}>
                            <Button icon={<GoogleOutlined />} onClick={connectGoogle}>
                              Conectar conta Google
                            </Button>
                            <Button onClick={() => setGoogleReady(true)}>
                              Selecionar agenda Google
                            </Button>
                            {googleReady && (
                              <Form
                                form={googleForm}
                                layout="vertical"
                                onFinish={(values) => googleLink.mutate(values)}
                              >
                                <Form.Item
                                  name="google_calendar_id"
                                  label="Agenda Google"
                                  rules={[{ required: true }]}
                                >
                                  <Select
                                    loading={googleCalendars.isPending}
                                    options={(googleCalendars.data ?? []).map((item) => ({
                                      value: item.id,
                                      label: `${item.nome}${item.principal ? ' (principal)' : ''}`,
                                    }))}
                                  />
                                </Form.Item>
                                <Form.Item
                                  name="direcao"
                                  label="Direção"
                                  initialValue="bidirecional"
                                >
                                  <Select
                                    options={[
                                      { value: 'bidirecional', label: 'Bidirecional' },
                                      { value: 'sistema_google', label: 'Sistema → Google' },
                                      { value: 'google_sistema', label: 'Google → Sistema' },
                                    ]}
                                  />
                                </Form.Item>
                                <Button
                                  htmlType="submit"
                                  type="primary"
                                  loading={googleLink.isPending}
                                >
                                  Vincular
                                </Button>
                              </Form>
                            )}
                            {selected.google_integracao && (
                              <Space wrap>
                                <Tag color="green">
                                  {selected.google_integracao.google_calendar_nome}
                                </Tag>
                                <Button
                                  icon={<SyncOutlined />}
                                  loading={sync.isPending}
                                  onClick={() => sync.mutate()}
                                >
                                  Sincronizar agora
                                </Button>
                                <Popconfirm
                                  title="Desvincular do Google?"
                                  onConfirm={async () => {
                                    await unlinkGoogleCalendar(selected.id);
                                    await refresh();
                                  }}
                                >
                                  <Button danger>Desvincular</Button>
                                </Popconfirm>
                              </Space>
                            )}
                          </Space>
                        ),
                      },
                    ]
                  : []),
              ]}
            />
          )}
        </div>
      </Space>

      <Modal
        open={editing !== null}
        title={editing === 'new' ? 'Nova agenda' : 'Editar agenda'}
        okText="Salvar"
        confirmLoading={saveCalendar.isPending}
        onCancel={() => setEditing(null)}
        onOk={() => calendarForm.validateFields().then((values) => saveCalendar.mutate(values))}
      >
        <Form form={calendarForm} layout="vertical">
          <Form.Item name="nome" label="Nome" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="descricao" label="Descrição">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item
            name="natureza_candidato"
            label="Agenda do candidato"
            rules={[{ required: true }]}
          >
            <Select
              options={[
                { value: 'rede', label: 'Rede' },
                { value: 'recurso', label: 'Recurso' },
                { value: 'rua', label: 'Rua' },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="frente_comunidade"
            label="Frente/Comunidade"
            rules={[{ required: true }]}
          >
            <Select options={fronts.map(([value, label]) => ({ value, label }))} />
          </Form.Item>
          <Form.Item name="tipo_agenda" label="Tipo de agenda" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'fixa_campanha', label: 'Agenda fixa da campanha' },
                { value: 'agenda_aberta', label: 'Agenda aberta' },
                { value: 'agenda_candidato', label: 'Agenda do candidato' },
              ]}
            />
          </Form.Item>
          <Form.Item name="visibilidade" label="Visibilidade" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'publica', label: 'Pública' },
                { value: 'restrita', label: 'Restrita' },
              ]}
            />
          </Form.Item>
          <Form.Item name="cor" label="Cor" rules={[{ required: true }]}>
            <Input type="color" />
          </Form.Item>
        </Form>
      </Modal>
    </Modal>
  );
}
