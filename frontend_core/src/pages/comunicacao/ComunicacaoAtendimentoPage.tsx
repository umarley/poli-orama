import {
  CloseCircleOutlined,
  DeleteOutlined,
  PhoneOutlined,
  PlusOutlined,
  StopOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Empty,
  Form,
  Input,
  List,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Spin,
  Switch,
  Tag,
  Timeline,
  Typography,
} from 'antd';
import dayjs from 'dayjs';
import { useEffect, useMemo, useState } from 'react';

import { AttachmentsPanel } from '@/components/arquivos/AttachmentsPanel';
import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  ElectoralLocationFields,
} from '@/components/territorios/ElectoralLocationFields';
import type { PessoaContato, TipoContato } from '@/modules/cadastro/types';
import {
  addAttendanceContact,
  addAttendanceDocument,
  addAttendanceInteraction,
  closeAttendance,
  deleteAttendanceContact,
  getCurrentAttendance,
  invalidateAttendance,
  listAttendanceChannels,
  listRejectionReasons,
  startAttendance,
  updateAttendance,
  updateAttendanceContact,
  updateAttendancePerson,
} from '@/modules/comunicacao/atendimento-service';
import type {
  Attendance,
  AttendanceClosePayload,
  AttendancePersonUpdate,
  AttendanceStatus,
  CommunicationChannel,
  VoteIntention,
} from '@/modules/comunicacao/atendimento-types';
import { listarEstados, listarMunicipios } from '@/modules/territorios/territorios-service';
import { normalizeApiError } from '@/services/api/api-error';
import { formatPhoneContact, isValidPhoneContact } from '@/utils/phone-format';

import styles from './ComunicacaoPage.module.css';

const sexOptions = [
  { value: 'F', label: 'Feminino' },
  { value: 'M', label: 'Masculino' },
  { value: 'O', label: 'Outro' },
  { value: 'N', label: 'Prefere não informar' },
];

const intentionOptions = [
  { value: 'votara', label: 'Votará no candidato' },
  { value: 'nao_votara', label: 'Não votará no candidato' },
  { value: 'indeciso', label: 'Ainda está indeciso' },
  { value: 'nao_respondeu', label: 'Preferiu não responder' },
];

const closeStatusOptions = [
  { value: 'concluido', label: 'Concluído' },
  { value: 'sem_resposta', label: 'Sem resposta' },
  { value: 'numero_invalido', label: 'Número inválido' },
  { value: 'interrompido', label: 'Interrompido' },
];

const documentTypeOptions = [
  { value: 'cpf', label: 'CPF' },
  { value: 'rg', label: 'RG' },
  { value: 'titulo_eleitor', label: 'Título de eleitor' },
  { value: 'cnh', label: 'CNH' },
  { value: 'passaporte', label: 'Passaporte' },
  { value: 'outro', label: 'Outro' },
];
const phoneContactTypes = new Set<TipoContato>(['telefone', 'celular', 'whatsapp']);
const contactTypeOptions: Array<{ value: TipoContato; label: string }> = [
  { value: 'email', label: 'E-mail' },
  { value: 'telefone', label: 'Telefone' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'celular', label: 'Celular' },
];

const intentionLabels: Record<VoteIntention, string> = {
  votara: 'Votará no candidato',
  nao_votara: 'Não votará no candidato',
  indeciso: 'Ainda está indeciso',
  nao_respondeu: 'Preferiu não responder',
};

const statusLabels: Record<AttendanceStatus, string> = {
  em_atendimento: 'Em atendimento',
  concluido: 'Concluído',
  sem_resposta: 'Sem resposta',
  numero_invalido: 'Número inválido',
  interrompido: 'Interrompido',
};

interface PersonFormValues {
  nome_completo: string;
  data_nascimento?: dayjs.Dayjs | null;
  sexo?: 'M' | 'F' | 'O' | 'N' | null;
  titulo_eleitor?: string;
  municipio_voto_uf_ibge?: number;
  codigo_municipio_ibge?: number;
  zona_eleitoral_id?: number;
  secao_eleitoral_id?: number;
  local_votacao_id?: number;
}

interface AttendanceFormValues {
  canal: number;
  canal_outro?: string;
  intencao_voto?: VoteIntention;
  motivo_rejeicao_id?: number;
  motivo_observacao?: string;
  observacao?: string;
}

interface CloseFormValues extends AttendanceFormValues {
  situacao: Exclude<AttendanceStatus, 'em_atendimento'>;
  motivo_encerramento?: string;
}

interface DocumentFormValues {
  tipo_documento: string;
  numero: string;
  orgao_emissor?: string;
  uf_emissor?: string;
}

