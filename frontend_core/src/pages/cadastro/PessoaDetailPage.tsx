import {
  ArrowLeftOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  PrinterOutlined,
} from '@ant-design/icons';
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  Modal,
  Popconfirm,
  Row,
  Col,
  Select,
  Space,
  Spin,
  Switch,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { CircleMarker, MapContainer, TileLayer, useMap, useMapEvents } from 'react-leaflet';
import { useNavigate, useParams } from 'react-router-dom';

import 'leaflet/dist/leaflet.css';

import { AttachmentsPanel } from '@/components/arquivos/AttachmentsPanel';
import { PersonInteractionsPanel } from '@/components/comunicacao/PersonInteractionsPanel';
import { AppToast } from '@/components/feedback/AppToast';
import { RemotePersonSelect } from '@/components/forms/RemotePersonSelect';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  ElectoralLocationFields,
  ElectoralSectionField,
} from '@/components/territorios/ElectoralLocationFields';
import {
  atualizarContato,
  atualizarDocumento,
  atualizarEndereco,
  atualizarPessoa,
  atualizarRedeSocial,
  calcularCompletudePessoa,
  criarContato,
  criarDocumento,
  criarIndicacao,
  criarRedeSocial,
  definirEleitor,
  listarEstadosCivis,
  listarReligioes,
  listarTags,
  listarTiposPessoa,
  obterPessoa,
  substituirTiposPessoa,
} from '@/modules/cadastro/pessoas-service';
import { generatePersonRegistrationPdf } from '@/modules/cadastro/person-registration-pdf';
import { getAttachmentBlob, listAttachments } from '@/modules/arquivos/arquivos-service';
import { listarInteracoesPessoa } from '@/modules/comunicacao/comunicacao-service';
import type {
  PessoaContato,
  PessoaDocumento,
  PessoaEndereco,
  PessoaRedeSocial,
  RedeSocial,
  TipoContato,
  TipoDocumento,
} from '@/modules/cadastro/types';
import {
  listarEstados,
  listarLocaisVotacao,
  listarMunicipios,
  listarTerritorios,
  listarTerritoriosPessoa,
  removerVinculoPessoaTerritorio,
  listarSecoes,
  listarZonas,
  vincularPessoaTerritorio,
} from '@/modules/territorios/territorios-service';
import type { VinculoPessoaTerritorio } from '@/modules/territorios/types';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';

type Editor =
  | { type: 'person' }
  | { type: 'types' }
  | { type: 'document'; item: PessoaDocumento }
  | { type: 'new-document' }
  | { type: 'contact'; item: PessoaContato }
  | { type: 'new-contact' }
  | { type: 'social'; item: PessoaRedeSocial }
  | { type: 'new-social' }
  | { type: 'voter' }
  | { type: 'address'; item: PessoaEndereco };

type EditValues = Record<string, string | number | number[] | boolean | null | undefined>;
interface TerritoryLinkValues {
  territorio_id: number;
  vinculo: VinculoPessoaTerritorio;
}

interface IndicationValues {
  pessoa_indicada_id: number;
  origem?: string;
  contexto?: string;
  data_indicacao: string;
}

const territoryLinkOptions: Array<{ value: VinculoPessoaTerritorio; label: string }> = [
  { value: 'moradia', label: 'Moradia' },
  { value: 'atuacao', label: 'Atuação' },
  { value: 'votacao', label: 'Votação' },
  { value: 'responsabilidade', label: 'Responsabilidade' },
];
const socialNetworkOptions: Array<{ value: RedeSocial; label: string }> = [
  { value: 'instagram', label: 'Instagram' },
  { value: 'facebook', label: 'Facebook' },
  { value: 'tiktok', label: 'TikTok' },
  { value: 'x', label: 'X' },
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'youtube', label: 'YouTube' },
  { value: 'outro', label: 'Outra' },
];
const sexOptions = [
  { value: 'F', label: 'Feminino' },
  { value: 'M', label: 'Masculino' },
  { value: 'O', label: 'Outro' },
  { value: 'N', label: 'Prefere não informar' },
];
interface ViaCepResponse {
  cep?: string;
  logradouro?: string;
  complemento?: string;
  bairro?: string;
  uf?: string;
  ibge?: string;
  erro?: boolean;
}

interface AddressLocationPickerProps {
  latitude?: number | null;
  longitude?: number | null;
  center: [number, number];
  onChange: (latitude: number, longitude: number) => void;
}

function AddressMapEvents({ onChange }: Pick<AddressLocationPickerProps, 'onChange'>) {
  useMapEvents({
    click: (event) => onChange(event.latlng.lat, event.latlng.lng),
  });
  return null;
}

function AddressMapCenter({ center }: Pick<AddressLocationPickerProps, 'center'>) {
  const map = useMap();
  const [latitude, longitude] = center;
  useEffect(() => {
    map.setView([latitude, longitude], map.getZoom());
    const timer = window.setTimeout(() => map.invalidateSize(), 0);
    return () => window.clearTimeout(timer);
  }, [latitude, longitude, map]);
  return null;
}

function AddressLocationPicker({
  latitude,
  longitude,
  center,
  onChange,
}: AddressLocationPickerProps) {
  const selectedPosition =
    latitude != null && longitude != null ? ([latitude, longitude] as [number, number]) : null;

  return (
    <MapContainer
      center={selectedPosition ?? center}
      zoom={selectedPosition ? 17 : 13}
      style={{ height: 320, width: '100%', borderRadius: 8 }}
      scrollWheelZoom
    >
      <AddressMapCenter center={selectedPosition ?? center} />
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <AddressMapEvents onChange={onChange} />
      {selectedPosition ? (
        <CircleMarker
          center={selectedPosition}
          radius={9}
          pathOptions={{ color: '#fff', fillColor: '#1677ff', fillOpacity: 1, weight: 3 }}
        />
      ) : null}
    </MapContainer>
  );
}

const documentTypeOptions: Array<{ value: TipoDocumento; label: string }> = [
  { value: 'cpf', label: 'CPF' },
  { value: 'rg', label: 'RG' },
  { value: 'titulo_eleitor', label: 'Título eleitoral' },
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

function formatDate(value: string | null): string {
  if (!value) return '—';
  const [year, month, day] = value.split('-');
  return year && month && day ? `${day}/${month}/${year}` : value;
}

function formatDateTime(value: string | null): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');

  return `${day}/${month}/${year} ${hours}:${minutes}:${seconds}`;
}

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

