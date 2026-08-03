import { ArrowLeftOutlined, PrinterOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Card, Descriptions, Space, Spin, Table, Tag, Typography } from 'antd';
import L from 'leaflet';
import { useEffect, useMemo, useState } from 'react';
import { GeoJSON, MapContainer, TileLayer, useMap } from 'react-leaflet';
import { Link, useNavigate, useParams } from 'react-router-dom';

import 'leaflet/dist/leaflet.css';

import { AppToast } from '@/components/feedback/AppToast';
import { PageHeader } from '@/components/layout/PageHeader';
import { obterDetalhesTerritorio } from '@/modules/territorios/territorios-service';
import { generateTerritoryReportPdf } from '@/modules/territorios/territory-report-pdf';
import type { TerritorioDetalhe } from '@/modules/territorios/types';
import { normalizeApiError } from '@/services/api/api-error';
import { formatInteger } from '@/utils/number-format';

function formatPhone(value: string | null | undefined): string {
  if (!value) return '—';
  const digits = value.replace(/\D/g, '');
  const localDigits = digits.startsWith('55') && digits.length > 11 ? digits.slice(2) : digits;
  if (localDigits.length === 10) {
    return `(${localDigits.slice(0, 2)}) ${localDigits.slice(2, 6)}-${localDigits.slice(6)}`;
  }
  if (localDigits.length === 11) {
    return `(${localDigits.slice(0, 2)}) ${localDigits.slice(2, 7)}-${localDigits.slice(7)}`;
  }
  return value;
}

type LeafletGeoJson = React.ComponentProps<typeof GeoJSON>['data'];

type TerritoryMapShape = {
  cor: string;
  geometry: NonNullable<TerritorioDetalhe['geometry']>;
};

function TerritoryShapeMap({ shape }: { shape: TerritoryMapShape }) {
  const map = useMap();
  const collection = useMemo(
    () => ({
      type: 'FeatureCollection' as const,
      features: [
        {
          type: 'Feature' as const,
          properties: { cor: shape.cor },
          geometry: shape.geometry,
        },
      ],
    }),
    [shape],
  );

  useEffect(() => {
    const bounds = L.geoJSON(collection as LeafletGeoJson).getBounds();
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [24, 24] });
  }, [collection, map]);

  return (
    <GeoJSON
      data={collection as LeafletGeoJson}
      style={{
        color: shape.cor,
        fillColor: shape.cor,
        fillOpacity: 0.25,
        opacity: 0.95,
        weight: 2,
      }}
    />
  );
}

export function TerritorioDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const territoryId = Number(id);
  const [printing, setPrinting] = useState(false);

  const detail = useQuery({
    queryKey: ['territorios', territoryId, 'detalhes'],
    queryFn: () => obterDetalhesTerritorio(territoryId),
    enabled: Number.isInteger(territoryId) && territoryId > 0,
  });

  if (detail.error) {
    return <Alert type="error" showIcon message={normalizeApiError(detail.error).message} />;
  }

  const item = detail.data;
  const isMunicipio = item?.tipo_codigo === 'municipio';
  const isEstado = item?.tipo_codigo === 'estado';
  const hasCustomMeshType = ['bairro', 'microrregiao', 'comunidade', 'area_personalizada'].includes(
    item?.tipo_codigo ?? '',
  );
  const shape: TerritoryMapShape | null = item?.geometry
    ? { cor: item.cor, geometry: item.geometry }
    : null;

  const handlePrintReport = async () => {
    if (!item) return;
    setPrinting(true);
    try {
      await generateTerritoryReportPdf({ detail: item });
      AppToast.success('Relatório gerado em PDF.');
    } catch (error) {
      AppToast.error(normalizeApiError(error).message || 'Não foi possível gerar o relatório.');
    } finally {
      setPrinting(false);
    }
  };

  return (
    <Spin spinning={detail.isPending}>
      <PageHeader
        title={item?.territorio_nome ?? 'Território'}
        description="Detalhes territoriais, indicadores demográficos e pessoas vinculadas."
        breadcrumbs={[
          { label: 'Início', to: '/dashboard' },
          { label: 'Territórios', to: '/territorios?aba=mapa' },
          { label: item?.territorio_nome ?? 'Detalhes' },
        ]}
        actions={
          <Space wrap>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/territorios?aba=mapa')}>
              Voltar ao mapa
            </Button>
            <Button
              type="primary"
              icon={<PrinterOutlined />}
              loading={printing}
              disabled={!item}
              onClick={() => void handlePrintReport()}
            >
              Imprimir relatório
            </Button>
          </Space>
        }
      />

      <Card title="Mapa do território" style={{ marginBottom: 16 }}>
        {shape ? (
          <MapContainer
            center={[-15.78, -47.93]}
            zoom={4}
            style={{ height: 420, width: '100%', borderRadius: 8 }}
          >
            <TileLayer
              attribution="&copy; OpenStreetMap contributors"
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <TerritoryShapeMap shape={shape} />
          </MapContainer>
        ) : (
          <Typography.Text type="secondary">
            {hasCustomMeshType
              ? 'Este território ainda não possui malha geográfica desenhada.'
              : 'Este território não possui malha geográfica disponível para exibição.'}
          </Typography.Text>
        )}
      </Card>

      <Card
        title={isEstado ? 'Dados do estado' : isMunicipio ? 'Dados do município' : 'Indicadores'}
        style={{ marginBottom: 16 }}
      >
        <Descriptions bordered column={{ xs: 1, sm: 2, md: 3 }} size="small">
          <Descriptions.Item label="Território">
            <Space>
              <Tag color={item?.cor}>{item?.territorio_nome}</Tag>
              <Typography.Text type="secondary">{item?.tipo_nome}</Typography.Text>
            </Space>
          </Descriptions.Item>
          {isMunicipio ? (
            <Descriptions.Item label="Município">
              {item?.municipio_nome ?? '—'}
              {item?.uf ? ` / ${item.uf}` : ''}
            </Descriptions.Item>
          ) : null}
          <Descriptions.Item label="Estado">
            {item?.estado_nome ?? '—'}
            {item?.uf && !isMunicipio ? ` (${item.uf})` : ''}
          </Descriptions.Item>
          <Descriptions.Item label="Total de habitantes">
            {item?.habitantes != null ? formatInteger(item.habitantes) : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="Total de eleitores">
            {formatInteger(item?.quantidade_eleitores ?? 0)}
          </Descriptions.Item>
          <Descriptions.Item label="Pessoas vinculadas">
            {formatInteger(item?.quantidade_pessoas ?? 0)}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {isMunicipio && (item?.pessoas?.length ?? 0) > 0 ? (
        <Card title="Pessoas vinculadas">
          <Table
            rowKey="id"
            pagination={{
              pageSize: 10,
              showTotal: (total) => `${formatInteger(total)} pessoa(s)`,
            }}
            dataSource={item?.pessoas ?? []}
            columns={[
              {
                title: 'Nome',
                dataIndex: 'nome_completo',
                render: (value: string, record) => (
                  <Link to={`/cadastro/pessoas/${record.id}`}>{value}</Link>
                ),
              },
              {
                title: 'Telefone / WhatsApp',
                dataIndex: 'telefone',
                render: (value: string | null) => formatPhone(value),
              },
              {
                title: 'E-mail',
                dataIndex: 'email',
                render: (value: string | null) => value ?? '—',
              },
              {
                title: 'Papel',
                dataIndex: 'papel',
                render: (value: string) => <Tag>{value}</Tag>,
              },
            ]}
          />
        </Card>
      ) : null}
    </Spin>
  );
}
