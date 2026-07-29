import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Col,
  DatePicker,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Steps,
  Switch,
  Typography,
} from 'antd';
import type { Dayjs } from 'dayjs';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { ElectoralLocationFields } from '@/components/territorios/ElectoralLocationFields';
import { buscarPessoas, criarPessoa } from '@/modules/cadastro/pessoas-service';
import { listarEstados, listarMunicipios } from '@/modules/territorios/territorios-service';
import type {
  BuscaRapidaItem,
  EstadoCivil,
  Lideranca,
  PessoaCreateInput,
  PessoaTipo,
  TipoContato,
  TipoDocumento,
} from '@/modules/cadastro/types';
import { normalizeApiError } from '@/services/api/api-error';

interface WizardValues {
  nome_completo: string;
  nome_social?: string;
  apelido?: string;
  sexo?: 'M' | 'F' | 'O' | 'N';
  data_nascimento?: Dayjs;
  estado_civil?: number;
  documentos?: Array<{
    tipo_documento?: TipoDocumento;
    numero?: string;
  }>;
  contatos?: Array<{
    tipo_contato?: TipoContato;
    valor?: string;
  }>;
  cep?: string;
  codigo_uf_ibge?: number;
  codigo_municipio_ibge?: number;
  codigo_uf_eleitoral_ibge?: number;
  codigo_municipio_eleitoral_ibge?: number;
  logradouro?: string;
  numero?: string;
  complemento?: string;
  bairro_texto?: string;
  tipo_ids?: number[];
  titulo_eleitor?: string;
  zona_eleitoral_id?: number;
  secao_eleitoral_id?: number;
  local_votacao_id?: number;
  lideranca_superior_id?: number;
  voluntario?: boolean;
  observacoes?: string;
}

interface PessoaWizardProps {
  open: boolean;
  tipos: PessoaTipo[];
  liderancas: Lideranca[];
  estadosCivis: EstadoCivil[];
  onClose: () => void;
  onCreated: (id: number) => void;
}

interface ViaCepResponse {
  cep?: string;
  logradouro?: string;
  complemento?: string;
  bairro?: string;
  localidade?: string;
  uf?: string;
  ibge?: string;
  erro?: boolean;
}

const phoneContactTypes = new Set<TipoContato>(['whatsapp', 'celular', 'telefone']);

const documentTypeOptions: Array<{ value: TipoDocumento; label: string }> = [
  { value: 'cpf', label: 'CPF' },
  { value: 'rg', label: 'RG' },
  { value: 'titulo_eleitor', label: 'Título eleitoral' },
  { value: 'cnh', label: 'CNH' },
  { value: 'passaporte', label: 'Passaporte' },
  { value: 'outro', label: 'Outro' },
];

const contactTypeOptions: Array<{ value: TipoContato; label: string }> = [
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'celular', label: 'Celular' },
  { value: 'telefone', label: 'Telefone' },
  { value: 'email', label: 'E-mail' },
  { value: 'outro', label: 'Outro' },
];

function formatPhoneContact(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 11);
  if (!digits) return '';
  if (digits.length <= 2) return `(${digits}`;

  const areaCode = digits.slice(0, 2);
  const number = digits.slice(2);
  if (number.length <= 4) return `(${areaCode}) ${number}`;
  if (number.length <= 8) {
    return `(${areaCode}) ${number.slice(0, 4)}-${number.slice(4)}`;
  }
  return `(${areaCode}) ${number.slice(0, 5)}-${number.slice(5)}`;
}

function formatCpfDocument(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 11);
  if (digits.length <= 3) return digits;
  if (digits.length <= 6) return `${digits.slice(0, 3)}.${digits.slice(3)}`;
  if (digits.length <= 9) {
    return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6)}`;
  }
  return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`;
}

function formatCep(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 8);
  if (digits.length <= 5) return digits;
  return `${digits.slice(0, 5)}-${digits.slice(5)}`;
}

const stepFields: Array<Array<keyof WizardValues>> = [
  ['nome_completo', 'nome_social', 'apelido', 'sexo', 'data_nascimento', 'estado_civil'],
  ['documentos', 'contatos'],
  [
    'cep',
    'codigo_uf_ibge',
    'codigo_municipio_ibge',
    'logradouro',
    'numero',
    'complemento',
    'bairro_texto',
  ],
  [
    'tipo_ids',
    'titulo_eleitor',
    'codigo_uf_eleitoral_ibge',
    'codigo_municipio_eleitoral_ibge',
    'zona_eleitoral_id',
    'secao_eleitoral_id',
    'local_votacao_id',
    'lideranca_superior_id',
    'observacoes',
  ],
];