interface InteractionFormValues {
  assunto?: string;
  conteudo: string;
  resultado?: string;
}

interface ContactFormValues {
  tipo_contato?: TipoContato;
  valor?: string;
  principal?: boolean;
  observacao?: string | null;
}

type ContactEditor =
  | { type: 'contact'; item: PessoaContato }
  | { type: 'new-contact' };

function formatContactValue(type: TipoContato, value: string): string {
  if (!phoneContactTypes.has(type)) return value;
  const digits = value.replace(/\D/g, '');
  const localDigits = digits.startsWith('55') && digits.length > 11 ? digits.slice(2) : digits;
  return formatPhoneContact(localDigits);
}

function isActive(attendance: Attendance | null | undefined) {
  return attendance?.situacao === 'em_atendimento' && !attendance.finalizado_em;
}

function isOtherChannel(channels: CommunicationChannel[], channelId?: number) {
  return channels.some((item) => item.id === channelId && item.codigo === 'outro');
}

export function ComunicacaoAtendimentoPage() {
  const queryClient = useQueryClient();
  const [personForm] = Form.useForm<PersonFormValues>();
  const [attendanceForm] = Form.useForm<AttendanceFormValues>();
  const [closeForm] = Form.useForm<CloseFormValues>();
  const [documentForm] = Form.useForm<DocumentFormValues>();
  const [interactionForm] = Form.useForm<InteractionFormValues>();
  const [contactForm] = Form.useForm<ContactFormValues>();
  const [invalidateForm] = Form.useForm<{ motivo_inativacao: string }>();
  const [closeOpen, setCloseOpen] = useState(false);
  const [invalidateOpen, setInvalidateOpen] = useState(false);
  const [contactEditor, setContactEditor] = useState<ContactEditor | null>(null);
  const watchedChannel = Form.useWatch('canal', attendanceForm);
  const watchedIntention = Form.useWatch('intencao_voto', attendanceForm);
  const watchedCloseChannel = Form.useWatch('canal', closeForm);
  const watchedCloseIntention = Form.useWatch('intencao_voto', closeForm);
  const watchedCloseStatus = Form.useWatch('situacao', closeForm);
  const selectedVoterStateCode = Form.useWatch('municipio_voto_uf_ibge', personForm) as
    | number
    | undefined;
  const selectedVoterCityCode = Form.useWatch('codigo_municipio_ibge', personForm) as
    | number
    | undefined;

  const attendanceQuery = useQuery({
    queryKey: ['comunicacao', 'atendimento', 'atual'],
    queryFn: getCurrentAttendance,
  });
  const reasonsQuery = useQuery({
    queryKey: ['comunicacao', 'motivos-rejeicao'],
    queryFn: listRejectionReasons,
  });
  const channelsQuery = useQuery({
    queryKey: ['comunicacao', 'atendimento', 'canais'],
    queryFn: listAttendanceChannels,
  });
  const estadosQuery = useQuery({
    queryKey: ['territorios', 'global', 'estados'],
    queryFn: listarEstados,
  });
  const voterMunicipiosQuery = useQuery({
    queryKey: ['territorios', 'global', 'municipios', selectedVoterStateCode],
    queryFn: () => listarMunicipios(selectedVoterStateCode),
    enabled: Boolean(selectedVoterStateCode),
  });

  const attendance = attendanceQuery.data ?? null;
  const active = isActive(attendance);

  useEffect(() => {
    document.title = 'Atendimento · Comunicação';
  }, []);

  useEffect(() => {
    if (!attendance) {
      personForm.resetFields();
      attendanceForm.resetFields();
      return;
    }
    personForm.setFieldsValue({
      nome_completo: attendance.pessoa.nome_completo,
      data_nascimento: attendance.pessoa.data_nascimento
        ? dayjs(attendance.pessoa.data_nascimento)
        : null,
      sexo: (attendance.pessoa.sexo as PersonFormValues['sexo']) ?? null,
      titulo_eleitor: attendance.pessoa.titulo_eleitor ?? undefined,
      municipio_voto_uf_ibge: attendance.pessoa.codigo_municipio_ibge
        ? Math.floor(attendance.pessoa.codigo_municipio_ibge / 100000)
        : undefined,
      codigo_municipio_ibge: attendance.pessoa.codigo_municipio_ibge ?? undefined,
      zona_eleitoral_id: attendance.pessoa.zona_eleitoral_id ?? undefined,
      secao_eleitoral_id: attendance.pessoa.secao_eleitoral_id ?? undefined,
      local_votacao_id: attendance.pessoa.local_votacao_id ?? undefined,
    });
    attendanceForm.setFieldsValue({
      canal: attendance.canal,
      canal_outro: attendance.canal_outro ?? undefined,
      intencao_voto: attendance.intencao_voto ?? undefined,
      motivo_rejeicao_id: attendance.motivo_rejeicao_id ?? undefined,
      motivo_observacao: attendance.motivo_observacao ?? undefined,
      observacao: attendance.observacao ?? undefined,
    });
  }, [attendance, attendanceForm, personForm]);

  const reasonOptions = useMemo(
    () => (reasonsQuery.data ?? []).map((item) => ({ value: item.id, label: item.nome })),
    [reasonsQuery.data],
  );
  const channelOptions = useMemo(
    () => (channelsQuery.data ?? []).map((item) => ({ value: item.id, label: item.nome })),
    [channelsQuery.data],
  );
  const voterStateOptions = useMemo(
    () =>
      (estadosQuery.data ?? []).map((estado) => ({
        value: estado.codigo_ibge,
        label: `${estado.uf} - ${estado.nome}`,
      })),
    [estadosQuery.data],
  );
  const voterCityOptions = useMemo(
    () =>
      (voterMunicipiosQuery.data ?? []).map((municipio) => ({
        value: municipio.codigo_ibge,
        label: municipio.nome,
      })),
    [voterMunicipiosQuery.data],
  );
  const otherChannelSelected = isOtherChannel(channelsQuery.data ?? [], watchedChannel);
  const otherCloseChannelSelected = isOtherChannel(channelsQuery.data ?? [], watchedCloseChannel);

  const startMutation = useMutation({
    mutationFn: startAttendance,
    onSuccess: async (result) => {
      AppToast.success(`Atendimento iniciado com ${result.pessoa.nome_completo}.`);
      await queryClient.invalidateQueries({ queryKey: ['comunicacao', 'atendimento', 'atual'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const savePersonMutation = useMutation({
    mutationFn: (values: PersonFormValues) => {
      if (!attendance) throw new Error('Nenhum atendimento ativo.');
      const payload: AttendancePersonUpdate = {
        nome_completo: values.nome_completo,
        data_nascimento: values.data_nascimento
          ? values.data_nascimento.format('YYYY-MM-DD')
          : null,
        sexo: values.sexo ?? null,
        titulo_eleitor: values.titulo_eleitor ?? null,
        codigo_municipio_ibge: values.codigo_municipio_ibge ?? null,
        zona_eleitoral_id: values.zona_eleitoral_id ?? null,
        secao_eleitoral_id: values.secao_eleitoral_id ?? null,
        local_votacao_id: values.local_votacao_id ?? null,
      };
      return updateAttendancePerson(attendance.id, payload);
    },
    onSuccess: async () => {
      AppToast.success('Cadastro atualizado neste atendimento.');
      await queryClient.invalidateQueries({ queryKey: ['comunicacao', 'atendimento', 'atual'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const saveAttendanceMutation = useMutation({
    mutationFn: (values: AttendanceFormValues) => {
      if (!attendance) throw new Error('Nenhum atendimento ativo.');
      return updateAttendance(attendance.id, {
        canal: values.canal,
        canal_outro: otherChannelSelected ? values.canal_outro : null,
        intencao_voto: values.intencao_voto ?? null,
        motivo_rejeicao_id:
          values.intencao_voto === 'nao_votara' ? values.motivo_rejeicao_id : null,
        motivo_observacao: values.motivo_observacao ?? null,
        observacao: values.observacao ?? null,
      });
    },
    onSuccess: async () => {
      AppToast.success('Dados do atendimento salvos.');
      await queryClient.invalidateQueries({ queryKey: ['comunicacao', 'atendimento', 'atual'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const documentMutation = useMutation({
    mutationFn: (values: DocumentFormValues) => {
      if (!attendance) throw new Error('Nenhum atendimento ativo.');
      return addAttendanceDocument(attendance.id, values);
    },
    onSuccess: async () => {
      AppToast.success('Documento adicionado.');
      documentForm.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['comunicacao', 'atendimento', 'atual'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const interactionMutation = useMutation({
    mutationFn: (values: InteractionFormValues) => {
      if (!attendance) throw new Error('Nenhum atendimento ativo.');
      return addAttendanceInteraction(attendance.id, values);
    },
    onSuccess: async () => {
      AppToast.success('Interação registrada.');
      interactionForm.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['comunicacao', 'atendimento', 'atual'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const closeMutation = useMutation({
    mutationFn: (values: CloseFormValues) => {
      if (!attendance) throw new Error('Nenhum atendimento ativo.');
      const payload: AttendanceClosePayload = {
        situacao: values.situacao,
        canal: values.canal,
        canal_outro: isOtherChannel(channelsQuery.data ?? [], values.canal)
          ? values.canal_outro
          : null,
        intencao_voto: values.intencao_voto as VoteIntention,
        motivo_rejeicao_id:
          values.intencao_voto === 'nao_votara' ? values.motivo_rejeicao_id : null,
        motivo_observacao: values.motivo_observacao ?? null,
        observacao: values.observacao ?? null,
        motivo_encerramento: values.motivo_encerramento ?? null,
      };
      return closeAttendance(attendance.id, payload);
    },
    onSuccess: async () => {
      AppToast.success('Atendimento encerrado.');
      setCloseOpen(false);
      closeForm.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['comunicacao', 'atendimento', 'atual'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const invalidateMutation = useMutation({
    mutationFn: (values: { motivo_inativacao: string }) => {
      if (!attendance) throw new Error('Nenhum atendimento ativo.');
      return invalidateAttendance(attendance.id, values.motivo_inativacao);
    },
    onSuccess: async () => {
      AppToast.success('Contato marcado como inválido e cadastro inativado.');
      setInvalidateOpen(false);
      invalidateForm.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['comunicacao', 'atendimento', 'atual'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const saveContactMutation = useMutation({
    mutationFn: async (values: ContactFormValues) => {
      if (!attendance || !contactEditor) throw new Error('Nenhum atendimento ativo.');
      if (contactEditor.type === 'contact') {
        return updateAttendanceContact(attendance.id, contactEditor.item.id, {
          valor: String(values.valor),
          principal: Boolean(values.principal),
          observacao: values.observacao || null,
        });
      }
      return addAttendanceContact(attendance.id, {
        tipo_contato: values.tipo_contato as TipoContato,
        valor: String(values.valor),
        principal: Boolean(values.principal),
        observacao: values.observacao || null,
      });
    },
    onSuccess: async () => {
      AppToast.success(
        contactEditor?.type === 'new-contact' ? 'Contato adicionado.' : 'Contato atualizado.',
      );
      setContactEditor(null);
      contactForm.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['comunicacao', 'atendimento', 'atual'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const removeContactMutation = useMutation({
    mutationFn: (contactId: number) => {
      if (!attendance) throw new Error('Nenhum atendimento ativo.');
      return deleteAttendanceContact(attendance.id, contactId);
    },
    onSuccess: async () => {
      AppToast.success('Contato removido.');
      await queryClient.invalidateQueries({ queryKey: ['comunicacao', 'atendimento', 'atual'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const selectedContactType = Form.useWatch('tipo_contato', contactForm) as TipoContato | undefined;
  const isPhoneContact =
    contactEditor?.type === 'contact'
      ? phoneContactTypes.has(contactEditor.item.tipo_contato)
      : selectedContactType
        ? phoneContactTypes.has(selectedContactType)
        : false;
  const contactTypeForEditor =
    contactEditor?.type === 'contact' ? contactEditor.item.tipo_contato : selectedContactType;
  const contacts = attendance?.pessoa.contatos ?? [];
  const contactOptionsForNewContact = contactTypeOptions.map((option) => ({
    ...option,
    disabled: contacts.some((contact) => contact.tipo_contato === option.value),
  }));
  const hasAvailableContactType = contactOptionsForNewContact.some((option) => !option.disabled);
  const noContactItems = (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Nenhum vínculo registrado" />
  );

  const openContactEditor = (next: ContactEditor) => {
    setContactEditor(next);
    contactForm.resetFields();
    if (next.type === 'contact') {
      contactForm.setFieldsValue({
        valor: formatContactValue(next.item.tipo_contato, next.item.valor),
        principal: next.item.principal,
        observacao: next.item.observacao,
      });
      return;
    }
    const firstAvailableContactType =
      contactTypeOptions.find(
        (option) => !contacts.some((contact) => contact.tipo_contato === option.value),
      )?.value ?? 'email';
    contactForm.setFieldsValue({
      tipo_contato: firstAvailableContactType,
      principal: false,
    });
  };

  const openCloseModal = () => {
    if (!attendance) return;
    closeForm.setFieldsValue({
      situacao: 'concluido',
      canal: attendance.canal,
      canal_outro: attendance.canal_outro ?? undefined,
      intencao_voto: attendance.intencao_voto ?? undefined,
      motivo_rejeicao_id: attendance.motivo_rejeicao_id ?? undefined,
      motivo_observacao: attendance.motivo_observacao ?? undefined,
      observacao: attendance.observacao ?? undefined,
    });
    setCloseOpen(true);
  };

  return (
    <div className={styles.page}>
      <PageHeader
        title="Atendimento"
        description="Selecione um eleitor disponível, registre o contato e atualize o cadastro somente enquanto o atendimento estiver ativo."
        breadcrumbs={[
          { label: 'Comunicação', to: '/comunicacao' },
          { label: 'Atendimento' },
        ]}
        actions={
          <Space wrap>
            <Button
              type="primary"
              icon={<PhoneOutlined />}
              loading={startMutation.isPending}
              onClick={() => startMutation.mutate()}
            >
              Novo atendimento
            </Button>
            <Button disabled={!active} onClick={openCloseModal}>
              Encerrar atendimento
            </Button>
            <Button
              danger
              icon={<StopOutlined />}
              disabled={!active}
              onClick={() => setInvalidateOpen(true)}
            >
              Marcar contato como inválido
            </Button>
          </Space>
        }
      />

      {attendanceQuery.isError && (
        <Alert
          type="error"
          showIcon
          message="Não foi possível carregar o atendimento."
          description={normalizeApiError(attendanceQuery.error).message}
        />
      )}

      {attendanceQuery.isPending ? (
        <Spin />
      ) : !attendance ? (
        <Card>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="Nenhum atendimento em andamento. Clique em Novo atendimento para selecionar um eleitor."
          />
        </Card>
      ) : (
        <>
          {!active && (
            <Alert
              type="info"
              showIcon
              message="Este atendimento foi encerrado."
              description="Os dados permanecem disponíveis para consulta. O cadastro da pessoa não pode mais ser alterado por esta tela."
            />
          )}
          <div className={styles.layout}>
            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <Card
                title={attendance.pessoa.nome_completo}
                extra={<Tag color={active ? 'processing' : 'default'}>{statusLabels[attendance.situacao]}</Tag>}
              >
                <Descriptions size="small" column={1}>
                  <Descriptions.Item label="Telefone">
                    {attendance.pessoa.telefone || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="E-mail">{attendance.pessoa.email || '—'}</Descriptions.Item>
                  <Descriptions.Item label="Frente">
                    {attendance.pessoa.frentes.join(', ') || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Núcleo familiar">
                    {attendance.pessoa.nucleos_familiares.join(', ') || '—'}
                  </Descriptions.Item>
                </Descriptions>
                <div className={styles.tags} style={{ marginTop: 12 }}>
                  {attendance.pessoa.tags.length ? (
                    attendance.pessoa.tags.map((tag) => <Tag key={tag}>{tag}</Tag>)
                  ) : (
                    <Typography.Text type="secondary">Sem tags vinculadas</Typography.Text>
                  )}
                </div>
              </Card>

              <Card title="Atualização cadastral">
                <Form
                  form={personForm}
                  layout="vertical"
                  disabled={!active}
                  onFinish={(values) => savePersonMutation.mutate(values)}
                >
                  <Form.Item
                    name="nome_completo"
                    label="Nome"
                    rules={[{ required: true, min: 2, message: 'Informe o nome completo.' }]}
                  >
                    <Input />
                  </Form.Item>
                  <Form.Item name="data_nascimento" label="Data de nascimento">
                    <DatePicker format="DD/MM/YYYY" style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item name="sexo" label="Sexo">
                    <Select allowClear options={sexOptions} />
                  </Form.Item>
                  <Form.Item name="titulo_eleitor" label="Número do título de eleitor">
                    <Input />
                  </Form.Item>
                  <Row gutter={12}>
                    <Col xs={24} md={8}>
                      <Form.Item name="municipio_voto_uf_ibge" label="Estado do voto">
                        <Select
                          allowClear
                          showSearch
                          loading={estadosQuery.isPending}
                          optionFilterProp="label"
                          placeholder="Selecione"
                          options={voterStateOptions}
                          onChange={() => {
                            personForm.setFieldsValue({
                              codigo_municipio_ibge: undefined,
                              zona_eleitoral_id: undefined,
                              local_votacao_id: undefined,
                              secao_eleitoral_id: undefined,
                            });
                          }}
                        />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={16}>
                      <Form.Item name="codigo_municipio_ibge" label="Município do voto">
                        <Select
                          allowClear
                          showSearch
                          disabled={!selectedVoterStateCode}
                          loading={voterMunicipiosQuery.isFetching}
                          optionFilterProp="label"
                          placeholder={
                            selectedVoterStateCode ? 'Selecione' : 'Selecione o estado'
                          }
                          options={voterCityOptions}
                          onChange={() => {
                            personForm.setFieldsValue({
                              zona_eleitoral_id: undefined,
                              local_votacao_id: undefined,
                              secao_eleitoral_id: undefined,
                            });
                          }}
                        />
                      </Form.Item>
                    </Col>
                  </Row>
                  <ElectoralLocationFields
                    codigoMunicipioIbge={selectedVoterCityCode}
                    requireMunicipality
                  />
                  <Button
                    type="primary"
                    htmlType="submit"
                    icon={<UserOutlined />}
                    loading={savePersonMutation.isPending}
                    disabled={!active}
                  >
                    Salvar cadastro
                  </Button>
                </Form>
                <div style={{ marginTop: 16, marginBottom: 16 }}>
                  <Typography.Text style={{ display: 'block', marginBottom: 8 }}>
                    Observações cadastrais
                  </Typography.Text>
                  <Input.TextArea
                    rows={3}
                    disabled
                    value={attendance.pessoa.observacoes ?? ''}
                    placeholder="Nenhuma observação cadastral"
                  />
                </div>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                    <Typography.Title level={5} style={{ margin: 0 }}>
                      Contatos
                    </Typography.Title>
                    <Button
                      type="primary"
                      htmlType="button"
                      disabled={!active || !hasAvailableContactType}
                      onClick={() => openContactEditor({ type: 'new-contact' })}
                    >
                      Adicionar contato
                    </Button>
                  </Space>
                  <List
                    dataSource={contacts}
                    locale={{ emptyText: noContactItems }}
                    renderItem={(item) => (
                      <List.Item
                        actions={
                          active
                            ? [
                                <Button
                                  key="edit"
                                  type="link"
                                  htmlType="button"
                                  onClick={() => openContactEditor({ type: 'contact', item })}
                                >
                                  Editar
                                </Button>,
                                <Popconfirm
                                  key="remove"
                                  title="Remover contato?"
                                  description={`O contato ${formatContactValue(item.tipo_contato, item.valor)} será excluído deste cadastro.`}
                                  okText="Remover"
                                  cancelText="Cancelar"
                                  okButtonProps={{ danger: true }}
                                  onConfirm={() => removeContactMutation.mutateAsync(item.id)}
                                >
                                  <Button
                                    type="link"
                                    danger
                                    htmlType="button"
                                    icon={<DeleteOutlined />}
                                    loading={
                                      removeContactMutation.isPending &&
                                      removeContactMutation.variables === item.id
                                    }
                                  >
                                    Remover
                                  </Button>
                                </Popconfirm>,
                              ]
                            : []
                        }
                      >
                        <List.Item.Meta
                          title={
                            <Space>
                              {formatContactValue(item.tipo_contato, item.valor)}
                              {item.principal ? <Tag color="blue">Principal</Tag> : null}
                            </Space>
                          }
                          description={item.tipo_contato}
                        />
                      </List.Item>
                    )}
                  />
                </Space>
              </Card>

              <Card title="Documentos">
                <Form
                  form={documentForm}
                  layout="vertical"
                  disabled={!active}
                  onFinish={(values) => documentMutation.mutate(values)}
                >
                  <Form.Item name="tipo_documento" label="Tipo" rules={[{ required: true }]}>
                    <Select options={documentTypeOptions} />
                  </Form.Item>
                  <Form.Item name="numero" label="Número" rules={[{ required: true }]}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="orgao_emissor" label="Órgão emissor">
                    <Input />
                  </Form.Item>
                  <Form.Item name="uf_emissor" label="UF">
                    <Input maxLength={2} />
                  </Form.Item>
                  <Button
                    htmlType="submit"
                    icon={<PlusOutlined />}
                    loading={documentMutation.isPending}
                    disabled={!active}
                  >
                    Adicionar documento
                  </Button>
                </Form>
              </Card>

              <AttachmentsPanel
                entity="pessoa"
                entityId={attendance.pessoa.id}
                canEdit={active}
                enablePersonPhoto={active}
              />
            </Space>

            <Space direction="vertical" size={16} style={{ width: '100%' }}>
              <Card title="Registro do atendimento">
                <Descriptions size="small" column={1}>
                  <Descriptions.Item label="Início">
                    {dayjs(attendance.iniciado_em).format('DD/MM/YYYY HH:mm')}
                  </Descriptions.Item>
                  <Descriptions.Item label="Encerramento">
                    {attendance.finalizado_em
                      ? dayjs(attendance.finalizado_em).format('DD/MM/YYYY HH:mm')
                      : 'Em andamento'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Canal">
                    {attendance.canal_nome || '—'}
                    {attendance.canal_outro ? ` · ${attendance.canal_outro}` : ''}
                  </Descriptions.Item>
                  <Descriptions.Item label="Situação">{statusLabels[attendance.situacao]}</Descriptions.Item>
                </Descriptions>
                <Form
                  form={attendanceForm}
                  layout="vertical"
                  disabled={!active}
                  style={{ marginTop: 16 }}
                  onFinish={(values) => saveAttendanceMutation.mutate(values)}
                >
                  <Form.Item name="canal" label="Canal utilizado" rules={[{ required: true }]}>
                    <Select options={channelOptions} />
                  </Form.Item>
                  {otherChannelSelected && (
                    <Form.Item
                      name="canal_outro"
                      label="Qual canal foi utilizado?"
                      rules={[{ required: true, message: 'Informe o canal utilizado.' }]}
                    >
                      <Input />
                    </Form.Item>
                  )}
                  <Form.Item name="intencao_voto" label="Intenção de voto">
                    <Select allowClear options={intentionOptions} />
                  </Form.Item>
                  {watchedIntention === 'nao_votara' && (
                    <>
                      <Form.Item
                        name="motivo_rejeicao_id"
                        label="Motivo"
                        rules={[{ required: true, message: 'Informe o motivo da intenção negativa.' }]}
                      >
                        <Select options={reasonOptions} />
                      </Form.Item>
                      <Form.Item name="motivo_observacao" label="Complemento do motivo">
                        <Input.TextArea rows={2} />
                      </Form.Item>
                    </>
                  )}
                  <Form.Item name="observacao" label="Observações do atendimento">
                    <Input.TextArea rows={3} />
                  </Form.Item>
                  <Button
                    type="primary"
                    htmlType="submit"
                    loading={saveAttendanceMutation.isPending}
                    disabled={!active}
                  >
                    Salvar atendimento
                  </Button>
                </Form>
              </Card>

              <Card title="Histórico de intenção de voto">
                {attendance.historico_intencao.length ? (
                  <Timeline
                    items={attendance.historico_intencao.map((item) => ({
                      children: (
                        <>
                          <Typography.Text strong>
                            {intentionLabels[item.intencao_voto]}
                          </Typography.Text>
                          <div>
                            {item.motivo_rejeicao_nome}
                            {item.motivo_observacao ? ` · ${item.motivo_observacao}` : ''}
                          </div>
                          <Typography.Text type="secondary">
                            {dayjs(item.criado_em).format('DD/MM/YYYY HH:mm')}
                            {item.registrado_por_nome ? ` · ${item.registrado_por_nome}` : ''}
                          </Typography.Text>
                        </>
                      ),
                    }))}
                  />
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Nenhuma resposta registrada." />
                )}
              </Card>

              <Card title="Histórico de interações">
                <Form
                  form={interactionForm}
                  layout="vertical"
                  disabled={!active}
                  onFinish={(values) => interactionMutation.mutate(values)}
                >
                  <Form.Item name="assunto" label="Assunto">
                    <Input />
                  </Form.Item>
                  <Form.Item
                    name="conteudo"
                    label="Registro da interação"
                    rules={[{ required: true, min: 2 }]}
                  >
                    <Input.TextArea rows={3} />
                  </Form.Item>
                  <Form.Item name="resultado" label="Resultado">
                    <Input />
                  </Form.Item>
                  <Button
                    htmlType="submit"
                    icon={<PlusOutlined />}
                    loading={interactionMutation.isPending}
                    disabled={!active}
                  >
                    Registrar interação
                  </Button>
                </Form>
                {attendance.interacoes.length ? (
                  <Timeline
                    style={{ marginTop: 16 }}
                    items={attendance.interacoes.map((item) => ({
                      children: (
                        <>
                          <Typography.Text strong>{item.assunto || 'Interação'}</Typography.Text>
                          <div>{item.conteudo}</div>
                          <Typography.Text type="secondary">
                            {dayjs(item.data_interacao).format('DD/MM/YYYY HH:mm')}
                            {item.registrado_por_nome ? ` · ${item.registrado_por_nome}` : ''}
                            {item.resultado ? ` · ${item.resultado}` : ''}
                          </Typography.Text>
                        </>
                      ),
                    }))}
                  />
                ) : (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="Nenhuma interação registrada."
                    style={{ marginTop: 16 }}
                  />
                )}
              </Card>
            </Space>
          </div>
        </>
      )}

      <Modal
        title="Encerrar atendimento"
        open={closeOpen}
        okText="Confirmar encerramento"
        confirmLoading={closeMutation.isPending}
        onCancel={() => setCloseOpen(false)}
        onOk={() => closeForm.submit()}
      >
        <Form form={closeForm} layout="vertical" onFinish={(values) => closeMutation.mutate(values)}>
          <Form.Item name="situacao" label="Situação" rules={[{ required: true }]}>
            <Select options={closeStatusOptions} />
          </Form.Item>
          <Form.Item name="canal" label="Canal utilizado" rules={[{ required: true }]}>
            <Select options={channelOptions} />
          </Form.Item>
          {otherCloseChannelSelected && (
            <Form.Item
              name="canal_outro"
              label="Qual canal foi utilizado?"
              rules={[{ required: true, message: 'Informe o canal utilizado.' }]}
            >
              <Input />
            </Form.Item>
          )}
          <Form.Item name="intencao_voto" label="Intenção de voto" rules={[{ required: true }]}>
            <Select options={intentionOptions} />
          </Form.Item>
          {watchedCloseIntention === 'nao_votara' && (
            <>
              <Form.Item
                name="motivo_rejeicao_id"
                label="Motivo"
                rules={[{ required: true, message: 'Informe o motivo da intenção negativa.' }]}
              >
                <Select options={reasonOptions} />
              </Form.Item>
              <Form.Item name="motivo_observacao" label="Complemento do motivo">
                <Input.TextArea rows={2} />
              </Form.Item>
            </>
          )}
          {(watchedCloseStatus === 'interrompido' || watchedCloseStatus === 'numero_invalido') && (
            <Form.Item
              name="motivo_encerramento"
              label="Motivo do encerramento"
              rules={[{ required: true, message: 'Informe o motivo do encerramento.' }]}
            >
              <Input.TextArea rows={2} />
            </Form.Item>
          )}
          <Form.Item name="observacao" label="Observações">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Marcar contato como inválido"
        open={invalidateOpen}
        okText="Confirmar inativação"
        okButtonProps={{ danger: true, icon: <CloseCircleOutlined /> }}
        confirmLoading={invalidateMutation.isPending}
        onCancel={() => setInvalidateOpen(false)}
        onOk={() => invalidateForm.submit()}
      >
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message="Use somente se o cadastro não corresponder a uma pessoa real ou se não for possível nenhum contato."
          description="Se os dados pertencerem a outra pessoa, corrija o cadastro neste atendimento em vez de inativar."
        />
        <Form
          form={invalidateForm}
          layout="vertical"
          onFinish={(values) => invalidateMutation.mutate(values)}
        >
          <Form.Item
            name="motivo_inativacao"
            label="Motivo da inativação"
            rules={[{ required: true, min: 5, message: 'Informe o motivo com pelo menos 5 caracteres.' }]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={Boolean(contactEditor)}
        title={contactEditor?.type === 'new-contact' ? 'Adicionar contato' : 'Editar contato'}
        okText="Salvar"
        cancelText="Cancelar"
        confirmLoading={saveContactMutation.isPending}
        onCancel={() => setContactEditor(null)}
        onOk={() =>
          contactForm.validateFields().then((values) => saveContactMutation.mutate(values))
        }
      >
        <Form form={contactForm} layout="vertical" requiredMark={false}>
          {contactEditor?.type === 'new-contact' ? (
            <Form.Item name="tipo_contato" label="Canal" rules={[{ required: true }]}>
              <Select
                options={contactOptionsForNewContact}
                onChange={() => contactForm.setFieldValue('valor', undefined)}
              />
            </Form.Item>
          ) : null}
          <Form.Item
            name="valor"
            label="Contato"
            normalize={(value?: string) =>
              isPhoneContact && value ? formatPhoneContact(value) : value
            }
            rules={[
              { required: true, message: 'Informe o contato' },
              {
                validator: async (_, value?: string) => {
                  const valueType = contactTypeForEditor;
                  if (!value || !valueType) return;
                  if (valueType === 'email') {
                    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                    if (!emailPattern.test(value)) {
                      throw new Error('Informe um e-mail valido');
                    }
                  }
                  if (phoneContactTypes.has(valueType) && !isValidPhoneContact(value)) {
                    throw new Error('Informe um telefone com DDD');
                  }
                },
              },
            ]}
          >
            <Input
              inputMode={isPhoneContact ? 'tel' : undefined}
              maxLength={isPhoneContact ? 15 : undefined}
              placeholder={isPhoneContact ? '(00) 00000-0000' : undefined}
            />
          </Form.Item>
          <Form.Item name="principal" label="Principal" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="observacao" label="Observação">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
