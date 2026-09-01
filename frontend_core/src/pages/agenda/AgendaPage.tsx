import {
  CalendarOutlined,
  DownloadOutlined,
  PlusOutlined,
  SettingOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Calendar,
  Card,
  Col,
  DatePicker,
  Form,
  Input,
  List,
  Modal,
  Row,
  Segmented,
  Select,
  Space,
  Table,
  Tag,
} from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { AppToast } from '@/components/feedback/AppToast';
import { RemotePersonSelect } from '@/components/forms/RemotePersonSelect';
import { RemoteTerritorySelect } from '@/components/forms/RemoteTerritorySelect';
import { PageHeader } from '@/components/layout/PageHeader';
import { listarLiderancas } from '@/modules/cadastro/pessoas-service';
import {
  createEvent,
  downloadAgenda,
  listEvents,
  listEventStatuses,
  listEventTypes,
  listCalendars,
} from '@/modules/agenda/agenda-service';
import type { AgendaFilters } from '@/modules/agenda/types';
import { listarTerritorios } from '@/modules/territorios/territorios-service';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';

import { CalendarManagementModal } from './CalendarManagementModal';

interface EventForm {
  agenda_id: number;
  titulo: string;
  descricao?: string;
  tipo_evento_id?: number;
  status_evento_id?: number;
  periodo: [Dayjs, Dayjs?];
  local_nome?: string;
  territorio_id?: number;
  responsavel_pessoa_id: number;
}

const statusColors: Record<string, string> = {
  planejado: 'default',
  confirmado: 'processing',
  realizado: 'success',
  cancelado: 'error',
  remarcado: 'warning',
};