function hasDuplicateValues(values: Array<string | undefined>): boolean {
  const selectedValues = values.filter(Boolean);
  return selectedValues.length !== new Set(selectedValues).size;
}

function firstAvailableDocumentType(selectedTypes: TipoDocumento[]): TipoDocumento {
  return (
    documentTypeOptions.find((option) => !selectedTypes.includes(option.value))?.value ?? 'outro'
  );
}

function firstAvailableContactType(selectedTypes: TipoContato[]): TipoContato {
  return (
    contactTypeOptions.find((option) => !selectedTypes.includes(option.value))?.value ?? 'outro'
  );
}

export function PessoaWizard({
  open,
  tipos,
  liderancas,
  estadosCivis,
  onClose,
  onCreated,
}: PessoaWizardProps) {
  const [form] = Form.useForm<WizardValues>();
  const selectedStateCode = Form.useWatch('codigo_uf_ibge', form);
  const selectedElectoralStateCode = Form.useWatch('codigo_uf_eleitoral_ibge', form);
  const selectedElectoralCityCode = Form.useWatch('codigo_municipio_eleitoral_ibge', form);
  const [step, setStep] = useState(0);
  const [duplicates, setDuplicates] = useState<BuscaRapidaItem[]>([]);
  const [saving, setSaving] = useState(false);
  const [addressLookupLoading, setAddressLookupLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const statesQuery = useQuery({
    queryKey: ['global', 'estados'],
    queryFn: listarEstados,
  });
  const citiesQuery = useQuery({
    queryKey: ['global', 'municipios', selectedStateCode],
    queryFn: () => listarMunicipios(selectedStateCode),
    enabled: Boolean(selectedStateCode),
  });
  const electoralCitiesQuery = useQuery({
    queryKey: ['global', 'municipios', selectedElectoralStateCode],
    queryFn: () => listarMunicipios(selectedElectoralStateCode),
    enabled: Boolean(selectedElectoralStateCode),
  });

  useEffect(() => {
    if (open) {
      form.setFieldsValue({
        documentos: [{ tipo_documento: 'cpf' }],
        contatos: [{ tipo_contato: 'whatsapp' }],
      });
    }
  }, [form, open]);

  const close = () => {
    form.resetFields();
    setStep(0);
    setDuplicates([]);
    setError(null);
    onClose();
  };

  const lookupAddressByCep = async () => {
    const cep = form.getFieldValue('cep');
    const cepDigits = typeof cep === 'string' ? cep.replace(/\D/g, '') : '';
    if (!cepDigits) return;

    const formattedCep = formatCep(cepDigits);
    form.setFieldValue('cep', formattedCep);

    if (cepDigits.length !== 8) {
      form.setFields([{ name: 'cep', errors: ['Informe um CEP com 8 dígitos.'] }]);
      return;
    }

    setAddressLookupLoading(true);
    form.setFields([{ name: 'cep', errors: [] }]);
    try {
      const response = await fetch(`https://viacep.com.br/ws/${cepDigits}/json/`);
      if (!response.ok) {
        throw new Error('Falha ao consultar o CEP.');
      }

      const address = (await response.json()) as ViaCepResponse;
      if (address.erro) {
        form.setFields([{ name: 'cep', errors: ['CEP não encontrado.'] }]);
        return;
      }

      const state = statesQuery.data?.find((item) => item.uf === address.uf);
      const cityCode = address.ibge ? Number(address.ibge) : undefined;
      form.setFieldsValue({
        cep: address.cep ? formatCep(address.cep) : formattedCep,
        codigo_uf_ibge: state?.codigo_ibge,
        codigo_municipio_ibge: Number.isFinite(cityCode) ? cityCode : undefined,
        logradouro: address.logradouro || form.getFieldValue('logradouro'),
        complemento: address.complemento || form.getFieldValue('complemento'),
        bairro_texto: address.bairro || form.getFieldValue('bairro_texto'),
      });
    } catch {
      form.setFields([{ name: 'cep', errors: ['Não foi possível consultar o CEP agora.'] }]);
    } finally {
      setAddressLookupLoading(false);
    }
  };

  const checkDuplicates = async () => {
    const values = form.getFieldsValue();
    const term =
      values.documentos?.find((document) => document?.numero?.trim())?.numero ||
      values.contatos?.find((contact) => contact?.valor?.trim())?.valor ||
      values.nome_completo;
    if (!term || term.trim().length < 2) return;
    try {
      setDuplicates(await buscarPessoas(term.trim()));
    } catch {
      setDuplicates([]);
    }
  };

  const next = async () => {
    await form.validateFields(stepFields[step]);
    if (step <= 1) await checkDuplicates();
    if (step === 2) {
      form.setFieldsValue({
        codigo_uf_eleitoral_ibge: form.getFieldValue('codigo_uf_ibge'),
        codigo_municipio_eleitoral_ibge: form.getFieldValue('codigo_municipio_ibge'),
        zona_eleitoral_id: undefined,
        local_votacao_id: undefined,
        secao_eleitoral_id: undefined,
      });
    }
    setStep((current) => Math.min(current + 1, 3));
  };

  const submit = async () => {
    const values = await form.validateFields();
    setSaving(true);
    setError(null);
    try {
      const documentos = (values.documentos ?? [])
        .filter((document) => document.tipo_documento && document.numero?.trim())
        .map((document) => ({
          tipo_documento: document.tipo_documento as TipoDocumento,
          numero: document.numero?.trim() ?? '',
        }));
      const contatos = (values.contatos ?? [])
        .filter((contact) => contact.tipo_contato && contact.valor?.trim())
        .map((contact) => ({
          tipo_contato: contact.tipo_contato as TipoContato,
          valor: contact.valor?.trim() ?? '',
          principal: true,
        }));
      const payload: PessoaCreateInput = {
        nome_completo: values.nome_completo,
        nome_social: values.nome_social,
        apelido: values.apelido,
        sexo: values.sexo,
        data_nascimento: values.data_nascimento?.format('YYYY-MM-DD'),
        estado_civil: values.estado_civil,
        observacoes: values.observacoes,
        documentos,
        contatos,
        enderecos:
          values.cep || values.codigo_municipio_ibge || values.logradouro || values.bairro_texto
            ? [
                {
                  tipo: 'residencial',
                  principal: true,
                  endereco: {
                    cep: values.cep,
                    codigo_municipio_ibge: values.codigo_municipio_ibge,
                    logradouro: values.logradouro,
                    numero: values.numero,
                    complemento: values.complemento,
                    bairro_texto: values.bairro_texto,
                  },
                },
              ]
            : [],
        redes_sociais: [],
        tipo_ids: values.tipo_ids ?? [],
        lideranca_superior_id: values.lideranca_superior_id,
        papel_subordinado: 'liderado',
      };
      if (
        values.titulo_eleitor ||
        values.zona_eleitoral_id ||
        values.secao_eleitoral_id ||
        values.local_votacao_id
      ) {
        payload.eleitor = {
          titulo_eleitor: values.titulo_eleitor,
          zona_eleitoral_id: values.zona_eleitoral_id,
          secao_eleitoral_id: values.secao_eleitoral_id,
          local_votacao_id: values.local_votacao_id,
          codigo_municipio_ibge: values.codigo_municipio_eleitoral_ibge,
          situacao_titulo: 'regular',
        };
      }
      const person = await criarPessoa(payload);
      close();
      onCreated(person.id);
    } catch (reason) {
      setError(normalizeApiError(reason).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      width={760}
      title="Nova pessoa"
      onCancel={close}
      destroyOnClose
      footer={[
        <Button key="cancel" onClick={close}>
          Cancelar
        </Button>,
        step > 0 ? (
          <Button key="back" onClick={() => setStep((current) => current - 1)}>
            Voltar
          </Button>
        ) : null,
        step < 3 ? (
          <Button key="next" type="primary" onClick={next}>
            Continuar
          </Button>
        ) : (
          <Button key="save" type="primary" loading={saving} onClick={submit}>
            Salvar cadastro
          </Button>
        ),
      ]}
    >
      <Steps
        size="small"
        current={step}
        items={[
          { title: 'Dados básicos' },
          { title: 'Contato' },
          { title: 'Endereço' },
          { title: 'Classificação' },
        ]}
        style={{ marginBlock: 20 }}
      />
      {error ? <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} /> : null}
      {duplicates.length > 0 ? (
        <Alert
          type="warning"
          showIcon
          message="Possíveis cadastros duplicados"
          description={
            <div>
              Confira antes de continuar:{' '}
              {duplicates.map((item, index) => (
                <span key={item.id}>
                  {index > 0 ? ', ' : ''}
                  <Link to={`/cadastro/pessoas/${item.id}`} target="_blank">
                    {item.nome_completo}
                  </Link>
                </span>
              ))}
            </div>
          }
          style={{ marginBottom: 16 }}
        />
      ) : null}
      <Form
        form={form}
        layout="vertical"
        requiredMark={false}
        initialValues={{
          documentos: [{ tipo_documento: 'cpf' }],
          contatos: [{ tipo_contato: 'whatsapp' }],
        }}
      >
        <div hidden={step !== 0}>
          <Form.Item
            name="nome_completo"
            label="Nome completo"
            rules={[{ required: true, message: 'Informe o nome completo.' }]}
          >
            <Input autoFocus placeholder="Nome da pessoa" />
          </Form.Item>
          <Row gutter={12}>
            <Col xs={24} md={12}>
              <Form.Item name="nome_social" label="Nome social">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="apelido" label="Apelido">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="data_nascimento" label="Nascimento">
                <DatePicker
                  format={{ format: 'DD/MM/YYYY', type: 'mask' }}
                  placeholder="DD/MM/AAAA"
                  style={{ width: '100%' }}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="sexo" label="Sexo">
                <Select
                  allowClear
                  options={[
                    { value: 'F', label: 'Feminino' },
                    { value: 'M', label: 'Masculino' },
                    { value: 'O', label: 'Outro' },
                    { value: 'N', label: 'Não informar' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="estado_civil" label="Estado civil">
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  placeholder="Selecione"
                  options={estadosCivis.map((item) => ({
                    value: item.id,
                    label: item.nome,
                  }))}
                />
              </Form.Item>
            </Col>
          </Row>
        </div>
        <div hidden={step !== 1}>
          <Form.List
            name="documentos"
            rules={[
              {
                validator: async (_, documents?: WizardValues['documentos']) => {
                  if (
                    hasDuplicateValues(
                      (documents ?? []).map((document) => document?.tipo_documento),
                    )
                  ) {
                    throw new Error('Informe apenas um documento de cada tipo.');
                  }
                },
              },
            ]}
          >
            {(fields, { add, remove }, { errors }) => {
              const documents = form.getFieldValue('documentos') ?? [];
              const selectedTypes = documents
                .map((document?: { tipo_documento?: TipoDocumento }) => document?.tipo_documento)
                .filter(Boolean) as TipoDocumento[];

              return (
                <>
                  <Typography.Title level={5}>Documento</Typography.Title>
                  {fields.map((field) => {
                    const currentType = form.getFieldValue([
                      'documentos',
                      field.name,
                      'tipo_documento',
                    ]) as TipoDocumento | undefined;
                    const isCpfDocument = currentType === 'cpf';

                    return (
                      <Row gutter={12} key={field.key} align="top">
                        <Col xs={24} md={8}>
                          <Form.Item
                            {...field}
                            name={[field.name, 'tipo_documento']}
                            label={field.name === 0 ? 'Tipo' : ' '}
                            rules={[{ required: true, message: 'Selecione o tipo.' }]}
                          >
                            <Select
                              options={documentTypeOptions.map((option) => ({
                                ...option,
                                disabled:
                                  selectedTypes.includes(option.value) &&
                                  option.value !== currentType,
                              }))}
                            />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={14}>
                          <Form.Item
                            name={[field.name, 'numero']}
                            label={field.name === 0 ? 'Número' : ' '}
                            normalize={(value: string) =>
                              isCpfDocument ? formatCpfDocument(value) : value
                            }
                          >
                            <Input
                              inputMode={isCpfDocument ? 'numeric' : undefined}
                              maxLength={isCpfDocument ? 14 : undefined}
                              placeholder={isCpfDocument ? '###.###.###-##' : undefined}
                              onBlur={checkDuplicates}
                            />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={2}>
                          <Form.Item label={field.name === 0 ? ' ' : undefined}>
                            <Button
                              aria-label="Remover documento"
                              disabled={fields.length === 1}
                              icon={<DeleteOutlined />}
                              onClick={() => remove(field.name)}
                            />
                          </Form.Item>
                        </Col>
                      </Row>
                    );
                  })}
                  <Form.ErrorList errors={errors} />
                  <Button
                    type="dashed"
                    icon={<PlusOutlined />}
                    disabled={fields.length >= documentTypeOptions.length}
                    onClick={() =>
                      add({ tipo_documento: firstAvailableDocumentType(selectedTypes) })
                    }
                  >
                    Adicionar documento
                  </Button>
                </>
              );
            }}
          </Form.List>

          <Form.List
            name="contatos"
            rules={[
              {
                validator: async (_, contacts?: WizardValues['contatos']) => {
                  if (
                    hasDuplicateValues((contacts ?? []).map((contact) => contact?.tipo_contato))
                  ) {
                    throw new Error('Informe apenas um contato de cada canal.');
                  }
                },
              },
            ]}
          >
            {(fields, { add, remove }, { errors }) => {
              const contacts = form.getFieldValue('contatos') ?? [];
              const selectedTypes = contacts
                .map((contact?: { tipo_contato?: TipoContato }) => contact?.tipo_contato)
                .filter(Boolean) as TipoContato[];

              return (
                <>
                  <Typography.Title level={5} style={{ marginTop: 24 }}>
                    Canal
                  </Typography.Title>
                  {fields.map((field) => {
                    const currentType = form.getFieldValue([
                      'contatos',
                      field.name,
                      'tipo_contato',
                    ]) as TipoContato | undefined;
                    const isPhoneContact = currentType ? phoneContactTypes.has(currentType) : true;

                    return (
                      <Row gutter={12} key={field.key} align="top">
                        <Col xs={24} md={8}>
                          <Form.Item
                            {...field}
                            name={[field.name, 'tipo_contato']}
                            label={field.name === 0 ? 'Canal' : ' '}
                            rules={[{ required: true, message: 'Selecione o canal.' }]}
                          >
                            <Select
                              options={contactTypeOptions.map((option) => ({
                                ...option,
                                disabled:
                                  selectedTypes.includes(option.value) &&
                                  option.value !== currentType,
                              }))}
                            />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={14}>
                          <Form.Item
                            name={[field.name, 'valor']}
                            label={field.name === 0 ? 'Contato' : ' '}
                            normalize={(value: string) =>
                              isPhoneContact ? formatPhoneContact(value) : value
                            }
                            rules={[
                              {
                                validator: (_, value?: string) => {
                                  if (!value) return Promise.resolve();
                                  if (currentType === 'email') {
                                    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
                                      ? Promise.resolve()
                                      : Promise.reject(new Error('Informe um e-mail válido.'));
                                  }
                                  if (!isPhoneContact) return Promise.resolve();
                                  const digitCount = value.replace(/\D/g, '').length;
                                  return digitCount === 10 || digitCount === 11
                                    ? Promise.resolve()
                                    : Promise.reject(
                                        new Error(
                                          'Informe um telefone com DDD e 10 ou 11 dígitos.',
                                        ),
                                      );
                                },
                              },
                            ]}
                          >
                            <Input
                              inputMode={isPhoneContact ? 'tel' : 'email'}
                              maxLength={isPhoneContact ? 15 : undefined}
                              placeholder={isPhoneContact ? '(##) #####-####' : 'nome@exemplo.com'}
                              onBlur={checkDuplicates}
                            />
                          </Form.Item>
                        </Col>
                        <Col xs={24} md={2}>
                          <Form.Item label={field.name === 0 ? ' ' : undefined}>
                            <Button
                              aria-label="Remover contato"
                              disabled={fields.length === 1}
                              icon={<DeleteOutlined />}
                              onClick={() => remove(field.name)}
                            />
                          </Form.Item>
                        </Col>
                      </Row>
                    );
                  })}
                  <Form.ErrorList errors={errors} />
                  <Button
                    type="dashed"
                    icon={<PlusOutlined />}
                    disabled={fields.length >= contactTypeOptions.length}
                    onClick={() => add({ tipo_contato: firstAvailableContactType(selectedTypes) })}
                  >
                    Adicionar contato
                  </Button>
                </>
              );
            }}
          </Form.List>
        </div>
        <div hidden={step !== 2}>
          <Row gutter={12}>
            <Col xs={24} md={8}>
              <Form.Item name="cep" label="CEP">
                <Input
                  inputMode="numeric"
                  maxLength={9}
                  placeholder="#####-###"
                  onBlur={lookupAddressByCep}
                  onPressEnter={lookupAddressByCep}
                  disabled={addressLookupLoading}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={16}>
              <Form.Item name="logradouro" label="Logradouro">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="codigo_uf_ibge" label="Estado">
                <Select
                  allowClear
                  showSearch
                  loading={statesQuery.isLoading}
                  optionFilterProp="label"
                  placeholder="Selecione"
                  options={(statesQuery.data ?? []).map((item) => ({
                    value: item.codigo_ibge,
                    label: `${item.uf} - ${item.nome}`,
                  }))}
                  onChange={() => {
                    form.setFieldValue('codigo_municipio_ibge', undefined);
                  }}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={16}>
              <Form.Item name="codigo_municipio_ibge" label="Município">
                <Select
                  allowClear
                  showSearch
                  disabled={!selectedStateCode}
                  loading={citiesQuery.isFetching}
                  optionFilterProp="label"
                  placeholder={selectedStateCode ? 'Selecione' : 'Selecione o estado'}
                  options={(citiesQuery.data ?? []).map((item) => ({
                    value: item.codigo_ibge,
                    label: item.nome,
                  }))}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={6}>
              <Form.Item name="numero" label="Número">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={9}>
              <Form.Item name="complemento" label="Complemento">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={9}>
              <Form.Item name="bairro_texto" label="Bairro">
                <Input />
              </Form.Item>
            </Col>
          </Row>
        </div>
        <div hidden={step !== 3}>
          <Form.Item name="tipo_ids" label="Tipos da pessoa">
            <Select
              mode="multiple"
              placeholder="Eleitor, apoiador, voluntário..."
              options={tipos.map((item) => ({ value: item.id, label: item.nome }))}
            />
          </Form.Item>
          <Form.Item name="lideranca_superior_id" label="Liderança responsável">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              placeholder="Selecione ou deixe pendente"
              options={liderancas.map((item) => ({
                value: item.id,
                label: item.pessoa_nome_completo || `Liderança #${item.id}`,
              }))}
            />
          </Form.Item>
          <Row gutter={12}>
            <Col xs={24} md={12}>
              <Form.Item name="titulo_eleitor" label="Título eleitoral">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="codigo_uf_eleitoral_ibge" label="Estado">
                <Select
                  allowClear
                  showSearch
                  loading={statesQuery.isLoading}
                  optionFilterProp="label"
                  placeholder="Selecione"
                  options={(statesQuery.data ?? []).map((item) => ({
                    value: item.codigo_ibge,
                    label: `${item.uf} - ${item.nome}`,
                  }))}
                  onChange={() => {
                    form.setFieldsValue({
                      codigo_municipio_eleitoral_ibge: undefined,
                      zona_eleitoral_id: undefined,
                      local_votacao_id: undefined,
                      secao_eleitoral_id: undefined,
                    });
                  }}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="codigo_municipio_eleitoral_ibge" label="Município">
                <Select
                  allowClear
                  showSearch
                  disabled={!selectedElectoralStateCode}
                  loading={electoralCitiesQuery.isFetching}
                  optionFilterProp="label"
                  placeholder={selectedElectoralStateCode ? 'Selecione' : 'Selecione o estado'}
                  options={(electoralCitiesQuery.data ?? []).map((item) => ({
                    value: item.codigo_ibge,
                    label: item.nome,
                  }))}
                  onChange={() => {
                    form.setFieldsValue({
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
            codigoMunicipioIbge={selectedElectoralCityCode}
            requireMunicipality
          />
          <Form.Item name="observacoes" label="Observações">
            <Input.TextArea rows={3} />
          </Form.Item>
          <Form.Item name="voluntario" label="Disponível para voluntariado" valuePropName="checked">
            <Switch />
          </Form.Item>
        </div>
      </Form>
    </Modal>
  );
}
