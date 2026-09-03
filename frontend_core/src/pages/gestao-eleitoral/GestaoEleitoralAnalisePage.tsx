import {
  BankOutlined,
  BarChartOutlined,
  ClearOutlined,
  EnvironmentOutlined,
  GlobalOutlined,
  TeamOutlined,
  TrophyOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  Progress,
  Radio,
  Row,
  Select,
  Space,
  Spin,
  Tabs,
  Typography,
} from 'antd';
import L from 'leaflet';
import { useEffect, useMemo, useState } from 'react';
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet';
import { Link, useSearchParams } from 'react-router-dom';
import 'leaflet/dist/leaflet.css';

import { BaseTable } from '@/components/data/BaseTable';
import { LocalizedStatistic as Statistic } from '@/components/data/LocalizedStatistic';
import { PageHeader } from '@/components/layout/PageHeader';
import { buildElectoralHeatSeries, buildSectionMarkers } from '@/modules/gestao-eleitoral/electoral-heatmap';
import {
  getElectoralDistribution,
  getElectoralMap,
  getElectoralPanel,
  listElectoralElections,
  listElectoralMunicipalities,
  listElectoralOffices,
  listElectoralPollingPlaces,
  listElectoralSections,
  listElectoralStates,
  listElectoralZones,
  omitElectoralFilters,
  searchElectoralCandidates,
} from '@/modules/gestao-eleitoral/gestao-eleitoral-service';
import type {
  DistributionDimension,
  DistributionItem,
  ElectoralFilters,
  MapMode,
  MapPoint,
  MapView,
  RankingItem,
} from '@/modules/gestao-eleitoral/types';
import { normalizeApiError } from '@/services/api/api-error';
import { formatInteger, formatPercent } from '@/utils/number-format';

import { ElectoralHeatmapLayers } from './ElectoralHeatmapLayers';
import styles from './GestaoEleitoralPage.module.css';

const emptyFilters: ElectoralFilters = {};

function hasItems<T>(value?: T[]) {
  return Boolean(value?.length);
}

function electionLabel(item: {
  ds_eleicao: string | null;
  aa_eleicao: number | null;
  nr_turno: number | null;
  nm_tipo_eleicao: string | null;
}) {
  const name = item.ds_eleicao?.trim() || `Eleição ${item.aa_eleicao ?? ''}`.trim();
  const turn = item.nr_turno ? `${item.nr_turno}º turno` : null;
  const kind = item.nm_tipo_eleicao?.trim();
  return [name, turn, kind].filter(Boolean).join(' · ');
}

function rankingTitle(cargos?: string[]) {
  if (!cargos?.length) return 'Ranking por cargo';
  if (cargos.length === 1) return `Ranking · ${cargos[0]}`;
  return `Ranking · ${cargos.length} cargos`;
}

function MapFitBounds({ points }: { points: MapPoint[] }) {
  const map = useMap();
  useEffect(() => {
    if (!points.length) return;
    const bounds = L.latLngBounds(points.map((point) => [point.latitude, point.longitude]));
    map.fitBounds(bounds.pad(0.12), { maxZoom: 14 });
  }, [map, points]);
  return null;
}

function distributionLabel(item: DistributionItem) {
  return item.candidato ? `${item.rotulo} · ${item.candidato}` : item.rotulo;
}

function DistributionBars({ items }: { items: DistributionItem[] }) {
  if (!items.length) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Sem dados no recorte." />;
  return (
    <div className={styles.bars}>
      {items.map((item) => {
        const label = distributionLabel(item);
        return (
          <div key={item.chave} className={styles.barRow}>
            <div className={styles.barLabel}>
              <Typography.Text ellipsis={{ tooltip: label }}>{label}</Typography.Text>
              <span>
                {formatInteger(item.votos)} · {formatPercent(item.percentual)}
              </span>
            </div>
            <Progress percent={item.percentual} showInfo={false} />
          </div>
        );
      })}
    </div>
  );
}

export function GestaoEleitoralAnalisePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = searchParams.get('aba') ?? 'visao';
  const [filters, setFilters] = useState<ElectoralFilters>(emptyFilters);
  const [candidateQuery, setCandidateQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [mapMode, setMapMode] = useState<MapMode>('secao');
  const [mapView, setMapView] = useState<MapView>('calor');
  const [tableDimension, setTableDimension] = useState<DistributionDimension>('municipio');
  const [tablePage, setTablePage] = useState(1);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(candidateQuery.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [candidateQuery]);

  const updateFilters = (patch: ElectoralFilters, clear: Array<keyof ElectoralFilters> = []) => {
    setFilters((current) => {
      const next = { ...current, ...patch };
      (Object.entries(patch) as Array<[keyof ElectoralFilters, unknown]>).forEach(([key, value]) => {
        if (Array.isArray(value) && value.length === 0) delete next[key];
      });
      clear.forEach((key) => {
        delete next[key];
      });
      return next;
    });
    setTablePage(1);
  };
  const electionSelected = hasItems(filters.eleicao_chaves);
  const mapAggregation: MapMode = mapView === 'secao' ? 'secao' : mapMode;

  const elections = useQuery({
    queryKey: ['gestao-eleitoral', 'eleicoes'],
    queryFn: listElectoralElections,
  });
  const officeFilters = omitElectoralFilters(filters, 'ds_cargo', 'nm_votaveis');
  const stateFilters = omitElectoralFilters(
    filters,
    'sg_uf',
    'cd_municipio',
    'nr_zona',
    'nr_local_votacao',
    'nr_secao',
  );
  const municipalityFilters = omitElectoralFilters(
    filters,
    'cd_municipio',
    'nr_zona',
    'nr_local_votacao',
    'nr_secao',
  );
  const zoneFilters = omitElectoralFilters(filters, 'nr_zona', 'nr_local_votacao', 'nr_secao');
  const placeFilters = omitElectoralFilters(filters, 'nr_local_votacao', 'nr_secao');
  const sectionFilters = omitElectoralFilters(filters, 'nr_secao');

  const offices = useQuery({
    queryKey: ['gestao-eleitoral', 'cargos', officeFilters],
    queryFn: () => listElectoralOffices(officeFilters),
    enabled: electionSelected,
  });
  const candidates = useQuery({
    queryKey: ['gestao-eleitoral', 'candidatos', filters, debouncedQuery],
    queryFn: () => searchElectoralCandidates(filters, debouncedQuery),
    enabled: electionSelected && debouncedQuery.length >= 2,
  });
  const states = useQuery({
    queryKey: ['gestao-eleitoral', 'estados', stateFilters],
    queryFn: () => listElectoralStates(stateFilters),
    enabled: electionSelected,
  });
  const municipalities = useQuery({
    queryKey: ['gestao-eleitoral', 'municipios', municipalityFilters],
    queryFn: () => listElectoralMunicipalities(municipalityFilters),
    enabled: electionSelected && hasItems(filters.sg_uf),
  });
  const zones = useQuery({
    queryKey: ['gestao-eleitoral', 'zonas', zoneFilters],
    queryFn: () => listElectoralZones(zoneFilters),
    enabled: electionSelected && (hasItems(filters.sg_uf) || hasItems(filters.cd_municipio)),
  });
  const places = useQuery({
    queryKey: ['gestao-eleitoral', 'locais', placeFilters],
    queryFn: () => listElectoralPollingPlaces(placeFilters),
    enabled: hasItems(filters.cd_municipio) || hasItems(filters.nr_zona),
  });
  const sections = useQuery({
    queryKey: ['gestao-eleitoral', 'secoes', sectionFilters],
    queryFn: () => listElectoralSections(sectionFilters),
    enabled: hasItems(filters.nr_zona) || hasItems(filters.nr_local_votacao),
  });
  const panel = useQuery({
    queryKey: ['gestao-eleitoral', 'painel', filters],
    queryFn: () => getElectoralPanel(filters),
    enabled: electionSelected,
  });
  const mapData = useQuery({
    queryKey: ['gestao-eleitoral', 'mapa', filters, mapAggregation],
    queryFn: () => getElectoralMap(filters, mapAggregation),
    enabled: electionSelected && tab === 'mapa' && hasItems(filters.nm_votaveis),
  });
  const table = useQuery({
    queryKey: ['gestao-eleitoral', 'tabela', tableDimension, filters, tablePage],
    queryFn: () => getElectoralDistribution(tableDimension, filters, tablePage, 20),
    enabled: electionSelected && tab === 'tabelas',
  });

  const selectedElectionKeys = filters.eleicao_chaves ?? [];
  const candidateOptions = useMemo(() => {
    const searched = candidates.data ?? [];
    const selected = (filters.nm_votaveis ?? []).map((name) => ({
      value: name,
      label: name,
    }));
    const merged = new Map(selected.map((item) => [item.value, item]));
    searched.forEach((item) => {
      merged.set(item.nm_votavel, { value: item.nm_votavel, label: item.nm_votavel });
    });
    return [...merged.values()];
  }, [candidates.data, filters.nm_votaveis]);

  const panelError = panel.error ? normalizeApiError(panel.error).message : null;
  const data = panel.data;
  const mapPoints = mapData.data?.pontos ?? [];
  const heatSeries = useMemo(
    () => buildElectoralHeatSeries(mapPoints, filters.nm_votaveis ?? []),
    [mapPoints, filters.nm_votaveis],
  );
  const sectionMarkers = useMemo(
    () => buildSectionMarkers(mapPoints, filters.nm_votaveis ?? []),
    [mapPoints, filters.nm_votaveis],
  );
  const candidateSelected = hasItems(filters.nm_votaveis);

  return (
    <div className={styles.page}>
      <PageHeader
        title="Análise de resultados"
        description="Combine eleição, candidatos e território para comparar o desempenho e orientar a estratégia."
        breadcrumbs={[
          { label: 'Início', to: '/dashboard' },
          { label: 'Gestão eleitoral', to: '/gestao-eleitoral' },
          { label: 'Análise de resultados' },
        ]}
        actions={
          <Button icon={<ClearOutlined />} onClick={() => setFilters(emptyFilters)}>
            Limpar filtros
          </Button>
        }
      />

      <Card title="Filtros" size="small">
        <div className={styles.filters}>
          <Select
            mode="multiple"
            showSearch
            allowClear
            maxTagCount="responsive"
            optionFilterProp="label"
            placeholder="Eleição e turno"
            loading={elections.isFetching}
            status={elections.isError ? 'error' : undefined}
            value={selectedElectionKeys}
            options={(elections.data ?? []).map((item) => ({
              value: item.chave,
              label: electionLabel(item),
            }))}
            onChange={(value: string[]) => {
              if (!value.length) {
                setFilters(emptyFilters);
                return;
              }
              updateFilters({ eleicao_chaves: value }, [
                'ds_cargo',
                'nm_votaveis',
                'sg_uf',
                'cd_municipio',
                'nr_zona',
                'nr_local_votacao',
                'nr_secao',
              ]);
            }}
          />
          <Select
            mode="multiple"
            showSearch
            allowClear
            maxTagCount="responsive"
            optionFilterProp="label"
            placeholder="Cargo disputado"
            disabled={!electionSelected}
            value={filters.ds_cargo}
            options={(offices.data ?? []).map((item) => ({ value: item.valor, label: item.rotulo }))}
            onChange={(value: string[]) => updateFilters({ ds_cargo: value }, ['nm_votaveis'])}
          />
          <Select
            mode="multiple"
            showSearch
            allowClear
            maxTagCount="responsive"
            filterOption={false}
            placeholder="Pesquisar candidatos"
            disabled={!electionSelected}
            value={filters.nm_votaveis}
            options={candidateOptions}
            onSearch={setCandidateQuery}
            onChange={(value: string[]) => updateFilters({ nm_votaveis: value })}
            notFoundContent={
              debouncedQuery.length < 2 ? 'Digite ao menos 2 letras' : 'Nenhum candidato encontrado'
            }
          />
          <Select
            mode="multiple"
            showSearch
            allowClear
            maxTagCount="responsive"
            optionFilterProp="label"
            placeholder="Estado"
            disabled={!electionSelected}
            value={filters.sg_uf}
            options={(states.data ?? []).map((item) => ({ value: item.valor, label: item.rotulo }))}
            onChange={(value: string[]) =>
              updateFilters({ sg_uf: value }, ['cd_municipio', 'nr_zona', 'nr_local_votacao', 'nr_secao'])
            }
          />
          <Select
            mode="multiple"
            showSearch
            allowClear
            maxTagCount="responsive"
            optionFilterProp="label"
            placeholder="Município"
            disabled={!hasItems(filters.sg_uf)}
            value={filters.cd_municipio}
            options={(municipalities.data ?? []).map((item) => ({
              value: item.valor,
              label: item.rotulo,
            }))}
            onChange={(value: number[]) =>
              updateFilters({ cd_municipio: value }, ['nr_zona', 'nr_local_votacao', 'nr_secao'])
            }
          />
          <Select
            mode="multiple"
            showSearch
            allowClear
            maxTagCount="responsive"
            optionFilterProp="label"
            placeholder="Zona eleitoral"
            disabled={!hasItems(filters.sg_uf) && !hasItems(filters.cd_municipio)}
            value={filters.nr_zona}
            options={(zones.data ?? []).map((item) => ({ value: item.valor, label: item.rotulo }))}
            onChange={(value: number[]) =>
              updateFilters({ nr_zona: value }, ['nr_local_votacao', 'nr_secao'])
            }
          />
          <Select
            mode="multiple"
            showSearch
            allowClear
            maxTagCount="responsive"
            optionFilterProp="label"
            placeholder="Local de votação"
            disabled={!hasItems(filters.cd_municipio) && !hasItems(filters.nr_zona)}
            value={filters.nr_local_votacao}
            options={(places.data ?? []).map((item) => ({ value: item.valor, label: item.rotulo }))}
            onChange={(value: number[]) => updateFilters({ nr_local_votacao: value }, ['nr_secao'])}
          />
          <Select
            mode="multiple"
            showSearch
            allowClear
            maxTagCount="responsive"
            optionFilterProp="label"
            placeholder="Seção eleitoral"
            disabled={!hasItems(filters.nr_zona) && !hasItems(filters.nr_local_votacao)}
            value={filters.nr_secao}
            options={(sections.data ?? []).map((item) => ({ value: item.valor, label: item.rotulo }))}
            onChange={(value: number[]) => updateFilters({ nr_secao: value })}
          />
        </div>
      </Card>

      {elections.isError && (
        <Alert
          type="error"
          showIcon
          message="Não foi possível carregar as eleições."
          description={normalizeApiError(elections.error).message}
        />
      )}
      {!electionSelected && (
        <Alert
          type="info"
          showIcon
          message="Selecione uma eleição para carregar o painel."
          description="Os filtros seguintes e as visualizações usam apenas os dados agregados do recorte escolhido."
        />
      )}
      {panelError && <Alert type="error" showIcon message={panelError} />}

      <Tabs
        activeKey={tab}
        onChange={(key) => {
          const next = new URLSearchParams(searchParams);
          if (key === 'visao') next.delete('aba');
          else next.set('aba', key);
          setSearchParams(next, { replace: true });
        }}
        items={[
          {
            key: 'visao',
            label: 'Visão geral',
            children: (
              <Space direction="vertical" size={16} style={{ width: '100%' }}>
                <Row gutter={[16, 16]}>
                  <Col xs={24} sm={12} lg={8} xl={4}>
                    <Card className={styles.summaryCard}>
                      <span className={`${styles.summaryIcon} ${styles.blue}`}>
                        <BarChartOutlined />
                      </span>
                      <Statistic
                        title="Total de votos"
                        value={data?.indicadores.total_votos ?? 0}
                        formatter={(value) => formatInteger(Number(value))}
                      />
                    </Card>
                  </Col>
                  <Col xs={24} sm={12} lg={8} xl={4}>
                    <Card className={styles.summaryCard}>
                      <span className={`${styles.summaryIcon} ${styles.purple}`}>
                        <TeamOutlined />
                      </span>
                      <Statistic title="Candidatos" value={data?.indicadores.candidatos ?? 0} />
                    </Card>
                  </Col>
                  <Col xs={24} sm={12} lg={8} xl={4}>
                    <Card className={styles.summaryCard}>
                      <span className={`${styles.summaryIcon} ${styles.green}`}>
                        <BankOutlined />
                      </span>
                      <Statistic title="Municípios" value={data?.indicadores.municipios ?? 0} />
                    </Card>
                  </Col>
                  <Col xs={24} sm={12} lg={8} xl={4}>
                    <Card className={styles.summaryCard}>
                      <span className={`${styles.summaryIcon} ${styles.orange}`}>
                        <GlobalOutlined />
                      </span>
                      <Statistic title="Zonas" value={data?.indicadores.zonas ?? 0} />
                    </Card>
                  </Col>
                  <Col xs={24} sm={12} lg={8} xl={4}>
                    <Card className={styles.summaryCard}>
                      <span className={`${styles.summaryIcon} ${styles.blue}`}>
                        <EnvironmentOutlined />
                      </span>
                      <Statistic title="Locais" value={data?.indicadores.locais ?? 0} />
                    </Card>
                  </Col>
                  <Col xs={24} sm={12} lg={8} xl={4}>
                    <Card className={styles.summaryCard}>
                      <span className={`${styles.summaryIcon} ${styles.green}`}>
                        <TrophyOutlined />
                      </span>
                      <Statistic title="Seções" value={data?.indicadores.secoes ?? 0} />
                    </Card>
                  </Col>
                </Row>
                {hasItems(filters.ds_cargo) && (
                  <Card
                    title={rankingTitle(filters.ds_cargo)}
                    extra={<Link to="/gestao-eleitoral/analise?aba=ranking">Ver completo</Link>}
                  >
                    <RankingTable
                      items={data?.ranking ?? []}
                      loading={panel.isFetching}
                      emptyText="Nenhum candidato encontrado neste recorte."
                    />
                  </Card>
                )}
                {(data?.comparativo.length ?? 0) > 0 && (
                  <Card title="Comparativo entre candidatos selecionados">
                    <DistributionBars
                      items={(data?.comparativo ?? []).map((item) => ({
                        chave: item.nm_votavel,
                        rotulo: item.nm_votavel,
                        municipio: null,
                        zona: null,
                        local_votacao: null,
                        secao: null,
                        candidato: null,
                        votos: item.votos,
                        percentual: item.percentual,
                      }))}
                    />
                  </Card>
                )}
                <Row gutter={[16, 16]}>
                  <Col xs={24} lg={12}>
                    <Card title="Votos por município">
                      <DistributionBars items={data?.por_municipio ?? []} />
                    </Card>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Card title="Votos por zona">
                      <DistributionBars items={data?.por_zona ?? []} />
                    </Card>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Card title="Votos por local">
                      <DistributionBars items={data?.por_local ?? []} />
                    </Card>
                  </Col>
                  <Col xs={24} lg={12}>
                    <Card title="Votos por seção">
                      <DistributionBars items={data?.por_secao ?? []} />
                    </Card>
                  </Col>
                </Row>
              </Space>
            ),
          },
          {
            key: 'mapa',
            label: 'Mapa',
            children: (
              <Card
                title={mapView === 'calor' ? 'Mapa de calor da votação' : 'Mapa por seção eleitoral'}
                extra={
                  <Space wrap size={8}>
                    <Radio.Group
                      value={mapView}
                      onChange={(event) => setMapView(event.target.value)}
                      optionType="button"
                      options={[
                        { value: 'calor', label: 'Mapa de calor' },
                        { value: 'secao', label: 'Mapa por seção eleitoral' },
                      ]}
                    />
                    {mapView === 'calor' && (
                      <Radio.Group
                        value={mapMode}
                        onChange={(event) => setMapMode(event.target.value)}
                        optionType="button"
                        options={[
                          { value: 'secao', label: 'Votos por seção' },
                          { value: 'zona', label: 'Votos por zona' },
                        ]}
                      />
                    )}
                  </Space>
                }
              >
                {mapData.data?.truncado && (
                  <Alert
                    style={{ marginBottom: 12 }}
                    type="warning"
                    showIcon
                    message="O mapa exibe os locais com maior votação do recorte. Aplique filtros para ver um detalhamento completo."
                  />
                )}
                {!electionSelected ? (
                  <Empty description="Selecione uma eleição para ver o mapa." />
                ) : !candidateSelected ? (
                  <Empty
                    description={
                      mapView === 'calor'
                        ? 'Selecione um ou mais candidatos para plotar o mapa de calor da votação.'
                        : 'Selecione um ou mais candidatos para ver os pontos por seção eleitoral.'
                    }
                  />
                ) : !mapPoints.length && mapData.isFetching ? (
                  <Spin spinning>
                    <div className={styles.mapWrap} />
                  </Spin>
                ) : !mapPoints.length ? (
                  <Empty description="Não há coordenadas para os locais de votação deste recorte." />
                ) : (
                  <div className={styles.mapWrap}>
                    <MapContainer
                      key={mapView}
                      center={[-15.78, -47.93]}
                      zoom={4}
                      style={{ height: '100%', width: '100%' }}
                    >
                      <TileLayer
                        attribution="&copy; OpenStreetMap contributors"
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                      />
                      <MapFitBounds points={mapPoints} />
                      {mapView === 'calor' ? (
                        <ElectoralHeatmapLayers series={heatSeries} mapMode={mapAggregation} />
                      ) : (
                        sectionMarkers.map((marker) => (
                          <CircleMarker
                            key={marker.id}
                            center={[marker.latitude, marker.longitude]}
                            radius={marker.radius}
                            pathOptions={{
                              color: marker.color,
                              fillColor: marker.color,
                              fillOpacity: 0.72,
                              weight: 1.5,
                            }}
                          >
                            <Popup>
                              <Space direction="vertical" size={2}>
                                <strong>{marker.point.municipio ?? 'Município não informado'}</strong>
                                <span>
                                  Candidato:{' '}
                                  {marker.point.candidato
                                    ?? marker.point.candidatos[0]
                                    ?? 'Não informado'}
                                </span>
                                <span>Zona eleitoral: {marker.point.zona ?? '—'}</span>
                                <span>Seção: {marker.point.secao ?? '—'}</span>
                                <span>Local: {marker.point.local_votacao ?? '—'}</span>
                                <span>Votos: {formatInteger(marker.point.votos)}</span>
                                <span>
                                  Participação do candidato: {formatPercent(marker.point.percentual)}
                                </span>
                              </Space>
                            </Popup>
                          </CircleMarker>
                        ))
                      )}
                    </MapContainer>
                    {heatSeries.length > 0 && (
                      <div className={styles.heatLegend}>
                        {heatSeries.map((item) => (
                          <div key={item.key} className={styles.heatLegendItem}>
                            <span
                              className={styles.heatLegendSwatch}
                              style={{ background: item.color }}
                            />
                            <Typography.Text ellipsis={{ tooltip: item.label }}>
                              {item.label}
                            </Typography.Text>
                            <span>{formatInteger(item.votos)} votos</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </Card>
            ),
          },
          {
            key: 'ranking',
            label: 'Ranking',
            children: (
              <Card title={rankingTitle(filters.ds_cargo)}>
                {!hasItems(filters.ds_cargo) ? (
                  <Empty description="Selecione um ou mais cargos disputados para ver o ranking dos candidatos." />
                ) : (
                  <RankingTable
                    items={data?.ranking ?? []}
                    loading={panel.isFetching}
                    emptyText="Nenhum candidato encontrado neste recorte."
                  />
                )}
              </Card>
            ),
          },
          {
            key: 'tabelas',
            label: 'Tabelas',
            children: (
              <Card
                title="Detalhamento"
                extra={
                  <Select
                    value={tableDimension}
                    style={{ minWidth: 200 }}
                    onChange={(value) => {
                      setTableDimension(value);
                      setTablePage(1);
                    }}
                    options={[
                      { value: 'municipio', label: 'Por município' },
                      { value: 'zona', label: 'Por zona' },
                      { value: 'local', label: 'Por local de votação' },
                      { value: 'secao', label: 'Por seção' },
                    ]}
                  />
                }
              >
                <BaseTable<DistributionItem>
                  rowKey="chave"
                  loading={table.isFetching}
                  dataSource={table.data?.items ?? []}
                  pagination={{
                    current: tablePage,
                    pageSize: 20,
                    total: table.data?.total ?? 0,
                    onChange: setTablePage,
                    showSizeChanger: false,
                  }}
                  columns={[
                    { title: 'Local', dataIndex: 'rotulo', sorter: (a, b) => a.rotulo.localeCompare(b.rotulo) },
                    { title: 'Município', dataIndex: 'municipio', render: (value: string | null) => value ?? '—' },
                    { title: 'Zona', dataIndex: 'zona', render: (value: number | null) => value ?? '—' },
                    { title: 'Seção', dataIndex: 'secao', render: (value: number | null) => value ?? '—' },
                    {
                      title: 'Votos',
                      dataIndex: 'votos',
                      sorter: (a, b) => a.votos - b.votos,
                      defaultSortOrder: 'descend',
                      render: (value: number) => formatInteger(value),
                    },
                    {
                      title: '% recorte',
                      dataIndex: 'percentual',
                      sorter: (a, b) => a.percentual - b.percentual,
                      render: (value: number) => formatPercent(value),
                    },
                  ]}
                />
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
}

function RankingTable({
  items,
  loading,
  emptyText,
}: {
  items: RankingItem[];
  loading: boolean;
  emptyText?: string;
}) {
  return (
    <BaseTable
      rowKey={(row) => `${row.posicao}-${row.nm_votavel}`}
      loading={loading}
      dataSource={items}
      locale={emptyText ? { emptyText } : undefined}
      pagination={{ pageSize: 15, showSizeChanger: false }}
      columns={[
        { title: 'Posição', dataIndex: 'posicao', width: 90 },
        { title: 'Candidato', dataIndex: 'nm_votavel' },
        {
          title: 'Partido',
          dataIndex: 'partido',
          render: (value: string | null) => value ?? '—',
        },
        {
          title: 'Votos',
          dataIndex: 'votos',
          render: (value: number) => formatInteger(value),
        },
        {
          title: '% no recorte',
          dataIndex: 'percentual',
          render: (value: number) => formatPercent(value),
        },
        {
          title: 'Diferença p/ anterior',
          dataIndex: 'diferenca_votos',
          render: (value: number | null) => (value === null ? '—' : formatInteger(value)),
        },
      ]}
    />
  );
}
