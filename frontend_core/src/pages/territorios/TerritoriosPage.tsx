import {
  ApartmentOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AutoComplete,
  Button,
  Card,
  Checkbox,
  ColorPicker,
  Form,
  Input,
  List,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Tree,
  Typography,
} from 'antd';
import type { DataNode } from 'antd/es/tree';
import L from 'leaflet';
import { useEffect, useMemo, useState } from 'react';
import { CircleMarker, GeoJSON, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import 'leaflet/dist/leaflet.css';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import { listarLiderancas } from '@/modules/cadastro/pessoas-service';
import {
  atualizarTerritorio,
  cadastrarBairro,
  criarTerritorio,
  criarTipoTerritorio,
  inativarTerritorio,
  listarArvoreTerritorial,
  listarBairros,
  listarEstados,
  listarMunicipios,
  listarPessoasNoMarcador,
  listarTerritorios,
  listarTiposTerritorio,
  obterMarcadores,
  obterShapesMalhas,
  obterTerritorio,
  vincularLideranca,
} from '@/modules/territorios/territorios-service';
import { TerritoryMeshEditor } from '@/modules/territorios/TerritoryMeshEditor';
import type {
  MapLayerMode,
  MapMarker,
  MapTerritoryMeshType,
  MapTerritoryShape,
  Territorio,
  TerritorioInput,
  TerritorioMalhaGeometry,
  TerritorioTreeNode,
} from '@/modules/territorios/types';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';
import { formatInteger } from '@/utils/number-format';

type LeafletGeoJson = React.ComponentProps<typeof GeoJSON>['data'];

interface TerritoryForm extends TerritorioInput {
  id?: number;
  bairro_selecao?: string;
  malha_geom?: TerritorioMalhaGeometry | null;
}

const MESH_DRAWING_TYPE_CODES = new Set([
  'microrregiao',
  'comunidade',
  'area_personalizada',
  'bairro',
]);

interface LeadershipForm {
  territorio_id: number;
  lideranca_id: number;
  responsabilidade: 'principal' | 'apoio' | 'compartilhada';
}

interface TerritoryFilters {
  name: string;
  typeId?: number;
  parentId?: number;
  status?: 'active' | 'inactive';
}

const MAP_MESH_LAYER_OPTIONS: Array<{ value: MapTerritoryMeshType; label: string }> = [
  { value: 'municipio', label: 'Municípios' },
  { value: 'bairro', label: 'Bairro' },
  { value: 'microrregiao', label: 'Microrregião' },
  { value: 'comunidade', label: 'Comunidade' },
  { value: 'area_personalizada', label: 'Área personalizada' },
];

const MAP_MESH_LAYER_TYPES = new Set<MapTerritoryMeshType>(
  MAP_MESH_LAYER_OPTIONS.map((option) => option.value),
);

function resolveDefaultMapLayer(tipoCodigo: string): MapTerritoryMeshType | null {
  if (tipoCodigo === 'estado') return 'municipio';
  if (MAP_MESH_LAYER_TYPES.has(tipoCodigo as MapTerritoryMeshType)) {
    return tipoCodigo as MapTerritoryMeshType;
  }
  return null;
}

const initialTerritoryFilters: TerritoryFilters = { name: '' };

const territoryTabKeys = ['list', 'tree', 'map', 'types'] as const;
type TerritoryTabKey = (typeof territoryTabKeys)[number];

function resolveTerritoryTab(aba: string | null): TerritoryTabKey {
  switch (aba) {
    case 'mapa':
      return 'map';
    case 'hierarquia':
      return 'tree';
    case 'tipos':
      return 'types';
    default:
      return 'list';
  }
}

function territoryTabQueryValue(tab: TerritoryTabKey): string | null {
  switch (tab) {
    case 'map':
      return 'mapa';
    case 'tree':
      return 'hierarquia';
    case 'types':
      return 'tipos';
    default:
      return null;
  }
}

function normalizeSearch(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR');
}

function territoryTextColor(backgroundColor: string): string {
  const red = Number.parseInt(backgroundColor.slice(1, 3), 16);
  const green = Number.parseInt(backgroundColor.slice(3, 5), 16);
  const blue = Number.parseInt(backgroundColor.slice(5, 7), 16);
  const luminance = (red * 299 + green * 587 + blue * 114) / 1000;
  return luminance >= 150 ? '#1F1F1F' : '#FFFFFF';
}

function toTreeData(nodes: TerritorioTreeNode[]): DataNode[] {
  return nodes.map((node) => {
    const textColor = territoryTextColor(node.cor);
    return {
      key: node.id,
      title: (
        <Space
          style={{
            backgroundColor: node.cor,
            borderRadius: 6,
            color: textColor,
            padding: '4px 8px',
            cursor: 'pointer',
          }}
        >
          <span>{node.nome}</span>
          <Tag
            style={{
              background: 'transparent',
              borderColor: textColor,
              color: textColor,
              marginInlineEnd: 0,
            }}
          >
            {node.tipo_nome}
          </Tag>
        </Space>
      ),
      children: toTreeData(node.filhos),
    };
  });
}

function randomTerritoryColor(): string {
  const bytes = new Uint8Array(3);
  window.crypto.getRandomValues(bytes);
  return `#${Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('')}`.toUpperCase();
}

function TerritoryMapShapes({
  shapes,
  onShapeClick,
}: {
  shapes: MapTerritoryShape[];
  onShapeClick?: (territorioId: number) => void;
}) {
  const map = useMap();
  const collection = useMemo(
    () => ({
      type: 'FeatureCollection' as const,
      features: shapes.map((shape) => ({
        type: 'Feature' as const,
        properties: {
          territorio_id: shape.territorio_id,
          tipo_codigo: shape.tipo_codigo,
          nome: shape.nome,
          cor: shape.cor,
          quantidade_eleitores: shape.quantidade_eleitores,
          quantidade_pessoas: shape.quantidade_pessoas,
        },
        geometry: shape.geometry,
      })),
    }),
    [shapes],
  );

  useEffect(() => {
    if (!shapes.length) return;
    const bounds = L.geoJSON(collection as LeafletGeoJson).getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [16, 16] });
  }, [collection, map, shapes.length]);

  if (!shapes.length) return null;

  return (
    <GeoJSON
      key={shapes.map((shape) => `${shape.territorio_id}-${shape.cor}`).join('-')}
      data={collection as LeafletGeoJson}
      style={(feature) => {
        const color = String(feature?.properties?.cor ?? '#1677FF');
        return { color, fillColor: color, fillOpacity: 0.2, opacity: 0.9, weight: 2 };
      }}
      onEachFeature={(feature, layer) => {
        const label = document.createElement('div');
        const name = document.createElement('strong');
        const voters = document.createElement('div');
        const people = document.createElement('div');
        name.textContent = String(feature.properties?.nome ?? 'Território');
        people.textContent = `Pessoas vinculadas: ${formatInteger(
          Number(feature.properties?.quantidade_pessoas ?? 0),
        )}`;
        if (feature.properties?.tipo_codigo === 'municipio') {
          voters.textContent = `Qtd Eleitores: ${formatInteger(
            Number(feature.properties?.quantidade_eleitores ?? 0),
          )}`;
          label.append(name, voters, people);
        } else {
          label.append(name, people);
        }
        layer.bindTooltip(label, { direction: 'top', sticky: true });
        if (onShapeClick) {
          const pathLayer = layer as L.Path;
          pathLayer.on('click', () => {
            const territorioId = Number(feature.properties?.territorio_id);
            if (Number.isInteger(territorioId) && territorioId > 0) {
              onShapeClick(territorioId);
            }
          });
          pathLayer.on('mouseover', () => pathLayer.setStyle({ weight: 3, fillOpacity: 0.35 }));
          pathLayer.on('mouseout', () => {
            const color = String(feature?.properties?.cor ?? '#1677FF');
            pathLayer.setStyle({ color, fillColor: color, fillOpacity: 0.2, opacity: 0.9, weight: 2 });
          });
          const pathElement = pathLayer.getElement();
          if (pathElement instanceof HTMLElement || pathElement instanceof SVGElement) {
            pathElement.style.setProperty('cursor', 'pointer');
          }
        }
      }}
    />
  );
}