export function AgendaPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const permissions = useSessionStore((state) => state.user?.permissions ?? []);
  const [view, setView] = useState<string>('Mês');
  const [referenceDate, setReferenceDate] = useState(dayjs());
  const [filters, setFilters] = useState<AgendaFilters>({});
  const [modalOpen, setModalOpen] = useState(false);
  const [managementOpen, setManagementOpen] = useState(false);
  const [form] = Form.useForm<EventForm>();
  const monthFilters = useMemo(() => {
    const periodStart =
      view === 'Semana' ? referenceDate.startOf('week') : referenceDate.startOf('month');
    const periodEnd =
      view === 'Semana'
        ? referenceDate.add(1, 'week').startOf('week')
        : referenceDate.add(1, 'month').startOf('month');
    return {
      data_inicio: periodStart.toISOString(),
      data_fim: periodEnd.toISOString(),
      ...filters,
    };
  }, [filters, referenceDate, view]);
  const events = useQuery({
    queryKey: ['agenda', 'eventos', monthFilters],
    queryFn: () => listEvents(monthFilters),
  });
  const types = useQuery({ queryKey: ['agenda', 'tipos'], queryFn: listEventTypes });
  const calendars = useQuery({ queryKey: ['agenda', 'agendas'], queryFn: listCalendars });
  const statuses = useQuery({
    queryKey: ['agenda', 'status'],
    queryFn: listEventStatuses,
  });
  const territories = useQuery({
    queryKey: ['territorios', 'agenda'],
    queryFn: () => listarTerritorios(),
  });
  const leaderships = useQuery({
    queryKey: ['cadastro', 'liderancas', 'agenda'],
    queryFn: () => listarLiderancas(),
  });
  const creation = useMutation({
    mutationFn: (values: EventForm) =>
      createEvent({
        titulo: values.titulo,
        agenda_id: values.agenda_id,
        descricao: values.descricao,
        tipo_evento_id: values.tipo_evento_id,
        status_evento_id: values.status_evento_id,
        data_inicio: values.periodo[0].toISOString(),
        data_fim: values.periodo[1]?.toISOString(),
        local_nome: values.local_nome,
        territorio_id: values.territorio_id,
        responsavel_pessoa_id: values.responsavel_pessoa_id,
      }),
    onSuccess: async (item) => {
      AppToast.success('Evento criado.');
      setModalOpen(false);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['agenda'] });
      navigate(`/agenda/eventos/${item.id}`);
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const exportMutation = useMutation({
    mutationFn: () => downloadAgenda(monthFilters),
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const items = events.data ?? [];
  const weekItems = items.filter((item) => {
    const value = dayjs(item.data_inicio);
    return (
      !value.isBefore(referenceDate.startOf('week')) &&
      value.isBefore(referenceDate.add(1, 'week').startOf('week'))
    );
  });
  const renderEvent = (item: (typeof items)[number]) => (
    <Button type="link" size="small" onClick={() => navigate(`/agenda/eventos/${item.id}`)}>
      <span style={{ color: item.agenda_cor }}>●</span> {dayjs(item.data_inicio).format('HH:mm')}{' '}
      {item.titulo}
    </Button>
  );
  return (
    <div>
      <PageHeader
        title="Agenda e eventos"
        description="Calendário político, participantes, pautas, presença e demandas."
        breadcrumbs={[{ label: 'Início', to: '/dashboard' }, { label: 'Agenda' }]}
        actions={
          <Space>
            <Button icon={<SettingOutlined />} onClick={() => setManagementOpen(true)}>
              Agendas
            </Button>
            {permissions.includes('agenda.exportar') && (
              <Button
                icon={<DownloadOutlined />}
                loading={exportMutation.isPending}
                onClick={() => exportMutation.mutate()}
              >
                Exportar
              </Button>
            )}
            {permissions.includes('agenda.criar') && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
                Novo evento
              </Button>
            )}
          </Space>
        }
      />
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[12, 12]}>
          <Col xs={24} md={6}>
            <Select
              allowClear
              placeholder="Agenda"
              style={{ width: '100%' }}
              options={(calendars.data ?? []).map((item) => ({
                value: item.id,
                label: (
                  <span>
                    <span style={{ color: item.cor }}>●</span> {item.nome}
                  </span>
                ),
              }))}
              onChange={(value) => setFilters((old) => ({ ...old, agenda_id: value }))}
            />
          </Col>
          <Col xs={24} md={6}>
            <Select
              allowClear
              placeholder="Agenda do candidato"
              style={{ width: '100%' }}
              options={[
                { value: 'rede', label: 'Rede' },
                { value: 'recurso', label: 'Recurso' },
                { value: 'rua', label: 'Rua' },
              ]}
              onChange={(value) => setFilters((old) => ({ ...old, natureza_candidato: value }))}
            />
          </Col>
          <Col xs={24} md={6}>
            <Select
              allowClear
              placeholder="Frente/Comunidade"
              style={{ width: '100%' }}
              options={[
                { value: 'juventude', label: 'Juventude' },
                { value: 'sindicalista', label: 'Sindicalista' },
                { value: 'cultura', label: 'Cultura' },
                { value: 'engenharia', label: 'Engenharia' },
                { value: 'saude', label: 'Saúde' },
                { value: 'educacao', label: 'Educação' },
                { value: 'dobradas', label: 'Dobradas' },
              ]}
              onChange={(value) => setFilters((old) => ({ ...old, frente_comunidade: value }))}
            />
          </Col>
          <Col xs={24} md={6}>
            <Select
              allowClear
              placeholder="Tipo de agenda"
              style={{ width: '100%' }}
              options={[
                { value: 'fixa_campanha', label: 'Agenda fixa da campanha' },
                { value: 'agenda_aberta', label: 'Agenda aberta' },
                { value: 'agenda_candidato', label: 'Agenda do candidato' },
              ]}
              onChange={(value) => setFilters((old) => ({ ...old, tipo_agenda: value }))}
            />
          </Col>
          <Col xs={24} md={6}>
            <Select
              allowClear
              placeholder="Visibilidade"
              style={{ width: '100%' }}
              options={[
                { value: 'publica', label: 'Pública' },
                { value: 'restrita', label: 'Restrita' },
              ]}
              onChange={(value) => setFilters((old) => ({ ...old, visibilidade: value }))}
            />
          </Col>
          <Col xs={24} md={6}>
            <Select
              allowClear
              placeholder="Território"
              style={{ width: '100%' }}
              options={(territories.data ?? []).map((item) => ({
                value: item.id,
                label: item.nome,
              }))}
              onChange={(value) => setFilters((old) => ({ ...old, territorio_id: value }))}
            />
          </Col>
          <Col xs={24} md={6}>
            <Select
              allowClear
              placeholder="Liderança"
              style={{ width: '100%' }}
              options={(leaderships.data ?? []).map((item) => ({
                value: item.id,
                label: item.apelido_campanha || `Liderança #${item.id}`,
              }))}
              onChange={(value) => setFilters((old) => ({ ...old, lideranca_id: value }))}
            />
          </Col>
          <Col xs={24} md={6}>
            <Select
              allowClear
              placeholder="Tipo"
              style={{ width: '100%' }}
              options={(types.data ?? []).map((item) => ({ value: item.id, label: item.nome }))}
              onChange={(value) => setFilters((old) => ({ ...old, tipo_evento_id: value }))}
            />
          </Col>
          <Col xs={24} md={6}>
            <Select
              allowClear
              placeholder="Status"
              style={{ width: '100%' }}
              options={(statuses.data ?? []).map((item) => ({
                value: item.id,
                label: item.nome,
              }))}
              onChange={(value) => setFilters((old) => ({ ...old, status_evento_id: value }))}
            />
          </Col>
        </Row>
      </Card>
      <Card
        title={
          <Segmented
            value={view}
            onChange={(value) => setView(String(value))}
            options={[
              { value: 'Mês', icon: <CalendarOutlined /> },
              { value: 'Semana', icon: <CalendarOutlined /> },
              { value: 'Lista', icon: <UnorderedListOutlined /> },
            ]}
          />
        }
      >
        {view === 'Mês' && (
          <Calendar
            value={referenceDate}
            onPanelChange={(date) => setReferenceDate(date)}
            onSelect={(date) => setReferenceDate(date)}
            cellRender={(date) => (
              <Space direction="vertical" size={0}>
                {items
                  .filter((item) => dayjs(item.data_inicio).isSame(date, 'day'))
                  .slice(0, 3)
                  .map((item) => (
                    <div key={item.id}>{renderEvent(item)}</div>
                  ))}
              </Space>
            )}
          />
        )}
        {view === 'Semana' && (
          <List
            dataSource={weekItems}
            locale={{ emptyText: 'Nenhum evento nesta semana.' }}
            renderItem={(item) => (
              <List.Item actions={[renderEvent(item)]}>
                <List.Item.Meta
                  title={dayjs(item.data_inicio).format('dddd, DD/MM/YYYY')}
                  description={`${item.local_nome || 'Local a definir'} · ${item.responsavel_nome}`}
                />
              </List.Item>
            )}
          />
        )}
        {view === 'Lista' && (
          <Table
            rowKey="id"
            loading={events.isPending}
            dataSource={items}
            onRow={(item) => ({
              onClick: () => navigate(`/agenda/eventos/${item.id}`),
              style: { cursor: 'pointer' },
            })}
            columns={[
              {
                title: 'Data',
                dataIndex: 'data_inicio',
                render: (value: string) => dayjs(value).format('DD/MM/YYYY HH:mm'),
              },
              { title: 'Evento', dataIndex: 'titulo' },
              {
                title: 'Agenda',
                render: (_, item) => <Tag color={item.agenda_cor}>{item.agenda_nome}</Tag>,
              },
              { title: 'Tipo', dataIndex: 'tipo_evento_nome' },
              { title: 'Território', dataIndex: 'territorio_nome' },
              {
                title: 'Status',
                render: (_, item) => (
                  <Tag color={statusColors[item.status_evento_codigo ?? '']}>
                    {item.status_evento_nome}
                  </Tag>
                ),
              },
            ]}
          />
        )}
      </Card>
      <Modal
        open={modalOpen}
        title="Novo evento"
        okText="Criar evento"
        width={720}
        confirmLoading={creation.isPending}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.validateFields().then((values) => creation.mutate(values))}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="agenda_id" label="Agenda" rules={[{ required: true }]}>
            <Select
              options={(calendars.data ?? [])
                .filter((item) => item.permissoes.includes('criar'))
                .map((item) => ({
                  value: item.id,
                  label: item.nome,
                }))}
            />
          </Form.Item>
          <Form.Item name="titulo" label="Título" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="descricao" label="Descrição">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="tipo_evento_id" label="Tipo">
                <Select
                  options={(types.data ?? []).map((item) => ({
                    value: item.id,
                    label: item.nome,
                  }))}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="status_evento_id" label="Status">
                <Select
                  options={(statuses.data ?? []).map((item) => ({
                    value: item.id,
                    label: item.nome,
                  }))}
                />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="periodo" label="Data e horário" rules={[{ required: true }]}>
            <DatePicker.RangePicker
              format="DD/MM/YYYY HH:mm:ss"
              showTime={{ format: 'HH:mm:ss' }}
              style={{ width: '100%' }}
            />
          </Form.Item>
          <Row gutter={12}>
            <Col span={12}>
              <Form.Item name="local_nome" label="Local">
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="territorio_id" label="Território">
                <RemoteTerritorySelect />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="responsavel_pessoa_id" label="Responsável" rules={[{ required: true }]}>
            <RemotePersonSelect />
          </Form.Item>
        </Form>
      </Modal>
      <CalendarManagementModal open={managementOpen} onClose={() => setManagementOpen(false)} />
    </div>
  );
}
