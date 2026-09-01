import { DeleteOutlined, EditOutlined, FileProtectOutlined, PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  Col,
  DatePicker,
  Descriptions,
  Divider,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
} from 'antd';
import type { UploadFile } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useMemo, useState } from 'react';

import { AttachmentsPanel } from '@/components/arquivos/AttachmentsPanel';
import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import { listAttachmentTypes, uploadAttachment } from '@/modules/arquivos/arquivos-service';
import {
  createContract,
  deleteContract,
  listContracts,
  searchContractPeople,
  updateContract,
} from '@/modules/contratos/contratos-service';
import type {
  CampaignContract,
  ContractInput,
  ContractStatus,
  ContractorType,
  LegalEntityInput,
  PersonOption,
} from '@/modules/contratos/types';
import { normalizeApiError } from '@/services/api/api-error';

const documentCodes = [
  'contrato_rg_frente',
  'contrato_rg_verso',
  'contrato_cnh',
  'contrato_cpf',
  'contrato_comprovante_endereco',
  'contrato_foto',
  'contrato_cartao_cnpj',
  'contrato_social',
];

interface ContractFormValues {
  tipo_contratado: ContractorType;
  pessoa_id?: number;
  pessoa_juridica?: LegalEntityInput;
  funcao_cargo: string;
  valor_parcela: number;
  quantidade_parcelas: 1 | 2 | 3;
  periodo: [Dayjs, Dayjs];
  status: ContractStatus;
  observacoes?: string;
}

interface PendingDocument {
  typeId: number;
  file: File;
}

const money = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });
const statusColors: Record<ContractStatus, string> = {
  rascunho: 'default',
  ativo: 'green',
  encerrado: 'blue',
  cancelado: 'red',
};