function formatCep(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 8);
  if (digits.length <= 5) return digits;
  return `${digits.slice(0, 5)}-${digits.slice(5)}`;
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

function isValidCpfDocument(value: string): boolean {
  const digits = value.replace(/\D/g, '');
  if (digits.length !== 11 || digits === digits[0]?.repeat(11)) return false;

  for (const size of [9, 10]) {
    const total = digits
      .slice(0, size)
      .split('')
      .reduce((sum, digit, index) => sum + Number(digit) * (size + 1 - index), 0);
    const checkDigit = (total * 10) % 11;
    const normalizedCheckDigit = checkDigit === 10 ? 0 : checkDigit;
    if (normalizedCheckDigit !== Number(digits[size])) return false;
  }

  return true;
}

function formatDocumentValue(type: TipoDocumento, value: string): string {
  return type === 'cpf' ? formatCpfDocument(value) : value;
}

function formatFullAddress(address: PessoaEndereco['endereco'], locationLabel?: string): string {
  const street = [address.logradouro, address.numero].filter(Boolean).join(', ');
  const parts = [
    street,
    address.complemento,
    address.bairro_texto,
    locationLabel,
    address.cep ? `CEP ${formatCep(address.cep)}` : null,
  ];

  return parts.filter(Boolean).join(' - ') || 'Endereço não informado';
}

function formatContactValue(type: TipoContato, value: string): string {
  if (!phoneContactTypes.has(type)) return value;
  const digits = value.replace(/\D/g, '');
  const localDigits = digits.startsWith('55') && digits.length > 11 ? digits.slice(2) : digits;
  return formatPhoneContact(localDigits);
}

function isValidPhoneContact(value: string): boolean {
  const digits = value.replace(/\D/g, '');
  return digits.length === 10 || digits.length === 11;
}

