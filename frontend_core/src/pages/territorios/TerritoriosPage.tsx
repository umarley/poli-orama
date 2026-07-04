import {
  ApartmentOutlined,
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  Form,
  Input,
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
import 'leaflet/dist/leaflet.css';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import { listarLiderancas } from '@/modules/cadastro/pessoas-service';
import {
  atualizarTerritorio,
  criarTerritorio,
  criarTipoTerritorio,
  inativarTerritorio,
  listarArvoreTerritorial,
  listarTerritorios,
  listarTiposTerritorio,
  obterMarcadores,
  vincularLideranca,
} from '@/modules/territorios/territorios-service';
import type {
  Territorio,
  TerritorioInput,
  TerritorioTreeNode,
} from '@/modules/territorios/types';
import { normalizeApiError } from '@/services/api/api-error';
import { useSessionStore } from '@/stores/session-store';

interface TerritoryForm extends TerritorioInput {
  id?: number;
}

interface LeadershipForm {
  territorio_id: number;
  lideranca_id: number;
  responsabilidade: 'principal' | 'apoio' | 'compartilhada';
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
  const canCreate = permissions.includes('territorio.criar');
  const canEdit = permissions.includes('territorio.editar');
  const canDelete = permissions.includes('territorio.excluir');
  const [territoryModalOpen, setTerritoryModalOpen] = useState(false);
  const [typeModalOpen, setTypeModalOpen] = useState(false);
  const [leadershipModalOpen, setLeadershipModalOpen] = useState(false);
  const [selectedTerritory, setSelectedTerritory] = useState<Territorio | null>(null);
  const [mapTerritoryId, setMapTerritoryId] = useState<number>();
  const [territoryForm] = Form.useForm<TerritoryForm>();
  const [typeForm] = Form.useForm<{ codigo: string; nome: string; descricao?: string }>();
  const [leadershipForm] = Form.useForm<LeadershipForm>();

  const territories = useQuery({
    queryKey: ['territorios'],
    queryFn: () => listarTerritorios(true),
  });
  const types = useQuery({
    queryKey: ['territorios', 'tipos'],
    queryFn: () => listarTiposTerritorio(true),
  });
  const tree = useQuery({
    queryKey: ['territorios', 'arvore'],
    queryFn: listarArvoreTerritorial,
  });
  const leaders = useQuery({
    queryKey: ['cadastro', 'liderancas'],
    queryFn: listarLiderancas,
  });
  const markers = useQuery({
    queryKey: ['territorios', 'mapa', mapTerritoryId],
    queryFn: () => obterMarcadores(mapTerritoryId),
  });

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['territorios'] }),
      queryClient.invalidateQueries({ queryKey: ['cadastro', 'liderancas'] }),
    ]);
  };

  const saveTerritory = useMutation({
    mutationFn: (values: TerritoryForm) => {
      const { id, ...payload } = values;
      return id ? atualizarTerritorio(id, payload) : criarTerritorio(payload);
    },
    onSuccess: async () => {
      AppToast.success(selectedTerritory ? 'Território atualizado.' : 'Território criado.');
      setTerritoryModalOpen(false);
      setSelectedTerritory(null);
      territoryForm.resetFields();
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
      vincularLideranca(
        values.territorio_id,
        values.lideranca_id,
        values.responsabilidade,
      ),
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
                <Table<Territorio>
                  rowKey="id"
                  loading={territories.isPending}
                  dataSource={territories.data ?? []}
                  pagination={{ pageSize: 10 }}
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
                      <Popup>{marker.quantidade} pessoa(s) nesta localização</Popup>
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
                  canCreate && (
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
          <Form.Item name="nome" label="Nome" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item
            name="tipo_territorio_id"
            label="Tipo"
            rules={[{ required: true }]}
          >
            <Select
              options={(types.data ?? [])
                .filter((item) => item.ativo)
                .map((item) => ({ value: item.id, label: item.nome }))}
            />
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
        onOk={() =>
          leadershipForm.validateFields().then((values) => linkLeader.mutate(values))
        }
      >
        <Form form={leadershipForm} layout="vertical">
          <Form.Item name="territorio_id" label="Território" rules={[{ required: true }]}>
            <Select
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
          <Form.Item
            name="responsabilidade"
            label="Responsabilidade"
            initialValue="principal"
          >
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