export function ContractsPage() {
  const queryClient = useQueryClient();
  const [form] = Form.useForm<ContractFormValues>();
  const [filters, setFilters] = useState<Record<string, string | undefined>>({});
  const [personQuery, setPersonQuery] = useState('');
  const [selected, setSelected] = useState<CampaignContract | null>(null);
  const [editing, setEditing] = useState<CampaignContract | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [documentTypeId, setDocumentTypeId] = useState<number>();
  const [documentFile, setDocumentFile] = useState<UploadFile[]>([]);
  const [pendingDocuments, setPendingDocuments] = useState<PendingDocument[]>([]);

  const contracts = useQuery({
    queryKey: ['contratos', filters],
    queryFn: () => listContracts(filters),
  });
  const people = useQuery({
    queryKey: ['contratos', 'pessoas', personQuery],
    queryFn: () => searchContractPeople(personQuery),
    enabled: personQuery.trim().length >= 2,
  });
  const attachmentTypes = useQuery({
    queryKey: ['arquivos', 'tipos'],
    queryFn: listAttachmentTypes,
  });
  const contractDocumentTypes = useMemo(
    () => (attachmentTypes.data ?? []).filter((item) => documentCodes.includes(item.codigo)),
    [attachmentTypes.data],
  );

  const contractorType = Form.useWatch('tipo_contratado', form);
  const personId = Form.useWatch('pessoa_id', form);
  const amount = Form.useWatch('valor_parcela', form) ?? 0;
  const installments = Form.useWatch('quantidade_parcelas', form) ?? 1;
  const period = Form.useWatch('periodo', form);
  const total = amount * installments;
  const days = period?.[0] && period?.[1] ? period[1].diff(period[0], 'day') : 0;
  const daily = days > 0 ? total / days : 0;
  const selectedPerson = (people.data ?? []).find((item) => item.id === personId);

  const save = useMutation({
    mutationFn: async (values: ContractFormValues) => {
      const payload: ContractInput = {
        tipo_contratado: values.tipo_contratado,
        pessoa_id: values.tipo_contratado === 'pf' ? values.pessoa_id : undefined,
        pessoa_juridica: values.tipo_contratado === 'pj' ? values.pessoa_juridica : undefined,
        funcao_cargo: values.funcao_cargo,
        valor_parcela: values.valor_parcela,
        quantidade_parcelas: values.quantidade_parcelas,
        data_inicio: values.periodo[0].format('YYYY-MM-DD'),
        data_termino: values.periodo[1].format('YYYY-MM-DD'),
        status: values.status,
        observacoes: values.observacoes,
      };
      const contract = editing
        ? await updateContract(editing.id, {
            funcao_cargo: payload.funcao_cargo,
            valor_parcela: payload.valor_parcela,
            quantidade_parcelas: payload.quantidade_parcelas,
            data_inicio: payload.data_inicio,
            data_termino: payload.data_termino,
            status: payload.status,
            observacoes: payload.observacoes,
          })
        : await createContract(payload);
      for (const document of pendingDocuments) {
        await uploadAttachment({
          entity: 'contrato',
          entityId: contract.id,
          typeId: document.typeId,
          file: document.file,
        });
      }
      return contract;
    },
    onSuccess: async (contract) => {
      AppToast.success(editing ? 'Contrato atualizado.' : 'Contrato cadastrado.');
      setFormOpen(false);
      setEditing(null);
      setPendingDocuments([]);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['contratos'] });
      setSelected(contract);
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const remove = useMutation({
    mutationFn: deleteContract,
    onSuccess: async () => {
      AppToast.success('Contrato excluído.');
      await queryClient.invalidateQueries({ queryKey: ['contratos'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const openCreate = () => {
    setEditing(null);
    setPendingDocuments([]);
    form.resetFields();
    form.setFieldsValue({
      tipo_contratado: 'pf',
      quantidade_parcelas: 1,
      status: 'ativo',
    });
    setFormOpen(true);
  };
  const openEdit = (item: CampaignContract) => {
    setEditing(item);
    setPendingDocuments([]);
    setPersonQuery(item.contratado.nome);
    form.setFieldsValue({
      tipo_contratado: item.tipo_contratado,
      pessoa_id: item.pessoa_id ?? undefined,
      pessoa_juridica:
        item.tipo_contratado === 'pj'
          ? {
              razao_social: item.contratado.nome,
              cnpj: item.contratado.documento,
              telefone: item.contratado.telefone ?? undefined,
              cep: item.contratado.cep ?? undefined,
              logradouro: item.contratado.logradouro ?? undefined,
              numero: item.contratado.numero ?? undefined,
              complemento: item.contratado.complemento ?? undefined,
              bairro_texto: item.contratado.bairro ?? undefined,
              codigo_municipio_ibge: item.contratado.codigo_municipio_ibge ?? undefined,
              latitude: item.contratado.latitude ? Number(item.contratado.latitude) : undefined,
              longitude: item.contratado.longitude ? Number(item.contratado.longitude) : undefined,
            }
          : undefined,
      funcao_cargo: item.funcao_cargo,
      valor_parcela: Number(item.valor_parcela),
      quantidade_parcelas: item.quantidade_parcelas,
      periodo: [dayjs(item.data_inicio), dayjs(item.data_termino)],
      status: item.status,
      observacoes: item.observacoes ?? undefined,
    });
    setFormOpen(true);
  };
  const queueDocument = () => {
    const file = documentFile[0]?.originFileObj;
    if (!documentTypeId || !file) {
      AppToast.error('Selecione o tipo e o arquivo.');
      return;
    }
    setPendingDocuments((current) => [...current, { typeId: documentTypeId, file }]);
    setDocumentFile([]);
    setDocumentTypeId(undefined);
  };

  return (
    <div>
      <PageHeader
        title="Contratos de campanha"
        description="Dados contratuais e documentos sensíveis, exclusivos do perfil Tesoureiro."
        breadcrumbs={[{ label: 'Início', to: '/dashboard' }, { label: 'Contratos' }]}
        actions={
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            Novo contrato
          </Button>
        }
      />

      <Card>
        <Space wrap style={{ marginBottom: 16 }}>
          <Input.Search
            allowClear
            placeholder="Nome, CPF, CNPJ ou função"
            onSearch={(q) => setFilters((old) => ({ ...old, q: q || undefined }))}
            style={{ width: 300 }}
          />
          <Select
            allowClear
            placeholder="Tipo"
            style={{ width: 150 }}
            options={[
              { value: 'pf', label: 'Pessoa física' },
              { value: 'pj', label: 'Pessoa jurídica' },
            ]}
            onChange={(value) => setFilters((old) => ({ ...old, tipo_contratado: value }))}
          />
          <Select
            allowClear
            placeholder="Situação"
            style={{ width: 160 }}
            options={Object.keys(statusColors).map((value) => ({ value, label: value }))}
            onChange={(value) => setFilters((old) => ({ ...old, situacao: value }))}
          />
        </Space>
        <Table
          rowKey="id"
          loading={contracts.isLoading}
          dataSource={contracts.data ?? []}
          onRow={(item) => ({ onDoubleClick: () => setSelected(item) })}
          columns={[
            { title: 'Contratado', render: (_, item) => item.contratado.nome },
            { title: 'CPF/CNPJ', render: (_, item) => item.contratado.documento },
            { title: 'Função/Cargo', dataIndex: 'funcao_cargo' },
            {
              title: 'Período',
              render: (_, item) =>
                `${dayjs(item.data_inicio).format('DD/MM/YYYY')} a ${dayjs(item.data_termino).format('DD/MM/YYYY')}`,
            },
            { title: 'Valor total', render: (_, item) => money.format(Number(item.valor_total)) },
            {
              title: 'Situação',
              render: (_, item) => <Tag color={statusColors[item.status]}>{item.status}</Tag>,
            },
            {
              title: 'Ações',
              render: (_, item) => (
                <Space>
                  <Button icon={<FileProtectOutlined />} onClick={() => setSelected(item)} />
                  <Button icon={<EditOutlined />} onClick={() => openEdit(item)} />
                  <Popconfirm
                    title="Excluir este contrato?"
                    onConfirm={() => remove.mutate(item.id)}
                  >
                    <Button danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        open={formOpen}
        width={900}
        title={editing ? 'Editar contrato' : 'Novo contrato'}
        okText="Salvar"
        confirmLoading={save.isPending}
        onCancel={() => setFormOpen(false)}
        onOk={() => form.submit()}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={(values) => save.mutate(values)}>
          <Typography.Title level={5}>Dados do contratado</Typography.Title>
          <Form.Item name="tipo_contratado" label="Tipo de pessoa" rules={[{ required: true }]}>
            <Select
              disabled={Boolean(editing)}
              options={[
                { value: 'pf', label: 'Pessoa física' },
                { value: 'pj', label: 'Pessoa jurídica' },
              ]}
            />
          </Form.Item>
          {contractorType === 'pf' ? (
            <>
              <Form.Item name="pessoa_id" label="Pessoa cadastrada" rules={[{ required: true }]}>
                <Select
                  showSearch
                  filterOption={false}
                  onSearch={setPersonQuery}
                  loading={people.isFetching}
                  disabled={Boolean(editing)}
                  options={(people.data ?? []).map((person) => ({
                    value: person.id,
                    label: `${person.nome} — ${person.cpf}`,
                  }))}
                />
              </Form.Item>
              {selectedPerson ? <PersonSummary person={selectedPerson} /> : null}
            </>
          ) : (
            <LegalEntityFields disabled={Boolean(editing)} />
          )}

          <Divider />
          <Typography.Title level={5}>Dados do Contrato</Typography.Title>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="funcao_cargo" label="Função/Cargo" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item
                name="valor_parcela"
                label="Valor da parcela/contrato"
                rules={[{ required: true }]}
              >
                <InputNumber min={0.01} precision={2} style={{ width: '100%' }} prefix="R$" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="quantidade_parcelas" label="Parcelas" rules={[{ required: true }]}>
                <Select options={[1, 2, 3].map((value) => ({ value, label: value }))} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="periodo" label="Início e término" rules={[{ required: true }]}>
                <DatePicker.RangePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="Valor Total">
                <Input readOnly value={money.format(total)} />
              </Form.Item>
            </Col>
            <Col span={3}>
              <Form.Item label="Dias">
                <Input readOnly value={days > 0 ? days : ''} />
              </Form.Item>
            </Col>
            <Col span={3}>
              <Form.Item label="Diária">
                <Input readOnly value={money.format(daily)} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="status" label="Situação" rules={[{ required: true }]}>
                <Select
                  options={Object.keys(statusColors).map((value) => ({ value, label: value }))}
                />
              </Form.Item>
            </Col>
            <Col span={16}>
              <Form.Item name="observacoes" label="Observações">
                <Input.TextArea rows={2} />
              </Form.Item>
            </Col>
          </Row>

          <Divider />
          <Typography.Title level={5}>Documentos do contratado</Typography.Title>
          <Space.Compact block>
            <Select
              value={documentTypeId}
              onChange={setDocumentTypeId}
              placeholder="Tipo de documento"
              style={{ width: '40%' }}
              options={contractDocumentTypes.map((item) => ({ value: item.id, label: item.nome }))}
            />
            <Upload
              accept="image/png,image/jpeg,image/webp,application/pdf"
              beforeUpload={() => false}
              maxCount={1}
              fileList={documentFile}
              onChange={({ fileList }) => setDocumentFile(fileList)}
            >
              <Button>Selecionar arquivo</Button>
            </Upload>
            <Button onClick={queueDocument}>Adicionar</Button>
          </Space.Compact>
          {pendingDocuments.length > 0 ? (
            <Typography.Paragraph type="secondary" style={{ marginTop: 8 }}>
              {pendingDocuments.length} documento(s) serão enviados ao salvar.
            </Typography.Paragraph>
          ) : null}
        </Form>
      </Modal>

      <Modal
        open={Boolean(selected)}
        width={900}
        title="Detalhes do contrato"
        footer={null}
        onCancel={() => setSelected(null)}
        destroyOnClose
      >
        {selected ? (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="Contratado">{selected.contratado.nome}</Descriptions.Item>
              <Descriptions.Item label="CPF/CNPJ">
                {selected.contratado.documento}
              </Descriptions.Item>
              <Descriptions.Item label="Função">{selected.funcao_cargo}</Descriptions.Item>
              <Descriptions.Item label="Situação">{selected.status}</Descriptions.Item>
              <Descriptions.Item label="Valor total">
                {money.format(Number(selected.valor_total))}
              </Descriptions.Item>
              <Descriptions.Item label="Valor diária">
                {money.format(Number(selected.valor_diaria))}
              </Descriptions.Item>
              <Descriptions.Item label="Dias de trabalho">
                {selected.dias_trabalho}
              </Descriptions.Item>
              <Descriptions.Item label="Telefone">
                {selected.contratado.telefone ?? '—'}
              </Descriptions.Item>
              <Descriptions.Item label="Endereço" span={2}>
                {[
                  selected.contratado.logradouro,
                  selected.contratado.numero,
                  selected.contratado.bairro,
                  selected.contratado.cidade,
                ]
                  .filter(Boolean)
                  .join(', ') || '—'}
              </Descriptions.Item>
            </Descriptions>
            <AttachmentsPanel
              entity="contrato"
              entityId={selected.id}
              canEdit
              allowedTypeCodes={documentCodes}
            />
          </Space>
        ) : null}
      </Modal>
    </div>
  );
}

function PersonSummary({ person }: { person: PersonOption }) {
  return (
    <Descriptions size="small" bordered column={3}>
      <Descriptions.Item label="CPF">{person.cpf}</Descriptions.Item>
      <Descriptions.Item label="RG">{person.rg ?? '—'}</Descriptions.Item>
      <Descriptions.Item label="Nascimento">
        {person.data_nascimento ? dayjs(person.data_nascimento).format('DD/MM/YYYY') : '—'}
      </Descriptions.Item>
      <Descriptions.Item label="Celular">{person.telefone ?? '—'}</Descriptions.Item>
      <Descriptions.Item label="Endereço" span={2}>
        {[person.logradouro, person.numero, person.bairro, person.cidade]
          .filter(Boolean)
          .join(', ') || '—'}
      </Descriptions.Item>
    </Descriptions>
  );
}

function LegalEntityFields({ disabled }: { disabled: boolean }) {
  return (
    <Row gutter={16}>
      <Col span={12}>
        <Form.Item
          name={['pessoa_juridica', 'razao_social']}
          label="Razão social"
          rules={[{ required: true }]}
        >
          <Input disabled={disabled} />
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name={['pessoa_juridica', 'nome_fantasia']} label="Nome fantasia">
          <Input disabled={disabled} />
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name={['pessoa_juridica', 'cnpj']} label="CNPJ" rules={[{ required: true }]}>
          <Input disabled={disabled} />
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name={['pessoa_juridica', 'telefone']} label="Telefone">
          <Input disabled={disabled} />
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name={['pessoa_juridica', 'cep']} label="CEP">
          <Input disabled={disabled} />
        </Form.Item>
      </Col>
      <Col span={8}>
        <Form.Item name={['pessoa_juridica', 'logradouro']} label="Rua/Logradouro">
          <Input disabled={disabled} />
        </Form.Item>
      </Col>
      <Col span={4}>
        <Form.Item name={['pessoa_juridica', 'numero']} label="Número">
          <Input disabled={disabled} />
        </Form.Item>
      </Col>
      <Col span={8}>
        <Form.Item name={['pessoa_juridica', 'complemento']} label="Complemento">
          <Input disabled={disabled} />
        </Form.Item>
      </Col>
      <Col span={8}>
        <Form.Item name={['pessoa_juridica', 'bairro_texto']} label="Bairro">
          <Input disabled={disabled} />
        </Form.Item>
      </Col>
      <Col span={8}>
        <Form.Item
          name={['pessoa_juridica', 'codigo_municipio_ibge']}
          label="Código IBGE da cidade"
        >
          <InputNumber disabled={disabled} style={{ width: '100%' }} />
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name={['pessoa_juridica', 'latitude']} label="Latitude">
          <InputNumber disabled={disabled} style={{ width: '100%' }} />
        </Form.Item>
      </Col>
      <Col span={6}>
        <Form.Item name={['pessoa_juridica', 'longitude']} label="Longitude">
          <InputNumber disabled={disabled} style={{ width: '100%' }} />
        </Form.Item>
      </Col>
    </Row>
  );
}