function localIsoDate(): string {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function PessoaDetailPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const params = useParams();
  const personId = Number(params.id);
  const permissions = useSessionStore((state) => state.user?.permissions ?? []);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [addressLookupLoading, setAddressLookupLoading] = useState(false);
  const [printing, setPrinting] = useState(false);
  const [territoryModalOpen, setTerritoryModalOpen] = useState(false);
  const [indicationModalOpen, setIndicationModalOpen] = useState(false);
  const [form] = Form.useForm<EditValues>();
  const [territoryForm] = Form.useForm<TerritoryLinkValues>();
  const [indicationForm] = Form.useForm<IndicationValues>();
  const canViewTerritories = permissions.includes('territorio.visualizar');
  const canEditTerritories = permissions.includes('territorio.editar');
  const selectedAddressStateCode = Form.useWatch('codigo_uf_ibge', form) as number | undefined;
  const selectedAddressCityCode = Form.useWatch('codigo_municipio_ibge', form) as
    | number
    | undefined;
  const selectedAddressLatitude = Form.useWatch('latitude', form) as number | null | undefined;
  const selectedAddressLongitude = Form.useWatch('longitude', form) as number | null | undefined;
  const selectedVoterStateCode = Form.useWatch('municipio_voto_uf_ibge', form) as
    | number
    | undefined;
  const selectedVoterCityCode = Form.useWatch('codigo_municipio_ibge', form) as number | undefined;
  const selectedDocumentType = Form.useWatch('tipo_documento', form) as TipoDocumento | undefined;
  const isCpfDocument =
    editor?.type === 'document'
      ? editor.item.tipo_documento === 'cpf'
      : selectedDocumentType === 'cpf';
  const selectedContactType = Form.useWatch('tipo_contato', form) as TipoContato | undefined;
  const isPhoneContact =
    editor?.type === 'contact'
      ? phoneContactTypes.has(editor.item.tipo_contato)
      : selectedContactType
        ? phoneContactTypes.has(selectedContactType)
        : false;
  const contactTypeForEditor =
    editor?.type === 'contact' ? editor.item.tipo_contato : selectedContactType;
  const personQuery = useQuery({
    queryKey: ['cadastro', 'pessoa', personId],
    queryFn: () => obterPessoa(personId),
    enabled: Number.isInteger(personId),
  });
  const tagsQuery = useQuery({ queryKey: ['cadastro', 'tags'], queryFn: listarTags });
  const tagColorsById = useMemo(() => {
    const map = new Map<number, string>();
    for (const item of tagsQuery.data ?? []) {
      if (item.cor) map.set(item.id, item.cor);
    }
    return map;
  }, [tagsQuery.data]);
  const estadosCivisQuery = useQuery({
    queryKey: ['cadastro', 'estados-civis'],
    queryFn: listarEstadosCivis,
  });
  const religionsQuery = useQuery({
    queryKey: ['cadastro', 'religioes'],
    queryFn: listarReligioes,
  });
  const personTypesQuery = useQuery({
    queryKey: ['cadastro', 'tipos'],
    queryFn: listarTiposPessoa,
  });
  const estadosQuery = useQuery({
    queryKey: ['territorios', 'global', 'estados'],
    queryFn: listarEstados,
  });
  const municipiosQuery = useQuery({
    queryKey: ['territorios', 'global', 'municipios', selectedAddressStateCode],
    queryFn: () => listarMunicipios(selectedAddressStateCode),
    enabled: Boolean(selectedAddressStateCode),
  });
  const territoriesQuery = useQuery({
    queryKey: ['territorios', 'ativos'],
    queryFn: () => listarTerritorios(false),
    enabled: canViewTerritories,
  });
  const personTerritoriesQuery = useQuery({
    queryKey: ['territorios', 'pessoa', personId],
    queryFn: () => listarTerritoriosPessoa(personId),
    enabled: canViewTerritories && Number.isInteger(personId),
  });
  const addressMapCenter = useMemo<[number, number]>(() => {
    const municipality = municipiosQuery.data?.find(
      (item) => item.codigo_ibge === selectedAddressCityCode,
    );
    const latitude = municipality?.latitude ? Number(municipality.latitude) : Number.NaN;
    const longitude = municipality?.longitude ? Number(municipality.longitude) : Number.NaN;
    return Number.isFinite(latitude) && Number.isFinite(longitude)
      ? [latitude, longitude]
      : [-16.6869, -49.2648];
  }, [municipiosQuery.data, selectedAddressCityCode]);
  const voterMunicipiosQuery = useQuery({
    queryKey: ['territorios', 'global', 'municipios', selectedVoterStateCode],
    queryFn: () => listarMunicipios(selectedVoterStateCode),
    enabled: Boolean(selectedVoterStateCode),
  });
  const voterDetailCityCode = personQuery.data?.eleitor?.codigo_municipio_ibge ?? undefined;
  const voterDetailStateCode = voterDetailCityCode
    ? Math.floor(voterDetailCityCode / 100000)
    : undefined;
  const voterDetailZoneId = personQuery.data?.eleitor?.zona_eleitoral_id ?? undefined;
  const voterDetailPollingPlaceId = personQuery.data?.eleitor?.local_votacao_id ?? undefined;
  const voterDetailMunicipiosQuery = useQuery({
    queryKey: ['territorios', 'global', 'municipios', voterDetailStateCode, 'voter-detail'],
    queryFn: () => listarMunicipios(voterDetailStateCode),
    enabled: Boolean(voterDetailStateCode),
  });
  const voterDetailZonesQuery = useQuery({
    queryKey: ['territorios', 'global', 'zonas', voterDetailCityCode, 'voter-detail'],
    queryFn: () => listarZonas(undefined, voterDetailCityCode),
    enabled: Boolean(voterDetailCityCode),
  });
  const voterDetailPollingPlacesQuery = useQuery({
    queryKey: [
      'territorios',
      'global',
      'locais-votacao',
      voterDetailCityCode,
      voterDetailZoneId,
      'voter-detail',
    ],
    queryFn: () =>
      listarLocaisVotacao({
        codigo_municipio_ibge: voterDetailCityCode,
        zona_eleitoral_id: voterDetailZoneId,
      }),
    enabled: Boolean(voterDetailCityCode || voterDetailZoneId),
  });
  const voterDetailSectionsQuery = useQuery({
    queryKey: [
      'territorios',
      'global',
      'secoes',
      voterDetailZoneId,
      voterDetailPollingPlaceId,
      'voter-detail',
    ],
    queryFn: () => listarSecoes(voterDetailZoneId!, voterDetailPollingPlaceId),
    enabled: Boolean(voterDetailZoneId),
  });
  const addressStateCodes = Array.from(
    new Set(
      (personQuery.data?.enderecos ?? [])
        .map((item) => item.endereco.codigo_municipio_ibge)
        .filter((cityCode): cityCode is number => Boolean(cityCode))
        .map((cityCode) => Math.floor(cityCode / 100000)),
    ),
  );
  const addressMunicipalityQueries = useQueries({
    queries: addressStateCodes.map((stateCode) => ({
      queryKey: ['territorios', 'global', 'municipios', stateCode],
      queryFn: () => listarMunicipios(stateCode),
    })),
  });
  const saveMutation = useMutation({
    mutationFn: async (values: EditValues) => {
      if (!editor) return;
      if (editor.type === 'person') {
        const { tipo_ids: typeIds, ...personValues } = values;
        await atualizarPessoa(personId, personValues);
        await substituirTiposPessoa(personId, (typeIds as number[] | undefined) ?? []);
      }
      if (editor.type === 'types')
        await substituirTiposPessoa(personId, (values.tipo_ids as number[] | undefined) ?? []);
      if (editor.type === 'document') await atualizarDocumento(personId, editor.item.id, values);
      if (editor.type === 'new-document')
        await criarDocumento(personId, {
          tipo_documento: values.tipo_documento as TipoDocumento,
          numero: String(values.numero),
          orgao_emissor: (values.orgao_emissor as string | undefined) || null,
          uf_emissor: (values.uf_emissor as string | undefined) || null,
        });
      if (editor.type === 'contact') await atualizarContato(personId, editor.item.id, values);
      if (editor.type === 'new-contact')
        await criarContato(personId, {
          tipo_contato: values.tipo_contato as TipoContato,
          valor: String(values.valor),
          principal: Boolean(values.principal),
          observacao: (values.observacao as string | undefined) || null,
        });
      if (editor.type === 'social' || editor.type === 'new-social') {
        const payload = {
          rede: values.rede as RedeSocial,
          usuario_perfil: (values.usuario_perfil as string | undefined) || null,
          url: (values.url as string | undefined) || null,
          seguidores: (values.seguidores as number | undefined) ?? null,
        };
        if (editor.type === 'social') {
          await atualizarRedeSocial(personId, editor.item.id, payload);
        } else {
          await criarRedeSocial(personId, payload);
        }
      }
      if (editor.type === 'voter')
        await definirEleitor(personId, {
          titulo_eleitor: (values.titulo_eleitor as string | undefined) || null,
          zona_eleitoral_id: (values.zona_eleitoral_id as number | undefined) || null,
          secao_eleitoral_id: (values.secao_eleitoral_id as number | undefined) || null,
          local_votacao_id: (values.local_votacao_id as number | undefined) || null,
          codigo_municipio_ibge: (values.codigo_municipio_ibge as number | undefined) || null,
          situacao_titulo:
            (values.situacao_titulo as 'regular' | 'suspenso' | 'cancelado' | 'desconhecido') ||
            'regular',
        });
      if (editor.type === 'address')
        await atualizarEndereco(personId, editor.item.id, {
          principal: values.principal,
          endereco: {
            cep: values.cep,
            codigo_municipio_ibge: values.codigo_municipio_ibge,
            logradouro: values.logradouro,
            numero: values.numero,
            complemento: values.complemento,
            bairro_texto: values.bairro_texto,
            latitude: values.latitude,
            longitude: values.longitude,
          },
        });
    },
    onSuccess: async () => {
      AppToast.success('Dados atualizados.');
      setEditor(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['cadastro', 'pessoa', personId] }),
        queryClient.invalidateQueries({ queryKey: ['territorios', 'mapa'] }),
      ]);
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const completenessMutation = useMutation({
    mutationFn: () => calcularCompletudePessoa(personId),
    onSuccess: async (updatedPerson) => {
      AppToast.success('Completude calculada.');
      queryClient.setQueryData(['cadastro', 'pessoa', personId], updatedPerson);
      await queryClient.invalidateQueries({ queryKey: ['cadastro', 'pessoa', personId] });
      await queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const createIndicationMutation = useMutation({
    mutationFn: (values: IndicationValues) =>
      criarIndicacao(personId, {
        pessoa_indicada_id: values.pessoa_indicada_id,
        origem: values.origem?.trim() || null,
        contexto: values.contexto?.trim() || null,
        data_indicacao: values.data_indicacao,
      }),
    onSuccess: async () => {
      AppToast.success('Indicação adicionada.');
      setIndicationModalOpen(false);
      indicationForm.resetFields();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['cadastro', 'pessoa', personId] }),
        queryClient.invalidateQueries({ queryKey: ['cadastro', 'grafo-indicacoes'] }),
      ]);
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const linkTerritoryMutation = useMutation({
    mutationFn: (values: TerritoryLinkValues) =>
      vincularPessoaTerritorio(values.territorio_id, personId, values.vinculo),
    onSuccess: async () => {
      AppToast.success('Território associado à pessoa.');
      setTerritoryModalOpen(false);
      territoryForm.resetFields();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['territorios', 'pessoa', personId] }),
        queryClient.invalidateQueries({ queryKey: ['territorios', 'mapa'] }),
      ]);
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });
  const unlinkTerritoryMutation = useMutation({
    mutationFn: removerVinculoPessoaTerritorio,
    onSuccess: async () => {
      AppToast.success('Vínculo territorial removido.');
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['territorios', 'pessoa', personId] }),
        queryClient.invalidateQueries({ queryKey: ['territorios', 'mapa'] }),
      ]);
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const openEditor = (next: Editor) => {
    const person = personQuery.data;
    setEditor(next);
    form.resetFields();
    if (!person) return;
    if (next.type === 'person') {
      form.setFieldsValue({
        nome_completo: person.nome_completo,
        nome_social: person.nome_social,
        apelido: person.apelido,
        sexo: person.sexo,
        data_nascimento: person.data_nascimento,
        estado_civil: person.estado_civil,
        religiao_id: person.religiao_id,
        tipo_ids: person.tipos.map((item) => item.id),
        observacoes: person.observacoes,
      });
    } else if (next.type === 'types') {
      form.setFieldsValue({
        tipo_ids: person.tipos.map((item) => item.id),
      });
    } else if (next.type === 'address') {
      const cityCode = next.item.endereco.codigo_municipio_ibge;
      form.setFieldsValue({
        cep: next.item.endereco.cep ? formatCep(next.item.endereco.cep) : next.item.endereco.cep,
        codigo_uf_ibge: cityCode ? Math.floor(cityCode / 100000) : undefined,
        codigo_municipio_ibge: cityCode,
        logradouro: next.item.endereco.logradouro,
        numero: next.item.endereco.numero,
        complemento: next.item.endereco.complemento,
        bairro_texto: next.item.endereco.bairro_texto,
        latitude: next.item.endereco.latitude ? Number(next.item.endereco.latitude) : undefined,
        longitude: next.item.endereco.longitude ? Number(next.item.endereco.longitude) : undefined,
        principal: next.item.principal,
      });
    } else if (next.type === 'document') {
      form.setFieldsValue({
        numero: formatDocumentValue(next.item.tipo_documento, next.item.numero),
        orgao_emissor: next.item.orgao_emissor,
        uf_emissor: next.item.uf_emissor,
      });
    } else if (next.type === 'new-document') {
      const firstAvailableDocumentType =
        documentTypeOptions.find(
          (option) =>
            !person.documentos.some((document) => document.tipo_documento === option.value),
        )?.value ?? 'outro';
      form.setFieldsValue({
        tipo_documento: firstAvailableDocumentType,
      });
    } else if (next.type === 'contact') {
      form.setFieldsValue({
        valor: formatContactValue(next.item.tipo_contato, next.item.valor),
        principal: next.item.principal,
        observacao: next.item.observacao,
      });
    } else if (next.type === 'new-contact') {
      const firstAvailableContactType =
        contactTypeOptions.find(
          (option) => !person.contatos.some((contact) => contact.tipo_contato === option.value),
        )?.value ?? 'email';
      form.setFieldsValue({
        tipo_contato: firstAvailableContactType,
        principal: false,
      });
    } else if (next.type === 'social') {
      form.setFieldsValue({
        rede: next.item.rede,
        usuario_perfil: next.item.usuario_perfil,
        url: next.item.url,
        seguidores: next.item.seguidores,
      });
    } else if (next.type === 'new-social') {
      form.setFieldsValue({ rede: 'instagram' });
    } else if (next.type === 'voter') {
      const voter = person.eleitor;
      const cityCode = voter?.codigo_municipio_ibge;
      form.setFieldsValue({
        titulo_eleitor: voter?.titulo_eleitor,
        municipio_voto_uf_ibge: cityCode ? Math.floor(cityCode / 100000) : undefined,
        codigo_municipio_ibge: cityCode,
        zona_eleitoral_id: voter?.zona_eleitoral_id,
        local_votacao_id: voter?.local_votacao_id,
        secao_eleitoral_id: voter?.secao_eleitoral_id,
        situacao_titulo: voter?.situacao_titulo ?? 'regular',
      });
    }
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

      const cityCode = address.ibge ? Number(address.ibge) : undefined;
      const state = estadosQuery.data?.find((item) => item.uf === address.uf);
      const stateCode =
        state?.codigo_ibge ??
        (Number.isFinite(cityCode) ? Math.floor(Number(cityCode) / 100000) : undefined);

      form.setFieldsValue({
        cep: address.cep ? formatCep(address.cep) : formattedCep,
        codigo_uf_ibge: stateCode,
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
  const documentOptionsForNewDocument = documentTypeOptions.map((option) => ({
    ...option,
    disabled: person.documentos.some((document) => document.tipo_documento === option.value),
  }));
  const hasAvailableDocumentType = documentOptionsForNewDocument.some((option) => !option.disabled);
  const estadoOptions = (estadosQuery.data ?? []).map((estado) => ({
    value: estado.uf,
    label: `${estado.uf} - ${estado.nome}`,
  }));
  const addressStateOptions = (estadosQuery.data ?? []).map((estado) => ({
    value: estado.codigo_ibge,
    label: `${estado.uf} - ${estado.nome}`,
  }));
  const addressCityOptions = (municipiosQuery.data ?? []).map((municipio) => ({
    value: municipio.codigo_ibge,
    label: municipio.nome,
  }));
  const voterCityOptions = (voterMunicipiosQuery.data ?? []).map((municipio) => ({
    value: municipio.codigo_ibge,
    label: municipio.nome,
  }));
  const voterStatusOptions = [
    { value: 'regular', label: 'Regular' },
    { value: 'suspenso', label: 'Suspenso' },
    { value: 'cancelado', label: 'Cancelado' },
    { value: 'desconhecido', label: 'Desconhecido' },
  ];
  const voterState = voterDetailStateCode
    ? estadosQuery.data?.find((estado) => estado.codigo_ibge === voterDetailStateCode)
    : undefined;
  const voterMunicipality = voterDetailCityCode
    ? voterDetailMunicipiosQuery.data?.find(
        (municipio) => municipio.codigo_ibge === voterDetailCityCode,
      )
    : undefined;
  const voterZone = voterDetailZoneId
    ? voterDetailZonesQuery.data?.find((zone) => zone.id === voterDetailZoneId)
    : undefined;
  const voterPollingPlace = voterDetailPollingPlaceId
    ? voterDetailPollingPlacesQuery.data?.find((place) => place.id === voterDetailPollingPlaceId)
    : undefined;
  const voterSection = person.eleitor?.secao_eleitoral_id
    ? voterDetailSectionsQuery.data?.find(
        (section) => section.id === person.eleitor?.secao_eleitoral_id,
      )
    : undefined;
  const addressLocationByCityCode = new Map<number, string>();
  addressMunicipalityQueries.forEach((query) => {
    (query.data ?? []).forEach((municipio) => {
      const estado = estadosQuery.data?.find(
        (item) => item.codigo_ibge === municipio.codigo_uf_ibge,
      );
      addressLocationByCityCode.set(
        municipio.codigo_ibge,
        estado ? `${municipio.nome} - ${estado.uf}` : municipio.nome,
      );
    });
  });
  const contactOptionsForNewContact = contactTypeOptions.map((option) => ({
    ...option,
    disabled: person.contatos.some((contact) => contact.tipo_contato === option.value),
  }));
  const hasAvailableContactType = contactOptionsForNewContact.some((option) => !option.disabled);
  const voterLinkActionLabel = person.eleitor ? 'Atualizar vínculo' : 'Adicionar vínculo';
  const modalTitle =
    editor?.type === 'new-document'
      ? 'Adicionar documento'
      : editor?.type === 'new-contact'
        ? 'Adicionar contato'
        : editor?.type === 'new-social'
          ? 'Adicionar rede social'
          : editor?.type === 'social'
            ? 'Editar rede social'
            : editor?.type === 'types'
              ? 'Editar tipos da pessoa'
              : editor?.type === 'voter'
                ? voterLinkActionLabel
                : 'Editar cadastro';
  const noItems = (
    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Nenhum vínculo registrado" />
  );

  const printRegistration = async () => {
    setPrinting(true);
    try {
      const [attachments, interactions] = await Promise.all([
        listAttachments('pessoa', personId),
        listarInteracoesPessoa(personId, 5).catch(() => []),
      ]);
      const photoAttachment = attachments.find((item) => item.tipo?.codigo === 'foto');
      const photo = photoAttachment ? await getAttachmentBlob(photoAttachment.id, true) : null;
      const pollingPlaceAddress = voterPollingPlace
        ? [
            voterPollingPlace.logradouro,
            voterPollingPlace.numero,
            voterPollingPlace.cep ? `CEP ${voterPollingPlace.cep}` : null,
          ]
            .filter(Boolean)
            .join(', ')
        : undefined;

      await generatePersonRegistrationPdf({
        person,
        interactions,
        photo,
        civilStatus: estadosCivisQuery.data?.find((item) => item.id === person.estado_civil)?.nome,
        addressLabels: addressLocationByCityCode,
        electoral: {
          municipality: voterMunicipality?.nome,
          state: voterState?.uf,
          zone: voterZone ? String(voterZone.numero_zona) : undefined,
          section: voterSection ? String(voterSection.numero_secao) : undefined,
          pollingPlace: voterPollingPlace?.nome,
          pollingPlaceAddress,
        },
      });
      AppToast.success('Ficha cadastral gerada em PDF.');
    } catch (error) {
      AppToast.error(
        normalizeApiError(error).message || 'Não foi possível gerar a ficha cadastral.',
      );
    } finally {
      setPrinting(false);
    }
  };

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
            <Button icon={<PrinterOutlined />} loading={printing} onClick={printRegistration}>
              Imprimir ficha
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
                    {formatDate(person.data_nascimento)}
                  </Descriptions.Item>
                  <Descriptions.Item label="Sexo">
                    {sexOptions.find((item) => item.value === person.sexo)?.label || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Estado civil">
                    {estadosCivisQuery.data?.find((item) => item.id === person.estado_civil)
                      ?.nome || '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Religião">
                    {religionsQuery.data?.find((item) => item.id === person.religiao_id)?.nome ||
                      '—'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Tipos">
                    <Space wrap>
                      {person.tipos.length
                        ? person.tipos.map((item) => <Tag key={item.id}>{item.nome}</Tag>)
                        : '—'}
                      <Button
                        type="link"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => openEditor({ type: 'types' })}
                      >
                        Alterar tipos
                      </Button>
                    </Space>
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
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                    <Typography.Title level={5} style={{ margin: 0 }}>
                      Contatos
                    </Typography.Title>
                    <Button
                      type="primary"
                      disabled={!hasAvailableContactType}
                      onClick={() => openEditor({ type: 'new-contact' })}
                    >
                      Adicionar contato
                    </Button>
                  </Space>
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
                              {formatContactValue(item.tipo_contato, item.valor)}
                              {item.principal ? <Tag color="blue">Principal</Tag> : null}
                            </Space>
                          }
                          description={item.tipo_contato}
                        />
                      </List.Item>
                    )}
                  />
                  <Space style={{ width: '100%', justifyContent: 'space-between', marginTop: 24 }}>
                    <Typography.Title level={5} style={{ margin: 0 }}>
                      Redes sociais
                    </Typography.Title>
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => openEditor({ type: 'new-social' })}
                    >
                      Adicionar rede social
                    </Button>
                  </Space>
                  <List
                    dataSource={person.redes_sociais}
                    locale={{ emptyText: noItems }}
                    renderItem={(item) => (
                      <List.Item
                        actions={[
                          <Button
                            key="edit"
                            type="link"
                            onClick={() => openEditor({ type: 'social', item })}
                          >
                            Editar
                          </Button>,
                        ]}
                      >
                        <List.Item.Meta
                          title={
                            socialNetworkOptions.find((option) => option.value === item.rede)
                              ?.label || item.rede
                          }
                          description={
                            <Space direction="vertical" size={0}>
                              <Typography.Text>
                                {item.usuario_perfil || 'Usuário não informado'}
                              </Typography.Text>
                              {item.url ? (
                                <Typography.Link href={item.url} target="_blank" rel="noreferrer">
                                  {item.url}
                                </Typography.Link>
                              ) : null}
                              <Typography.Text type="secondary">
                                {item.seguidores === null
                                  ? 'Seguidores não informados'
                                  : `${item.seguidores.toLocaleString('pt-BR')} seguidores`}
                              </Typography.Text>
                            </Space>
                          }
                        />
                      </List.Item>
                    )}
                  />
                </Space>
              ),
            },
            {
              key: 'documentos',
              label: `Documentos (${person.documentos.length})`,
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div style={{ width: '100%', textAlign: 'right' }}>
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      disabled={!hasAvailableDocumentType}
                      onClick={() => openEditor({ type: 'new-document' })}
                    >
                      Adicionar documento
                    </Button>
                  </div>
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
                          title={formatDocumentValue(item.tipo_documento, item.numero)}
                          description={item.tipo_documento.toUpperCase()}
                        />
                      </List.Item>
                    )}
                  />
                </Space>
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
                        title={formatFullAddress(
                          item.endereco,
                          item.endereco.codigo_municipio_ibge
                            ? addressLocationByCityCode.get(item.endereco.codigo_municipio_ibge)
                            : undefined,
                        )}
                        description={
                          <Space>
                            {item.tipo}
                            {item.principal ? <Tag color="blue">Principal</Tag> : null}
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              ),
            },
            {
              key: 'territorios',
              label: `Territórios (${personTerritoriesQuery.data?.length ?? 0})`,
              children: canViewTerritories ? (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {canEditTerritories ? (
                    <div style={{ width: '100%', textAlign: 'right' }}>
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => {
                          territoryForm.setFieldsValue({ vinculo: 'moradia' });
                          setTerritoryModalOpen(true);
                        }}
                      >
                        Associar território
                      </Button>
                    </div>
                  ) : null}
                  <List
                    loading={personTerritoriesQuery.isPending}
                    dataSource={personTerritoriesQuery.data ?? []}
                    locale={{ emptyText: 'Nenhum território associado.' }}
                    renderItem={(item) => (
                      <List.Item
                        actions={
                          canEditTerritories
                            ? [
                                <Popconfirm
                                  key="remove"
                                  title="Remover vínculo territorial?"
                                  description={`A pessoa deixará de estar associada a ${item.territorio_nome}.`}
                                  okText="Remover"
                                  cancelText="Cancelar"
                                  okButtonProps={{ danger: true }}
                                  onConfirm={() => unlinkTerritoryMutation.mutateAsync(item.id)}
                                >
                                  <Button
                                    type="link"
                                    danger
                                    icon={<DeleteOutlined />}
                                    loading={
                                      unlinkTerritoryMutation.isPending &&
                                      unlinkTerritoryMutation.variables === item.id
                                    }
                                  >
                                    Remover
                                  </Button>
                                </Popconfirm>,
                              ]
                            : undefined
                        }
                      >
                        <List.Item.Meta
                          title={
                            <Space>
                              {item.territorio_nome}
                              {!item.territorio_ativo ? <Tag>Inativo</Tag> : null}
                            </Space>
                          }
                          description={
                            <Space>
                              <Tag color="blue">{item.tipo_nome}</Tag>
                              <span>
                                Vínculo:{' '}
                                {territoryLinkOptions.find(
                                  (option) => option.value === item.vinculo,
                                )?.label ?? item.vinculo}
                              </span>
                            </Space>
                          }
                        />
                      </List.Item>
                    )}
                  />
                </Space>
              ) : (
                <Alert
                  type="info"
                  showIcon
                  message="Você não possui permissão para visualizar territórios."
                />
              ),
            },
            {
              key: 'eleitor',
              label: 'Eleitor',
              children: (
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div style={{ width: '100%', textAlign: 'right' }}>
                    <Button
                      type="primary"
                      icon={<PlusOutlined />}
                      onClick={() => openEditor({ type: 'voter' })}
                    >
                      {voterLinkActionLabel}
                    </Button>
                  </div>
                  {person.eleitor ? (
                    <Descriptions bordered size="small" column={{ xs: 1, md: 2 }}>
                      <Descriptions.Item label="Título">
                        {person.eleitor.titulo_eleitor || '—'}
                      </Descriptions.Item>
                      <Descriptions.Item label="Estado">
                        {voterState ? `${voterState.uf} - ${voterState.nome}` : '—'}
                      </Descriptions.Item>
                      <Descriptions.Item label="Município">
                        {voterMunicipality?.nome || '—'}
                      </Descriptions.Item>
                      <Descriptions.Item label="Zona">
                        {voterZone?.numero_zona ? `Zona ${voterZone.numero_zona}` : '—'}
                      </Descriptions.Item>
                      <Descriptions.Item label="Local de votação" span={2}>
                        {voterPollingPlace?.nome || '—'}
                      </Descriptions.Item>
                      <Descriptions.Item label="Seção">
                        {voterSection?.numero_secao ? `Seção ${voterSection.numero_secao}` : '—'}
                      </Descriptions.Item>
                      <Descriptions.Item label="Situação">
                        {person.eleitor.situacao_titulo || '—'}
                      </Descriptions.Item>
                    </Descriptions>
                  ) : (
                    noItems
                  )}
                </Space>
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
                            {item.papel_subordinado === 'apoiador' ? 'Apoia' : 'Líder'}:{' '}
                            {item.lideranca_superior_nome || 'Nome não informado'}
                          </Tag>
                        ))
                      : noItems}
                  </section>
                  <section>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: 12,
                        marginBottom: 8,
                      }}
                    >
                      <Typography.Title level={5} style={{ margin: 0 }}>
                        Indicações
                      </Typography.Title>
                      {permissions.includes('cadastro.editar') ? (
                        <Button
                          type="primary"
                          icon={<PlusOutlined />}
                          onClick={() => {
                            indicationForm.setFieldsValue({ data_indicacao: localIsoDate() });
                            setIndicationModalOpen(true);
                          }}
                        >
                          Adicionar indicação
                        </Button>
                      ) : null}
                    </div>
                    <List
                      size="small"
                      dataSource={person.indicacoes}
                      locale={{ emptyText: 'Nenhuma indicação cadastrada.' }}
                      renderItem={(item) => (
                        <List.Item>
                          <List.Item.Meta
                            title={
                              item.pessoa_indicada_id ? (
                                <Button
                                  type="link"
                                  style={{ padding: 0, height: 'auto' }}
                                  onClick={() =>
                                    navigate(`/cadastro/pessoas/${item.pessoa_indicada_id}`)
                                  }
                                >
                                  Indicou{' '}
                                  {item.pessoa_indicada_nome ||
                                    `pessoa #${item.pessoa_indicada_id}`}
                                </Button>
                              ) : (
                                'Pessoa indicada não informada'
                              )
                            }
                            description={
                              <Space direction="vertical" size={2}>
                                <span>Data: {formatDate(item.data_indicacao)}</span>
                                <span>Origem: {item.origem || 'Não informada'}</span>
                                {item.contexto ? <span>Contexto: {item.contexto}</span> : null}
                              </Space>
                            }
                          />
                        </List.Item>
                      )}
                    />
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
                      <Tag key={item.id} color={tagColorsById.get(item.id)}>
                        {item.nome}
                      </Tag>
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
              key: 'anexos',
              label: 'Foto e anexos',
              children: (
                <AttachmentsPanel
                  entity="pessoa"
                  entityId={personId}
                  enablePersonPhoto
                  canEdit={permissions.includes('cadastro.editar')}
                />
              ),
            },
            {
              key: 'interacoes',
              label: 'Interações',
              children: permissions.includes('comunicacao.visualizar') ? (
                <PersonInteractionsPanel
                  pessoaId={personId}
                  canCreate={permissions.includes('comunicacao.criar')}
                />
              ) : (
                <Alert
                  type="warning"
                  showIcon
                  message="Você não tem permissão para visualizar interações."
                />
              ),
            },
            {
              key: 'historico',
              label: 'Histórico',
              children: (
                <Descriptions column={1} bordered size="small">
                  <Descriptions.Item label="Criado em">
                    {formatDateTime(person.criado_em)}
                  </Descriptions.Item>
                  <Descriptions.Item label="Atualizado em">
                    {formatDateTime(person.atualizado_em)}
                  </Descriptions.Item>
                  <Descriptions.Item label="Completude">
                    <Space>
                      <span>
                        {person.completude_cadastral
                          ? `${person.completude_cadastral}%`
                          : 'Não calculada'}
                      </span>
                      {permissions.includes('cadastro.editar') ? (
                        <Button
                          size="small"
                          loading={completenessMutation.isPending}
                          onClick={() => completenessMutation.mutate()}
                        >
                          Calcular completude do cadastro
                        </Button>
                      ) : null}
                    </Space>
                  </Descriptions.Item>
                </Descriptions>
              ),
            },
          ]}
        />
      </Card>

      <Modal
        open={indicationModalOpen}
        title="Adicionar indicação"
        okText="Adicionar"
        cancelText="Cancelar"
        confirmLoading={createIndicationMutation.isPending}
        onCancel={() => {
          setIndicationModalOpen(false);
          indicationForm.resetFields();
        }}
        onOk={() =>
          indicationForm.validateFields().then((values) => createIndicationMutation.mutate(values))
        }
      >
        <Form form={indicationForm} layout="vertical" requiredMark={false}>
          <Form.Item
            name="pessoa_indicada_id"
            label="Pessoa indicada"
            rules={[{ required: true, message: 'Selecione a pessoa indicada' }]}
          >
            <RemotePersonSelect excludeIds={[personId]} />
          </Form.Item>
          <Form.Item name="data_indicacao" label="Data da indicação" rules={[{ required: true }]}>
            <Input type="date" />
          </Form.Item>
          <Form.Item name="origem" label="Origem">
            <Input maxLength={60} placeholder="Ex.: visita ao comitê, reunião ou evento" />
          </Form.Item>
          <Form.Item name="contexto" label="Contexto">
            <Input.TextArea
              rows={4}
              maxLength={255}
              showCount
              placeholder="Descreva como aconteceu a indicação"
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={territoryModalOpen}
        title="Associar território"
        okText="Associar"
        cancelText="Cancelar"
        confirmLoading={linkTerritoryMutation.isPending}
        onCancel={() => {
          setTerritoryModalOpen(false);
          territoryForm.resetFields();
        }}
        onOk={() =>
          territoryForm.validateFields().then((values) => linkTerritoryMutation.mutate(values))
        }
      >
        <Form form={territoryForm} layout="vertical" requiredMark={false}>
          <Form.Item
            name="territorio_id"
            label="Território"
            rules={[{ required: true, message: 'Selecione o território' }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              loading={territoriesQuery.isPending}
              placeholder="Selecione"
              options={(territoriesQuery.data ?? []).map((territory) => ({
                value: territory.id,
                label: `${territory.nome} (${territory.tipo_nome})`,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="vinculo"
            label="Tipo de vínculo"
            rules={[{ required: true, message: 'Selecione o tipo de vínculo' }]}
          >
            <Select options={territoryLinkOptions} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={Boolean(editor)}
        title={modalTitle}
        width={editor?.type === 'address' ? 820 : undefined}
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
              <Row gutter={12}>
                <Col xs={24} md={12}>
                  <Form.Item name="data_nascimento" label="Nascimento">
                    <Input type="date" />
                  </Form.Item>
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="sexo" label="Sexo">
                    <Select allowClear options={sexOptions} />
                  </Form.Item>
                </Col>
              </Row>
              <Form.Item name="estado_civil" label="Estado civil">
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  options={(estadosCivisQuery.data ?? []).map((item) => ({
                    value: item.id,
                    label: item.nome,
                  }))}
                />
              </Form.Item>
              <Form.Item name="religiao_id" label="Religião">
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  loading={religionsQuery.isPending}
                  options={(religionsQuery.data ?? []).map((item) => ({
                    value: item.id,
                    label: item.nome,
                  }))}
                />
              </Form.Item>
              <Form.Item name="tipo_ids" label="Tipos da pessoa">
                <Select
                  mode="multiple"
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  loading={personTypesQuery.isPending}
                  options={(personTypesQuery.data ?? []).map((item) => ({
                    value: item.id,
                    label: item.nome,
                  }))}
                />
              </Form.Item>
              <Form.Item name="observacoes" label="Observações">
                <Input.TextArea rows={3} />
              </Form.Item>
            </>
          ) : null}
          {editor?.type === 'types' ? (
            <Form.Item name="tipo_ids" label="Tipos da pessoa">
              <Select
                mode="multiple"
                allowClear
                showSearch
                optionFilterProp="label"
                loading={personTypesQuery.isPending}
                placeholder="Eleitor, apoiador, voluntário..."
                options={(personTypesQuery.data ?? []).map((item) => ({
                  value: item.id,
                  label: item.nome,
                }))}
              />
            </Form.Item>
          ) : null}
          {editor?.type === 'document' || editor?.type === 'new-document' ? (
            <>
              {editor?.type === 'new-document' ? (
                <Form.Item name="tipo_documento" label="Documento" rules={[{ required: true }]}>
                  <Select
                    options={documentOptionsForNewDocument}
                    onChange={() => form.setFieldValue('numero', undefined)}
                  />
                </Form.Item>
              ) : null}
              <Form.Item
                name="numero"
                label="Número"
                normalize={(value?: string) =>
                  isCpfDocument && value ? formatCpfDocument(value) : value
                }
                rules={[
                  { required: true, message: 'Informe o número do documento' },
                  {
                    validator: async (_, value?: string) => {
                      if (!isCpfDocument || !value) return;
                      if (!isValidCpfDocument(value)) {
                        throw new Error('Informe um CPF valido');
                      }
                    },
                  },
                ]}
              >
                <Input
                  inputMode={isCpfDocument ? 'numeric' : undefined}
                  maxLength={isCpfDocument ? 14 : undefined}
                  placeholder={isCpfDocument ? '000.000.000-00' : undefined}
                />
              </Form.Item>
              <Form.Item name="orgao_emissor" label="Órgão emissor">
                <Input />
              </Form.Item>
              <Form.Item name="uf_emissor" label="UF">
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  loading={estadosQuery.isPending}
                  options={estadoOptions}
                />
              </Form.Item>
            </>
          ) : null}
          {editor?.type === 'contact' || editor?.type === 'new-contact' ? (
            <>
              {editor?.type === 'new-contact' ? (
                <Form.Item name="tipo_contato" label="Canal" rules={[{ required: true }]}>
                  <Select
                    options={contactOptionsForNewContact}
                    onChange={() => form.setFieldValue('valor', undefined)}
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
            </>
          ) : null}
          {editor?.type === 'social' || editor?.type === 'new-social' ? (
            <>
              <Form.Item name="rede" label="Rede social" rules={[{ required: true }]}>
                <Select options={socialNetworkOptions} />
              </Form.Item>
              <Form.Item name="usuario_perfil" label="Usuário ou perfil">
                <Input maxLength={120} placeholder="@usuario" />
              </Form.Item>
              <Form.Item
                name="url"
                label="URL"
                rules={[{ type: 'url', message: 'Informe uma URL válida.' }]}
              >
                <Input maxLength={2048} placeholder="https://..." />
              </Form.Item>
              <Form.Item name="seguidores" label="Quantidade de seguidores">
                <InputNumber min={0} precision={0} style={{ width: '100%' }} />
              </Form.Item>
            </>
          ) : null}
          {editor?.type === 'voter' ? (
            <>
              <Form.Item
                name="titulo_eleitor"
                label="Título eleitoral"
                normalize={(value?: string) =>
                  value ? value.replace(/\D/g, '').slice(0, 12) : value
                }
              >
                <Input inputMode="numeric" maxLength={12} />
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
                      options={addressStateOptions}
                      onChange={() => {
                        form.setFieldsValue({
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
                      placeholder={selectedVoterStateCode ? 'Selecione' : 'Selecione o estado'}
                      options={voterCityOptions}
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
                codigoMunicipioIbge={selectedVoterCityCode}
                hideSection
                fullWidthPollingPlace
              />
              <Row gutter={12}>
                <Col xs={24} md={12}>
                  <ElectoralSectionField />
                </Col>
                <Col xs={24} md={12}>
                  <Form.Item name="situacao_titulo" label="Situação do título">
                    <Select options={voterStatusOptions} />
                  </Form.Item>
                </Col>
              </Row>
            </>
          ) : null}
          {editor?.type === 'address' ? (
            <>
              <Form.Item name="cep" label="CEP">
                <Input
                  inputMode="numeric"
                  maxLength={9}
                  placeholder="00000-000"
                  onBlur={lookupAddressByCep}
                  onPressEnter={lookupAddressByCep}
                  disabled={addressLookupLoading}
                />
              </Form.Item>
              <Form.Item name="logradouro" label="Logradouro">
                <Input />
              </Form.Item>
              <Form.Item name="codigo_uf_ibge" label="Estado">
                <Select
                  allowClear
                  showSearch
                  loading={estadosQuery.isPending}
                  optionFilterProp="label"
                  placeholder="Selecione"
                  options={addressStateOptions}
                  onChange={() =>
                    form.setFieldsValue({
                      codigo_municipio_ibge: undefined,
                      latitude: null,
                      longitude: null,
                    })
                  }
                />
              </Form.Item>
              <Form.Item name="codigo_municipio_ibge" label="Cidade">
                <Select
                  allowClear
                  showSearch
                  disabled={!selectedAddressStateCode}
                  loading={municipiosQuery.isFetching}
                  optionFilterProp="label"
                  placeholder={selectedAddressStateCode ? 'Selecione' : 'Selecione o estado'}
                  options={addressCityOptions}
                  onChange={(cityCode) => {
                    if (cityCode !== selectedAddressCityCode) {
                      form.setFieldsValue({ latitude: null, longitude: null });
                    }
                  }}
                />
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
              <Form.Item label="Localização exata">
                <Space direction="vertical" size="small" style={{ display: 'flex' }}>
                  <Typography.Text type="secondary">
                    Clique no mapa para marcar o imóvel do eleitor. Selecione a cidade antes para
                    centralizar o mapa no município.
                  </Typography.Text>
                  <AddressLocationPicker
                    latitude={selectedAddressLatitude}
                    longitude={selectedAddressLongitude}
                    center={addressMapCenter}
                    onChange={(latitude, longitude) =>
                      form.setFieldsValue({
                        latitude: Number(latitude.toFixed(7)),
                        longitude: Number(longitude.toFixed(7)),
                      })
                    }
                  />
                  <Row gutter={12} style={{ width: '100%' }}>
                    <Col xs={24} md={12}>
                      <Form.Item name="latitude" label="Latitude" style={{ marginBottom: 0 }}>
                        <Input readOnly placeholder="Clique no mapa" />
                      </Form.Item>
                    </Col>
                    <Col xs={24} md={12}>
                      <Form.Item name="longitude" label="Longitude" style={{ marginBottom: 0 }}>
                        <Input readOnly placeholder="Clique no mapa" />
                      </Form.Item>
                    </Col>
                  </Row>
                  {selectedAddressLatitude != null && selectedAddressLongitude != null ? (
                    <Button
                      type="link"
                      danger
                      style={{ paddingInline: 0 }}
                      onClick={() => form.setFieldsValue({ latitude: null, longitude: null })}
                    >
                      Limpar localização
                    </Button>
                  ) : null}
                </Space>
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
