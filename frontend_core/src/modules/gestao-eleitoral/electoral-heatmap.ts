import type { MapPoint } from './types';

export interface HeatGradient {
  [stop: number]: string;
}

export interface ElectoralHeatSeries {
  key: string;
  label: string;
  color: string;
  gradient: HeatGradient;
  votos: number;
  latLngs: Array<[number, number, number]>;
  maxIntensity: number;
}

const PALETTES: Array<{ color: string; gradient: HeatGradient }> = [
  {
    color: '#1677ff',
    gradient: { 0.2: '#91caff', 0.45: '#4096ff', 0.7: '#1677ff', 1: '#003eb3' },
  },
  {
    color: '#f5222d',
    gradient: { 0.2: '#ffa39e', 0.45: '#ff4d4f', 0.7: '#cf1322', 1: '#820014' },
  },
  {
    color: '#52c41a',
    gradient: { 0.2: '#b7eb8f', 0.45: '#73d13d', 0.7: '#389e0d', 1: '#092b00' },
  },
  {
    color: '#fa8c16',
    gradient: { 0.2: '#ffd591', 0.45: '#ffa940', 0.7: '#d46b08', 1: '#873800' },
  },
  {
    color: '#722ed1',
    gradient: { 0.2: '#d3adf7', 0.45: '#9254de', 0.7: '#531dab', 1: '#22075e' },
  },
  {
    color: '#13c2c2',
    gradient: { 0.2: '#87e8de', 0.45: '#36cfc9', 0.7: '#006d75', 1: '#002329' },
  },
  {
    color: '#eb2f96',
    gradient: { 0.2: '#ffadd2', 0.45: '#f759ab', 0.7: '#9e1068', 1: '#520339' },
  },
  {
    color: '#fadb14',
    gradient: { 0.2: '#fff1b8', 0.45: '#ffec3d', 0.7: '#d4b106', 1: '#614700' },
  },
];

function pointCandidate(point: MapPoint): string {
  return point.candidato?.trim() || (point.candidatos.length === 1 ? point.candidatos[0] : '');
}

export function buildElectoralHeatSeries(
  points: MapPoint[],
  selectedNames: string[] = [],
): ElectoralHeatSeries[] {
  const grouped = new Map<string, MapPoint[]>();
  points.forEach((point) => {
    const key = pointCandidate(point);
    const current = grouped.get(key) ?? [];
    current.push(point);
    grouped.set(key, current);
  });

  const orderedKeys = [
    ...selectedNames.filter((name) => grouped.has(name)),
    ...[...grouped.keys()].filter((key) => key && !selectedNames.includes(key)),
  ];
  if (grouped.has('') && !orderedKeys.includes('')) {
    orderedKeys.push('');
  }

  return orderedKeys.map((key, index) => {
    const palette = PALETTES[index % PALETTES.length];
    const seriesPoints = grouped.get(key) ?? [];
    const votos = seriesPoints.reduce((total, point) => total + point.votos, 0);
    const maxIntensity = Math.max(...seriesPoints.map((point) => point.votos), 1);
    return {
      key: key || 'recorte',
      label: key || 'Votos do recorte',
      color: palette.color,
      gradient: palette.gradient,
      votos,
      maxIntensity,
      latLngs: seriesPoints.map((point) => [point.latitude, point.longitude, point.votos]),
    };
  });
}

export function markerRadiusForVotes(votos: number, maxVotos: number): number {
  if (maxVotos <= 0 || votos <= 0) return 7;
  return Math.round(7 + Math.sqrt(votos / maxVotos) * 18);
}

export interface ElectoralSectionMarker {
  id: string;
  latitude: number;
  longitude: number;
  color: string;
  radius: number;
  point: MapPoint;
}

export function buildSectionMarkers(
  points: MapPoint[],
  selectedNames: string[] = [],
): ElectoralSectionMarker[] {
  const series = buildElectoralHeatSeries(points, selectedNames);
  const colorByKey = new Map(series.map((item) => [item.key, item.color]));
  const maxVotes = Math.max(...points.map((point) => point.votos), 1);
  const occupancy = new Map<string, number>();
  const totals = new Map<string, number>();
  points.forEach((point) => {
    const key = `${point.latitude.toFixed(6)}|${point.longitude.toFixed(6)}`;
    totals.set(key, (totals.get(key) ?? 0) + 1);
  });

  return points
    .map((point, index) => {
      const candidateKey =
        point.candidato?.trim() || point.candidatos[0] || 'recorte';
      const geoKey = `${point.latitude.toFixed(6)}|${point.longitude.toFixed(6)}`;
      const total = totals.get(geoKey) ?? 1;
      const offsetIndex = occupancy.get(geoKey) ?? 0;
      occupancy.set(geoKey, offsetIndex + 1);
      const angle = total > 1 ? (2 * Math.PI * offsetIndex) / total : 0;
      const spread = total > 1 ? 0.0004 : 0;
      return {
        id: `${candidateKey}-${point.zona}-${point.secao}-${index}`,
        latitude: point.latitude + Math.sin(angle) * spread,
        longitude: point.longitude + Math.cos(angle) * spread,
        color: colorByKey.get(candidateKey) ?? series[0]?.color ?? '#1677ff',
        radius: markerRadiusForVotes(point.votos, maxVotes),
        point,
      };
    })
    .sort((left, right) => left.point.votos - right.point.votos);
}
