import L from 'leaflet';
import { useCallback, useEffect, useMemo } from 'react';
import { GeoJSON, useMap, useMapEvents } from 'react-leaflet';

import { formatInteger } from '@/utils/number-format';

export interface MapBounds {
  south: number;
  west: number;
  north: number;
  east: number;
}

export interface ElectoralZoneCandidateVotes {
  candidato: string;
  votos: number;
}

export interface ElectoralZoneMesh {
  id: number;
  numero_zona: number;
  municipio: string | null;
  quantidade_locais: number;
  quantidade_secoes?: number;
  total_votos?: number;
  candidatos?: ElectoralZoneCandidateVotes[];
  geometry: {
    type: 'Polygon';
    coordinates: number[][][];
  };
}

const colors = [
  '#1677ff',
  '#722ed1',
  '#13a8a8',
  '#389e0d',
  '#d48806',
  '#cf1322',
  '#c41d7f',
  '#08979c',
];

export const ELECTORAL_ZONE_LEGEND_COLOR = colors[1];

type LeafletGeoJson = React.ComponentProps<typeof GeoJSON>['data'];

function popupContent(properties: Record<string, unknown>) {
  const content = document.createElement('div');
  const title = document.createElement('strong');
  const municipality = document.createElement('div');
  const pollingPlaces = document.createElement('div');
  title.textContent = `Zona Eleitoral ${String(properties.numero_zona ?? '')}`;
  municipality.textContent = `Município: ${String(properties.municipio ?? 'Não informado')}`;
  pollingPlaces.textContent = `Locais de votação: ${formatInteger(Number(properties.quantidade_locais ?? 0))}`;
  content.append(title, municipality, pollingPlaces);

  if (properties.quantidade_secoes !== undefined) {
    const sections = document.createElement('div');
    sections.textContent = `Seções eleitorais: ${formatInteger(Number(properties.quantidade_secoes))}`;
    content.append(sections);
  }
  if (properties.total_votos !== undefined) {
    const votes = document.createElement('div');
    votes.style.marginTop = '6px';
    votes.textContent = `Votos na zona: ${formatInteger(Number(properties.total_votos))}`;
    content.append(votes);
  }
  const candidates = properties.candidatos as ElectoralZoneCandidateVotes[] | undefined;
  candidates?.forEach((candidate) => {
    const row = document.createElement('div');
    row.textContent = `${candidate.candidato}: ${formatInteger(candidate.votos)} votos`;
    content.append(row);
  });
  return content;
}

export function MapViewportReporter({ onChange }: { onChange: (bounds: MapBounds) => void }) {
  const map = useMap();
  const report = useCallback(() => {
    const bounds = map.getBounds();
    onChange({
      south: bounds.getSouth(),
      west: bounds.getWest(),
      north: bounds.getNorth(),
      east: bounds.getEast(),
    });
  }, [map, onChange]);
  useMapEvents({ moveend: report });
  useEffect(report, [report]);
  return null;
}

export function ElectoralZoneMeshes({ zones }: { zones: ElectoralZoneMesh[] }) {
  const collection = useMemo(
    () => ({
      type: 'FeatureCollection' as const,
      features: zones.map((zone) => ({
        type: 'Feature' as const,
        properties: {
          ...zone,
          geometry: undefined,
          color: colors[zone.id % colors.length],
        },
        geometry: zone.geometry,
      })),
    }),
    [zones],
  );

  if (!zones.length) return null;

  return (
    <GeoJSON
      key={zones.map((zone) => zone.id).join('-')}
      data={collection as LeafletGeoJson}
      style={(feature) => {
        const color = String(feature?.properties?.color ?? colors[0]);
        return { color, fillColor: color, fillOpacity: 0.14, opacity: 0.85, weight: 2 };
      }}
      onEachFeature={(feature, layer) => {
        layer.bindPopup(popupContent(feature.properties ?? {}));
        const pathLayer = layer as L.Path;
        pathLayer.on('mouseover', () => pathLayer.setStyle({ weight: 3, fillOpacity: 0.24 }));
        pathLayer.on('mouseout', () => {
          const color = String(feature.properties?.color ?? colors[0]);
          pathLayer.setStyle({
            color,
            fillColor: color,
            fillOpacity: 0.14,
            opacity: 0.85,
            weight: 2,
          });
        });
      }}
    />
  );
}
