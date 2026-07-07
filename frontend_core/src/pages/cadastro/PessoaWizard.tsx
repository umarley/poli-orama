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
} from 'antd';
import type { Dayjs } from 'dayjs';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { ElectoralLocationFields } from '@/components/territorios/ElectoralLocationFields';
import { buscarPessoas, criarPessoa } from '@/modules/cadastro/pessoas-service';
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
  tipo_documento?: TipoDocumento;
  documento?: string;
  tipo_contato?: TipoContato;
  contato?: string;
  cep?: string;
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

const phoneContactTypes = new Set<TipoContato>(['whatsapp', 'celular', 'telefone']);

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

function onlyDigits(value: string): string {
  return value.replace(/\D/g, '');
}

const stepFields: Array<Array<keyof WizardValues>> = [
  ['nome_completo', 'nome_social', 'apelido', 'sexo', 'data_nascimento', 'estado_civil'],
  ['tipo_documento', 'documento', 'tipo_contato', 'contato'],
  ['cep', 'logradouro', 'numero', 'complemento', 'bairro_texto'],
  [
    'tipo_ids',
    'titulo_eleitor',
    'zona_eleitoral_id',
    'secao_eleitoral_id',
    'local_votacao_id',
    'lideranca_superior_id',
    'observacoes',
  ],
];

export function PessoaWizard({
  open,
  tipos,
  liderancas,
  estadosCivis,
  onClose,
  onCreated,
}: PessoaWizardProps) {
  const [form] = Form.useForm<WizardValues>();
  const documentType = Form.useWatch('tipo_documento', form) ?? 'cpf';
  const contactType = Form.useWatch('tipo_contato', form) ?? 'whatsapp';
  const isCpfDocument = documentType === 'cpf';
  const isPhoneContact = phoneContactTypes.has(contactType);
  const [step, setStep] = useState(0);
  const [duplicates, setDuplicates] = useState<BuscaRapidaItem[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const currentDocument = form.getFieldValue('documento');
    if (currentDocument) {
      const nextDocument = isCpfDocument ? formatCpfDocument(currentDocument) : onlyDigits(currentDocument);
      if (nextDocument !== currentDocument) {
        form.setFieldValue('documento', nextDocument);
      }
    }
  }, [documentType, form, isCpfDocument]);

  const close = () => {
    form.resetFields();
    setStep(0);
    setDuplicates([]);
    setError(null);
    onClose();
  };

  const checkDuplicates = async () => {
    const values = form.getFieldsValue();
    const term = values.documento || values.contato || values.nome_completo;
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
    setStep((current) => Math.min(current + 1, 3));
  };

  const submit = async () => {
    const values = await form.validateFields();
    setSaving(true);
    setError(null);
    try {
      const payload: PessoaCreateInput = {
        nome_completo: values.nome_completo,
        nome_social: values.nome_social,
        apelido: values.apelido,
        sexo: values.sexo,
        data_nascimento: values.data_nascimento?.format('YYYY-MM-DD'),
        estado_civil: values.estado_civil,
        observacoes: values.observacoes,
        documentos:
          values.tipo_documento && values.documento
            ? [{ tipo_documento: values.tipo_documento, numero: values.documento }]
            : [],
        contatos:
          values.tipo_contato && values.contato
            ? [{ tipo_contato: values.tipo_contato, valor: values.contato, principal: true }]
            : [],
        enderecos:
          values.cep || values.logradouro || values.bairro_texto
            ? [
                {
                  tipo: 'residencial',
                  principal: true,
                  endereco: {
                    cep: values.cep,
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
      <Form form={form} layout="vertical" requiredMark={false}>
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
          <Row gutter={12}>
            <Col xs={24} md={8}>
              <Form.Item name="tipo_documento" label="Documento" initialValue="cpf">
                <Select
                  options={[
                    { value: 'cpf', label: 'CPF' },
                    { value: 'rg', label: 'RG' },
                    { value: 'titulo_eleitor', label: 'Título eleitoral' },
                    { value: 'outro', label: 'Outro' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={16}>
              <Form.Item
                name="documento"
                label="Número"
                normalize={(value: string) => (isCpfDocument ? formatCpfDocument(value) : value)}
              >
                <Input
                  inputMode={isCpfDocument ? 'numeric' : undefined}
                  maxLength={isCpfDocument ? 14 : undefined}
                  placeholder={isCpfDocument ? '###.###.###-##' : undefined}
                  onBlur={checkDuplicates}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="tipo_contato" label="Canal" initialValue="whatsapp">
                <Select
                  options={[
                    { value: 'whatsapp', label: 'WhatsApp' },
                    { value: 'celular', label: 'Celular' },
                    { value: 'telefone', label: 'Telefone' },
                    { value: 'email', label: 'E-mail' },
                  ]}
                />
              </Form.Item>
            </Col>
            <Col xs={24} md={16}>
              <Form.Item
                name="contato"
                label="Contato"
                normalize={(value: string) =>
                  isPhoneContact ? formatPhoneContact(value) : value
                }
                rules={[
                  {
                    validator: (_, value?: string) => {
                      if (!value) return Promise.resolve();
                      if (contactType === 'email') {
                        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
                          ? Promise.resolve()
                          : Promise.reject(new Error('Informe um e-mail válido.'));
                      }
                      const digitCount = value.replace(/\D/g, '').length;
                      return digitCount === 10 || digitCount === 11
                        ? Promise.resolve()
                        : Promise.reject(
                            new Error('Informe um telefone com DDD e 10 ou 11 dígitos.'),
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
          </Row>
        </div>
        <div hidden={step !== 2}>
          <Row gutter={12}>
            <Col xs={24} md={8}>
              <Form.Item name="cep" label="CEP">
                <Input />
              </Form.Item>
            </Col>
            <Col xs={24} md={16}>
              <Form.Item name="logradouro" label="Logradouro">
                <Input />
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
                label: item.apelido_campanha || `Liderança #${item.id}`,
              }))}
            />
          </Form.Item>
          <Row gutter={12}>
            <Col xs={24} md={12}>
              <Form.Item name="titulo_eleitor" label="Título eleitoral">
                <Input />
              </Form.Item>
            </Col>
          </Row>
          <ElectoralLocationFields />
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
