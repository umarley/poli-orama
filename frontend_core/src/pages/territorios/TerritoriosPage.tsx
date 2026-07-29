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
import { useMemo, useState } from 'react';
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet';
import { Link } from 'react-router-dom';
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
  vincularLideranca,
} from '@/modules/territorios/territorios-service';
import type {
  MapMarker,
  Territorio,
  TerritorioInput,
  TerritorioTreeNode,
} from '@/modules/territorios/types';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';
import { formatInteger } from '@/utils/number-format';

interface TerritoryForm extends TerritorioInput {
  id?: number;
  bairro_selecao?: string;
}

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

const initialTerritoryFilters: TerritoryFilters = { name: '' };

function normalizeSearch(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR');
}

function toTreeData(nodes: TerritorioTreeNode[]): DataNode[] {
  return nodes.map((node) => ({
    key: node.id,
    title: (
      <Space>
        <span>{node.nome}</span>
        <Tag>{node.tipo_nome}</Tag>
      </Space>
    ),
    children: toTreeData(node.filhos),
  }));
}

export function TerritoriosPage() {
  const queryClient = useQueryClient();
  const permissions = useSessionStore((state) => state.user?.permissions ?? []);
  const profiles = useSessionStore((state) => state.user?.profiles ?? []);
  const canCreate = permissions.includes('territorio.criar');
  const canEdit = permissions.includes('territorio.editar');
  const canDelete = permissions.includes('territorio.excluir');
  const isSaasManager = profiles.includes('gestor_saas');
  const [territoryModalOpen, setTerritoryModalOpen] = useState(false);
  const [typeModalOpen, setTypeModalOpen] = useState(false);
  const [leadershipModalOpen, setLeadershipModalOpen] = useState(false);
  const [selectedTerritory, setSelectedTerritory] = useState<Territorio | null>(null);
  const [mapTerritoryId, setMapTerritoryId] = useState<number>();
  const [selectedMarker, setSelectedMarker] = useState<MapMarker | null>(null);
  const [territoryFilters, setTerritoryFilters] =
    useState<TerritoryFilters>(initialTerritoryFilters);
  const [territoryForm] = Form.useForm<TerritoryForm>();
  const [typeForm] = Form.useForm<{ codigo: string; nome: string; descricao?: string }>();
  const [leadershipForm] = Form.useForm<LeadershipForm>();
  const selectedTerritoryTypeId = Form.useWatch('tipo_territorio_id', territoryForm);
  const selectedStateCode = Form.useWatch('codigo_uf_ibge', territoryForm);
  const selectedCityCode = Form.useWatch('codigo_municipio_ibge', territoryForm);

  const territories = useQuery({
    queryKey: ['territorios'],
    queryFn: () => listarTerritorios(true),
  });
  const types = useQuery({
    queryKey: ['territorios', 'tipos'],
    queryFn: () => listarTiposTerritorio(true),
  });
  const selectedTerritoryType = types.data?.find(
    (item) => item.id === selectedTerritoryTypeId,
  );
  const isStateTerritory = selectedTerritoryType?.codigo === 'estado';
  const isCityTerritory = selectedTerritoryType?.codigo === 'municipio';
  const isNeighborhoodTerritory = selectedTerritoryType?.codigo === 'bairro';
  const usesState = isStateTerritory || isCityTerritory || isNeighborhoodTerritory;
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
    queryKey: ['territorios', 'mapa', mapTerritoryId],
    queryFn: () => obterMarcadores(mapTerritoryId),
  });
  const markerPeople = useQuery({
    queryKey: [
      'territorios',
      'mapa',
      'pessoas',
      selectedMarker?.latitude,
      selectedMarker?.longitude,
      mapTerritoryId,
    ],
    queryFn: () =>
      listarPessoasNoMarcador(selectedMarker!.latitude, selectedMarker!.longitude, mapTerritoryId),
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
      const payload = { ...basePayload, bairro_id: neighborhoodId };
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

  const openCreate = () => {
    setSelectedTerritory(null);
    territoryForm.resetFields();
    setTerritoryModalOpen(true);
  };

  const openEdit = (territory: Territorio) => {
    setSelectedTerritory(territory);
    territoryForm.setFieldsValue({
      id: territory.id,
      nome: territory.nome,
      tipo_territorio_id: territory.tipo_territorio_id,
      territorio_pai_id: territory.territorio_pai_id ?? undefined,
      codigo_uf_ibge: territory.codigo_uf_ibge ?? undefined,
      codigo_municipio_ibge: territory.codigo_municipio_ibge ?? undefined,
      bairro_id: territory.bairro_id ?? undefined,
      bairro_selecao: territory.bairro_id ? territory.nome : undefined,
      zona_eleitoral_id: territory.zona_eleitoral_id ?? undefined,
      secao_eleitoral_id: territory.secao_eleitoral_id ?? undefined,
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
                  <Tree defaultExpandAll treeData={treeData} showLine />
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
              <Card
                title="Pessoas georreferenciadas"
                extra={
                  <Select
                    allowClear
                    placeholder="Todos os territórios"
                    style={{ width: 260 }}
                    value={mapTerritoryId}
                    onChange={setMapTerritoryId}
                    options={activeTerritories.map((item) => ({
                      value: item.id,
                      label: item.nome,
                    }))}
                  />
                }
              >
                <MapContainer
                  key={`${mapCenter[0]}-${mapCenter[1]}`}
                  center={mapCenter}
                  zoom={markers.data?.length ? 11 : 4}
                  style={{ height: 500, width: '100%', borderRadius: 8 }}
                >
                  <TileLayer
                    attribution="&copy; OpenStreetMap contributors"
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  {(markers.data ?? []).map((marker) => (
                    <CircleMarker
                      key={`${marker.latitude}-${marker.longitude}`}
                      center={[Number(marker.latitude), Number(marker.longitude)]}
                      radius={Math.min(24, 7 + Math.log2(marker.quantidade + 1) * 3)}
                    >
                      <Popup>
                        <Space direction="vertical" size={2}>
                          <span>
                            {formatInteger(marker.quantidade)} pessoa(s) nesta localização
                          </span>
                          <Button
                            type="link"
                            size="small"
                            style={{ padding: 0 }}
                            onClick={() => setSelectedMarker(marker)}
                          >
                            Ver pessoas
                          </Button>
                        </Space>
                      </Popup>
                    </CircleMarker>
                  ))}
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
        confirmLoading={saveTerritory.isPending}
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
                  selectedCityCode
                    ? 'Selecione ou digite um novo bairro'
                    : 'Selecione o município'
                }
                options={(neighborhoods.data ?? []).map((neighborhood) => ({
                  value: neighborhood.nome,
                  label: neighborhood.nome,
                }))}
                filterOption={(inputValue, option) =>
                  normalizeSearch(String(option?.label ?? '')).includes(
                    normalizeSearch(inputValue),
                  )
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
              options={(leaders.data ?? []).map((item) => ({
                value: item.id,
                label: item.apelido_campanha || `Liderança #${item.id}`,
              }))}
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