function PeopleLocationMarkers({
  markers,
  onSelectMarker,
}: {
  markers: MapMarker[];
  onSelectMarker: (marker: MapMarker) => void;
}) {
  const map = useMap();

  useEffect(() => {
    if (!markers.length) return;
    const bounds = L.latLngBounds(
      markers.map((marker) => [Number(marker.latitude), Number(marker.longitude)]),
    );
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [16, 16] });
  }, [map, markers]);

  if (!markers.length) return null;

  return (
    <>
      {markers.map((marker) => (
        <CircleMarker
          key={`${marker.latitude}-${marker.longitude}`}
          center={[Number(marker.latitude), Number(marker.longitude)]}
          radius={Math.min(24, 7 + Math.log2(marker.quantidade + 1) * 3)}
        >
          <Popup>
            <Space direction="vertical" size={2}>
              <span>{formatInteger(marker.quantidade)} pessoa(s) nesta localização</span>
              <Button
                type="link"
                size="small"
                style={{ padding: 0 }}
                onClick={() => onSelectMarker(marker)}
              >
                Ver pessoas
              </Button>
            </Space>
          </Popup>
        </CircleMarker>
      ))}
    </>
  );
}

export function TerritoriosPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = resolveTerritoryTab(searchParams.get('aba'));
  const queryClient = useQueryClient();
  const permissions = useSessionStore((state) => state.user?.permissions ?? []);
  const profiles = useSessionStore((state) => state.user?.profiles ?? []);
  const canCreate = permissions.includes('territorio.criar');
  const canEdit = permissions.includes('territorio.editar');
  const canDelete = permissions.includes('territorio.excluir');
  const isSaasManager = profiles.includes('gestor_saas');
  const [territoryModalOpen, setTerritoryModalOpen] = useState(false);
  const [meshEditorReady, setMeshEditorReady] = useState(false);
  const [typeModalOpen, setTypeModalOpen] = useState(false);
  const [leadershipModalOpen, setLeadershipModalOpen] = useState(false);
  const [selectedTerritory, setSelectedTerritory] = useState<Territorio | null>(null);
  const [mapTerritoryFilter, setMapTerritoryFilter] = useState<'all' | number>('all');
  const [mapLayerMode, setMapLayerMode] = useState<MapLayerMode>('municipio');
  const [mapLayerManuallySet, setMapLayerManuallySet] = useState(false);
  const [selectedMarker, setSelectedMarker] = useState<MapMarker | null>(null);
  const [territoryFilters, setTerritoryFilters] =
    useState<TerritoryFilters>(initialTerritoryFilters);
  const [territoryForm] = Form.useForm<TerritoryForm>();
  const [typeForm] = Form.useForm<{ codigo: string; nome: string; descricao?: string }>();
  const [leadershipForm] = Form.useForm<LeadershipForm>();
  const selectedTerritoryTypeId = Form.useWatch('tipo_territorio_id', territoryForm);
  const selectedStateCode = Form.useWatch('codigo_uf_ibge', territoryForm);
  const selectedCityCode = Form.useWatch('codigo_municipio_ibge', territoryForm);
  const selectedParentId = Form.useWatch('territorio_pai_id', territoryForm);
  const selectedColor = Form.useWatch('cor', territoryForm) ?? '#1677FF';

  const territories = useQuery({
    queryKey: ['territorios'],
    queryFn: () => listarTerritorios(true),
  });
  const selectedMapTerritoryId =
    mapTerritoryFilter === 'all' ? undefined : mapTerritoryFilter;
  const territoryShapes = useQuery({
    queryKey: ['territorios', 'mapa', 'malhas', mapLayerMode, selectedMapTerritoryId],
    queryFn: () => {
      if (mapLayerMode === 'people') return Promise.resolve([]);
      return obterShapesMalhas(mapLayerMode, selectedMapTerritoryId);
    },
    enabled: mapLayerMode !== 'people',
  });
  const types = useQuery({
    queryKey: ['territorios', 'tipos'],
    queryFn: () => listarTiposTerritorio(true),
  });
  const selectedTerritoryType = types.data?.find((item) => item.id === selectedTerritoryTypeId);
  const isStateTerritory = selectedTerritoryType?.codigo === 'estado';
  const isCityTerritory = selectedTerritoryType?.codigo === 'municipio';
  const isNeighborhoodTerritory = selectedTerritoryType?.codigo === 'bairro';
  const usesMeshDrawing = MESH_DRAWING_TYPE_CODES.has(selectedTerritoryType?.codigo ?? '');
  const usesState = isStateTerritory || isCityTerritory || isNeighborhoodTerritory;
  const parentTerritory = (territories.data ?? []).find((item) => item.id === selectedParentId);
  const meshContextMunicipioIbge =
    selectedCityCode ??
    selectedTerritory?.codigo_municipio_ibge ??
    parentTerritory?.codigo_municipio_ibge;
  const meshContextStateCode =
    selectedStateCode ??
    selectedTerritory?.codigo_uf_ibge ??
    parentTerritory?.codigo_uf_ibge ??
    undefined;
  const states = useQuery({
    queryKey: ['territorios', 'global', 'estados'],
    queryFn: listarEstados,
    enabled: usesState,
  });
  const cities = useQuery({
    queryKey: ['territorios', 'global', 'municipios', selectedStateCode],
    queryFn: () => listarMunicipios(selectedStateCode),
    enabled: (isCityTerritory || isNeighborhoodTerritory) && Boolean(selectedStateCode),
  });
  const meshCities = useQuery({
    queryKey: ['territorios', 'global', 'municipios', meshContextStateCode, 'malha'],
    queryFn: () => listarMunicipios(meshContextStateCode),
    enabled: usesMeshDrawing && Boolean(meshContextStateCode),
  });
  const neighborhoods = useQuery({
    queryKey: ['territorios', 'global', 'bairros', selectedCityCode],
    queryFn: () => listarBairros(selectedCityCode!),
    enabled: isNeighborhoodTerritory && Boolean(selectedCityCode),
  });
  const tree = useQuery({
    queryKey: ['territorios', 'arvore'],
    queryFn: listarArvoreTerritorial,
  });
  const leaders = useQuery({
    queryKey: ['cadastro', 'liderancas'],
    queryFn: () => listarLiderancas(),
  });
  const markers = useQuery({
    queryKey: ['territorios', 'mapa', selectedMapTerritoryId],
    queryFn: () => obterMarcadores(selectedMapTerritoryId),
    enabled: mapLayerMode === 'people',
  });
  const markerPeople = useQuery({
    queryKey: [
      'territorios',
      'mapa',
      'pessoas',
      selectedMarker?.latitude,
      selectedMarker?.longitude,
      selectedMapTerritoryId,
    ],
    queryFn: () =>
      listarPessoasNoMarcador(
        selectedMarker!.latitude,
        selectedMarker!.longitude,
        selectedMapTerritoryId,
      ),
    enabled: selectedMarker !== null,
  });

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['territorios'] }),
      queryClient.invalidateQueries({ queryKey: ['cadastro', 'liderancas'] }),
    ]);
  };

  const saveTerritory = useMutation({
    mutationFn: async (values: TerritoryForm) => {
      const { id, bairro_selecao: neighborhoodSelection, ...basePayload } = values;
      let neighborhoodId = values.bairro_id;
      if (isNeighborhoodTerritory) {
        const neighborhoodName = neighborhoodSelection?.trim();
        if (!neighborhoodName || !values.codigo_municipio_ibge) {
          throw new Error('Informe o município e o bairro.');
        }
        const existingNeighborhood = neighborhoods.data?.find(
          (item) => normalizeSearch(item.nome) === normalizeSearch(neighborhoodName),
        );
        if (existingNeighborhood) {
          neighborhoodId = existingNeighborhood.id;
        } else if (
          selectedTerritory?.bairro_id &&
          normalizeSearch(selectedTerritory.nome) === normalizeSearch(neighborhoodName)
        ) {
          neighborhoodId = selectedTerritory.bairro_id;
        } else {
          const createdNeighborhood = await cadastrarBairro(
            values.codigo_municipio_ibge,
            neighborhoodName,
          );
          neighborhoodId = createdNeighborhood.id;
        }
      }
      const payload = {
        ...basePayload,
        bairro_id: neighborhoodId,
        malha_geom: values.malha_geom ?? null,
      };
      return id ? atualizarTerritorio(id, payload) : criarTerritorio(payload);
    },
    onSuccess: async () => {
      AppToast.success(selectedTerritory ? 'Território atualizado.' : 'Território criado.');
      setTerritoryModalOpen(false);
      setSelectedTerritory(null);
      territoryForm.resetFields();
      await queryClient.invalidateQueries({
        queryKey: ['territorios', 'global', 'bairros'],
      });
      await refresh();
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const deactivate = useMutation({
    mutationFn: inativarTerritorio,
    onSuccess: async () => {
      AppToast.success('Território inativado.');
      await refresh();
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const createType = useMutation({
    mutationFn: criarTipoTerritorio,
    onSuccess: async () => {
      AppToast.success('Tipo territorial criado.');
      typeForm.resetFields();
      setTypeModalOpen(false);
      await queryClient.invalidateQueries({ queryKey: ['territorios', 'tipos'] });
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const linkLeader = useMutation({
    mutationFn: (values: LeadershipForm) =>
      vincularLideranca(values.territorio_id, values.lideranca_id, values.responsabilidade),
    onSuccess: async () => {
      AppToast.success('Área de responsabilidade atualizada.');
      leadershipForm.resetFields();
      setLeadershipModalOpen(false);
      await refresh();
    },
    onError: (error) => AppToast.error(normalizeApiError(error).message),
  });

  const treeData = useMemo(() => toTreeData(tree.data ?? []), [tree.data]);
  const activeTerritories = (territories.data ?? []).filter((item) => item.ativo);

  const handleMapTerritoryFilterChange = (value: 'all' | number) => {
    setSelectedMarker(null);
    if (value === 'all') {
      setMapTerritoryFilter('all');
      setMapLayerManuallySet(false);
      return;
    }

    const isFirstTerritorySelection = mapTerritoryFilter === 'all';
    setMapTerritoryFilter(value);

    if (isFirstTerritorySelection && !mapLayerManuallySet) {
      const territory = activeTerritories.find((item) => item.id === value);
      const defaultLayer = territory ? resolveDefaultMapLayer(territory.tipo_codigo) : null;
      if (defaultLayer) setMapLayerMode(defaultLayer);
    }
  };

  const handleMapLayerModeChange = (mode: MapLayerMode) => {
    setMapLayerMode(mode);
    setMapLayerManuallySet(true);
    setSelectedMarker(null);
  };

  const filteredTerritories = useMemo(() => {
    const normalizedName = normalizeSearch(territoryFilters.name.trim());
    return (territories.data ?? []).filter((territory) => {
      if (normalizedName && !normalizeSearch(territory.nome).includes(normalizedName)) return false;
      if (territoryFilters.typeId && territory.tipo_territorio_id !== territoryFilters.typeId)
        return false;
      if (territoryFilters.parentId !== undefined) {
        const expectedParentId = territoryFilters.parentId === 0 ? null : territoryFilters.parentId;
        if (territory.territorio_pai_id !== expectedParentId) return false;
      }
      if (territoryFilters.status && territory.ativo !== (territoryFilters.status === 'active'))
        return false;
      return true;
    });
  }, [territories.data, territoryFilters]);
  const territoryFilterKey = [
    territoryFilters.name,
    territoryFilters.typeId,
    territoryFilters.parentId,
    territoryFilters.status,
  ].join('-');
  const mapCenter: [number, number] = markers.data?.length
    ? [Number(markers.data[0].latitude), Number(markers.data[0].longitude)]
    : [-15.78, -47.93];
  const meshMapCenter = useMemo((): [number, number] => {
    const city = [...(meshCities.data ?? []), ...(cities.data ?? [])].find(
      (item) => item.codigo_ibge === meshContextMunicipioIbge,
    );
    if (city?.latitude && city?.longitude) {
      return [Number(city.latitude), Number(city.longitude)];
    }
    return mapCenter;
  }, [meshCities.data, cities.data, meshContextMunicipioIbge, mapCenter]);

  const openCreate = () => {
    setSelectedTerritory(null);
    territoryForm.resetFields();
    territoryForm.setFieldValue('cor', randomTerritoryColor());
    setTerritoryModalOpen(true);
  };

  const openEdit = async (territory: Territorio) => {
    setSelectedTerritory(territory);
    const fullTerritory = await obterTerritorio(territory.id);
    territoryForm.setFieldsValue({
      id: fullTerritory.id,
      nome: fullTerritory.nome,
      tipo_territorio_id: fullTerritory.tipo_territorio_id,
      territorio_pai_id: fullTerritory.territorio_pai_id ?? undefined,
      codigo_uf_ibge: fullTerritory.codigo_uf_ibge ?? undefined,
      codigo_municipio_ibge: fullTerritory.codigo_municipio_ibge ?? undefined,
      bairro_id: fullTerritory.bairro_id ?? undefined,
      bairro_selecao: fullTerritory.bairro_id ? fullTerritory.nome : undefined,
      zona_eleitoral_id: fullTerritory.zona_eleitoral_id ?? undefined,
      secao_eleitoral_id: fullTerritory.secao_eleitoral_id ?? undefined,
      cor: fullTerritory.cor,
      malha_geom: fullTerritory.malha_geom ?? null,
    });
    setTerritoryModalOpen(true);
  };

  return (
    <div>
      <PageHeader
        title="Territórios"
        description="Estrutura territorial, áreas de responsabilidade e visualização geográfica."
        breadcrumbs={[{ label: 'Início', to: '/dashboard' }, { label: 'Territórios' }]}
        actions={
          canCreate ? (
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              Novo território
            </Button>
          ) : undefined
        }
      />

      <Tabs
        activeKey={activeTab}
        onChange={(key) => {
          const nextTab = key as TerritoryTabKey;
          const aba = territoryTabQueryValue(nextTab);
          const nextParams = new URLSearchParams(searchParams);
          if (aba) nextParams.set('aba', aba);
          else nextParams.delete('aba');
          setSearchParams(nextParams, { replace: true });
        }}
        items={[
          {
            key: 'list',
            label: 'Territórios operacionais',
            children: (
              <Card>
                <Space wrap size="middle" style={{ marginBottom: 20 }}>
                  <Input
                    allowClear
                    placeholder="Buscar por nome"
                    style={{ width: 260 }}
                    value={territoryFilters.name}
                    onChange={(event) =>
                      setTerritoryFilters((current) => ({
                        ...current,
                        name: event.target.value,
                      }))
                    }
                  />
                  <Select
                    allowClear
                    showSearch
                    optionFilterProp="label"
                    placeholder="Todos os tipos"
                    style={{ width: 220 }}
                    value={territoryFilters.typeId}
                    onChange={(typeId) =>
                      setTerritoryFilters((current) => ({ ...current, typeId }))
                    }
                    options={(types.data ?? []).map((type) => ({
                      value: type.id,
                      label: type.nome,
                    }))}
                  />
                  <Select
                    allowClear
                    showSearch
                    optionFilterProp="label"
                    placeholder="Todos os territórios pais"
                    style={{ width: 260 }}
                    value={territoryFilters.parentId}
                    onChange={(parentId) =>
                      setTerritoryFilters((current) => ({ ...current, parentId }))
                    }
                    options={[
                      { value: 0, label: 'Raiz (sem território pai)' },
                      ...(territories.data ?? []).map((territory) => ({
                        value: territory.id,
                        label: territory.nome,
                      })),
                    ]}
                  />
                  <Select
                    allowClear
                    placeholder="Todos os status"
                    style={{ width: 170 }}
                    value={territoryFilters.status}
                    onChange={(status) =>
                      setTerritoryFilters((current) => ({ ...current, status }))
                    }
                    options={[
                      { value: 'active', label: 'Ativo' },
                      { value: 'inactive', label: 'Inativo' },
                    ]}
                  />
                  <Button onClick={() => setTerritoryFilters(initialTerritoryFilters)}>
                    Limpar filtros
                  </Button>
                  <Typography.Text type="secondary">
                    {formatInteger(filteredTerritories.length)} território(s) encontrado(s)
                  </Typography.Text>
                </Space>
                <Table<Territorio>
                  key={territoryFilterKey}
                  rowKey="id"
                  loading={territories.isPending}
                  dataSource={filteredTerritories}
                  pagination={{
                    pageSize: 10,
                    showTotal: (total) => `${formatInteger(total)} território(s)`,
                  }}
                  columns={[
                    { title: 'Nome', dataIndex: 'nome' },
                    {
                      title: 'Tipo',
                      dataIndex: 'tipo_nome',
                      render: (value: string) => <Tag color="blue">{value}</Tag>,
                    },
                    {
                      title: 'Território pai',
                      dataIndex: 'territorio_pai_id',
                      render: (value: number | null) =>
                        value
                          ? territories.data?.find((item) => item.id === value)?.nome || `#${value}`
                          : 'Raiz',
                    },
                    {
                      title: 'Status',
                      dataIndex: 'ativo',
                      render: (value: boolean) => (
                        <Tag color={value ? 'success' : 'default'}>
                          {value ? 'Ativo' : 'Inativo'}
                        </Tag>
                      ),
                    },
                    {
                      title: 'Ações',
                      width: 180,
                      render: (_, item) => (
                        <Space>
                          {canEdit && (
                            <Button
                              aria-label={`Editar ${item.nome}`}
                              icon={<EditOutlined />}
                              onClick={() => openEdit(item)}
                            />
                          )}
                          {canEdit && (
                            <Button
                              aria-label={`Vincular liderança a ${item.nome}`}
                              icon={<TeamOutlined />}
                              onClick={() => {
                                leadershipForm.setFieldValue('territorio_id', item.id);
                                setLeadershipModalOpen(true);
                              }}
                            />
                          )}
                          {canDelete && item.ativo && (
                            <Popconfirm
                              title="Inativar este território?"
                              onConfirm={() => deactivate.mutate(item.id)}
                            >
                              <Button danger icon={<DeleteOutlined />} />
                            </Popconfirm>
                          )}
                        </Space>
                      ),
                    },
                  ]}
                />
              </Card>
            ),
          },
          {
            key: 'tree',
            label: 'Hierarquia',
            children: (
              <Card
                title={
                  <Space>
                    <ApartmentOutlined />
                    Árvore territorial
                  </Space>
                }
              >
                {treeData.length ? (
                  <Tree
                    defaultExpandAll
                    treeData={treeData}
                    showLine
                    onSelect={(selectedKeys) => {
                      const territoryId = Number(selectedKeys[0]);
                      if (Number.isInteger(territoryId) && territoryId > 0) {
                        navigate(`/territorios/${territoryId}`);
                      }
                    }}
                  />
                ) : (
                  <Typography.Text type="secondary">
                    Nenhuma estrutura territorial cadastrada.
                  </Typography.Text>
                )}
              </Card>
            ),
          },
          {
            key: 'map',
            label: 'Mapa',
            children: (
              <Card title="Mapa dos territórios">
                <Space wrap size="large" align="start" style={{ marginBottom: 16 }}>
                  <Space direction="vertical" size={4}>
                    <Typography.Text strong>Território:</Typography.Text>
                    <Select
                      showSearch
                      optionFilterProp="label"
                      style={{ minWidth: 280 }}
                      value={mapTerritoryFilter}
                      onChange={handleMapTerritoryFilterChange}
                      options={[
                        { value: 'all', label: 'Todos' },
                        ...activeTerritories.map((item) => ({
                          value: item.id,
                          label: `${item.nome} (${item.tipo_nome})`,
                        })),
                      ]}
                    />
                  </Space>
                  <Space direction="vertical" size={4}>
                    <Typography.Text strong>Exibir no mapa:</Typography.Text>
                    <Space wrap>
                      {MAP_MESH_LAYER_OPTIONS.map((option) => (
                        <Checkbox
                          key={option.value}
                          checked={mapLayerMode === option.value}
                          onChange={() => handleMapLayerModeChange(option.value)}
                        >
                          {option.label}
                        </Checkbox>
                      ))}
                      <Checkbox
                        checked={mapLayerMode === 'people'}
                        onChange={() => handleMapLayerModeChange('people')}
                      >
                        Localização pessoas
                      </Checkbox>
                    </Space>
                  </Space>
                </Space>
                {mapLayerMode !== 'people' && territoryShapes.isError ? (
                  <Typography.Text type="danger">
                    Não foi possível carregar as malhas territoriais. Selecione Localização pessoas
                    para visualizar os pontos no mapa.
                  </Typography.Text>
                ) : null}
                <MapContainer
                  key={`${mapLayerMode}-${mapCenter[0]}-${mapCenter[1]}`}
                  center={mapCenter}
                  zoom={mapLayerMode === 'people' && markers.data?.length ? 11 : 4}
                  style={{ height: 500, width: '100%', borderRadius: 8 }}
                >
                  <TileLayer
                    attribution="&copy; OpenStreetMap contributors"
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  {mapLayerMode !== 'people' ? (
                    <TerritoryMapShapes
                      shapes={territoryShapes.data ?? []}
                      onShapeClick={(territorioId) => navigate(`/territorios/${territorioId}`)}
                    />
                  ) : (
                    <PeopleLocationMarkers
                      markers={markers.data ?? []}
                      onSelectMarker={setSelectedMarker}
                    />
                  )}
                </MapContainer>
              </Card>
            ),
          },
          {
            key: 'types',
            label: 'Tipos',
            children: (
              <Card
                title="Tipos de território"
                extra={
                  isSaasManager && (
                    <Button icon={<PlusOutlined />} onClick={() => setTypeModalOpen(true)}>
                      Novo tipo
                    </Button>
                  )
                }
              >
                <Table
                  rowKey="id"
                  pagination={false}
                  dataSource={types.data ?? []}
                  columns={[
                    { title: 'Nome', dataIndex: 'nome' },
                    { title: 'Código', dataIndex: 'codigo' },
                    {
                      title: 'Origem',
                      dataIndex: 'tenant_id',
                      render: (value: number | null) => (value ? 'Tenant' : 'Sistema'),
                    },
                    {
                      title: 'Status',
                      dataIndex: 'ativo',
                      render: (value: boolean) => (value ? 'Ativo' : 'Inativo'),
                    },
                  ]}
                />
              </Card>
            ),
          },
        ]}
      />

      <Modal
        open={selectedMarker !== null}
        title="Pessoas nesta localização"
        footer={null}
        destroyOnClose
        onCancel={() => setSelectedMarker(null)}
      >
        <List
          loading={markerPeople.isPending}
          dataSource={markerPeople.data ?? []}
          locale={{ emptyText: 'Nenhuma pessoa encontrada nesta localização.' }}
          renderItem={(person) => (
            <List.Item
              actions={[
                <Link key="details" to={`/cadastro/pessoas/${person.id}`}>
                  Ver cadastro
                </Link>,
              ]}
            >
              <List.Item.Meta
                title={person.nome_completo}
                description={
                  [person.apelido, person.telefone, person.territorio]
                    .filter(Boolean)
                    .join(' • ') || 'Sem informações complementares'
                }
              />
            </List.Item>
          )}
        />
      </Modal>

      <Modal
        open={territoryModalOpen}
        title={selectedTerritory ? 'Editar território' : 'Novo território'}
        okText="Salvar"
        width={usesMeshDrawing ? 920 : 640}
        destroyOnClose
        transitionName=""
        maskTransitionName=""
        styles={{ body: { maxHeight: 'calc(100vh - 220px)', overflowY: 'auto' } }}
        confirmLoading={saveTerritory.isPending}
        afterOpenChange={(open) => {
          if (open) {
            window.setTimeout(() => setMeshEditorReady(true), 50);
          } else {
            setMeshEditorReady(false);
          }
        }}
        onCancel={() => setTerritoryModalOpen(false)}
        onOk={() => territoryForm.validateFields().then((values) => saveTerritory.mutate(values))}
      >
        <Form form={territoryForm} layout="vertical">
          <Form.Item name="id" hidden>
            <Input />
          </Form.Item>
          <Form.Item name="tipo_territorio_id" label="Tipo" rules={[{ required: true }]}>
            <Select
              onChange={() => {
                territoryForm.setFieldsValue({
                  codigo_uf_ibge: undefined,
                  codigo_municipio_ibge: undefined,
                  bairro_id: undefined,
                  bairro_selecao: undefined,
                  malha_geom: null,
                });
              }}
              options={(types.data ?? [])
                .filter((item) => item.ativo)
                .map((item) => ({ value: item.id, label: item.nome }))}
            />
          </Form.Item>
          {usesState ? (
            <Form.Item
              name="codigo_uf_ibge"
              label="Estado"
              rules={[{ required: true, message: 'Selecione o estado' }]}
            >
              <Select
                showSearch
                optionFilterProp="label"
                loading={states.isPending}
                placeholder="Selecione o estado"
                options={(states.data ?? []).map((state) => ({
                  value: state.codigo_ibge,
                  label: `${state.uf} - ${state.nome}`,
                }))}
                onChange={(stateCode) => {
                  const state = states.data?.find((item) => item.codigo_ibge === stateCode);
                  territoryForm.setFieldsValue({
                    codigo_municipio_ibge: undefined,
                    bairro_id: undefined,
                    bairro_selecao: undefined,
                    nome: isStateTerritory ? state?.nome : territoryForm.getFieldValue('nome'),
                  });
                }}
              />
            </Form.Item>
          ) : null}
          {isCityTerritory || isNeighborhoodTerritory ? (
            <Form.Item
              name="codigo_municipio_ibge"
              label="Município"
              rules={[{ required: true, message: 'Selecione o município' }]}
            >
              <Select
                showSearch
                optionFilterProp="label"
                disabled={!selectedStateCode}
                loading={cities.isFetching}
                placeholder={selectedStateCode ? 'Selecione o município' : 'Selecione o estado'}
                options={(cities.data ?? []).map((city) => ({
                  value: city.codigo_ibge,
                  label: city.nome,
                }))}
                onChange={(cityCode) => {
                  const city = cities.data?.find((item) => item.codigo_ibge === cityCode);
                  const municipalityTerritory = (territories.data ?? []).find(
                    (territory) =>
                      territory.ativo &&
                      territory.tipo_codigo === 'municipio' &&
                      territory.codigo_municipio_ibge === cityCode,
                  );
                  territoryForm.setFieldsValue({
                    bairro_id: undefined,
                    bairro_selecao: undefined,
                    nome: isCityTerritory ? city?.nome : territoryForm.getFieldValue('nome'),
                    territorio_pai_id: isNeighborhoodTerritory
                      ? municipalityTerritory?.id
                      : territoryForm.getFieldValue('territorio_pai_id'),
                  });
                }}
              />
            </Form.Item>
          ) : null}
          {isNeighborhoodTerritory ? (
            <Form.Item
              name="bairro_selecao"
              label="Bairro"
              rules={[
                { required: true, message: 'Selecione ou informe o bairro' },
                {
                  validator: async (_, value?: string) => {
                    if (value !== undefined && !value.trim()) {
                      throw new Error('Informe um nome válido para o bairro');
                    }
                  },
                },
              ]}
            >
              <AutoComplete
                disabled={!selectedCityCode}
                placeholder={
                  selectedCityCode ? 'Selecione ou digite um novo bairro' : 'Selecione o município'
                }
                options={(neighborhoods.data ?? []).map((neighborhood) => ({
                  value: neighborhood.nome,
                  label: neighborhood.nome,
                }))}
                filterOption={(inputValue, option) =>
                  normalizeSearch(String(option?.label ?? '')).includes(normalizeSearch(inputValue))
                }
                onChange={(neighborhoodName) => {
                  territoryForm.setFieldsValue({
                    bairro_id: undefined,
                    nome: neighborhoodName,
                  });
                }}
                onSelect={(neighborhoodName) => {
                  const neighborhood = neighborhoods.data?.find(
                    (item) => item.nome === neighborhoodName,
                  );
                  territoryForm.setFieldsValue({
                    bairro_id: neighborhood?.id,
                    nome: neighborhood?.nome,
                  });
                }}
              >
                <Input.Search loading={neighborhoods.isFetching} />
              </AutoComplete>
            </Form.Item>
          ) : null}
          <Form.Item name="nome" label="Nome" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="cor"
            label="Cor"
            rules={[{ required: true, message: 'Selecione uma cor' }]}
            getValueFromEvent={(color) => color.toHexString().toUpperCase()}
          >
            <ColorPicker disabledAlpha format="hex" showText />
          </Form.Item>
          <Form.Item name="territorio_pai_id" label="Território pai">
            <Select
              allowClear
              showSearch
              optionFilterProp="label"
              options={activeTerritories
                .filter((item) => item.id !== selectedTerritory?.id)
                .map((item) => ({ value: item.id, label: item.nome }))}
            />
          </Form.Item>
          {usesMeshDrawing ? (
            <Form.Item name="malha_geom" label="Malha geográfica" valuePropName="value">
              <TerritoryMeshEditor
                active={meshEditorReady}
                color={selectedColor}
                center={meshMapCenter}
                zoom={meshContextMunicipioIbge ? 13 : 4}
              />
            </Form.Item>
          ) : null}
        </Form>
      </Modal>

      <Modal
        open={typeModalOpen}
        title="Novo tipo territorial"
        okText="Criar"
        confirmLoading={createType.isPending}
        onCancel={() => setTypeModalOpen(false)}
        onOk={() => typeForm.validateFields().then((values) => createType.mutate(values))}
      >
        <Form form={typeForm} layout="vertical">
          <Form.Item name="nome" label="Nome" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="codigo"
            label="Código"
            rules={[
              { required: true },
              { pattern: /^[a-z0-9_]+$/, message: 'Use letras minúsculas, números e _.' },
            ]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="descricao" label="Descrição">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={leadershipModalOpen}
        title="Associar liderança ao território"
        okText="Associar"
        confirmLoading={linkLeader.isPending}
        onCancel={() => setLeadershipModalOpen(false)}
        onOk={() => leadershipForm.validateFields().then((values) => linkLeader.mutate(values))}
      >
        <Form form={leadershipForm} layout="vertical">
          <Form.Item name="territorio_id" label="Território" rules={[{ required: true }]}>
            <Select
              disabled
              options={activeTerritories.map((item) => ({
                value: item.id,
                label: item.nome,
              }))}
            />
          </Form.Item>
          <Form.Item name="lideranca_id" label="Liderança" rules={[{ required: true }]}>
            <Select
              showSearch
              optionFilterProp="label"
              options={(leaders.data ?? []).map((item) => {
                const nome = item.pessoa_nome_completo || `Liderança #${item.id}`;
                return {
                  value: item.id,
                  label: item.apelido_campanha ? `${nome} (${item.apelido_campanha})` : nome,
                };
              })}
            />
          </Form.Item>
          <Form.Item name="responsabilidade" label="Responsabilidade" initialValue="principal">
            <Select
              options={[
                { value: 'principal', label: 'Principal' },
                { value: 'apoio', label: 'Apoio' },
                { value: 'compartilhada', label: 'Compartilhada' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
