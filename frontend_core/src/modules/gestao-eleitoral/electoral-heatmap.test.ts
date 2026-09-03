import { describe, expect, it } from 'vitest';

import { buildElectoralHeatSeries, buildSectionMarkers, markerRadiusForVotes } from './electoral-heatmap';
import type { MapPoint } from './types';

function point(partial: Partial<MapPoint> & Pick<MapPoint, 'candidato' | 'votos'>): MapPoint {
  return {
    latitude: -16.68,
    longitude: -49.25,
    zona: 1,
    secao: 10,
    local_votacao: 'Escola',
    municipio: 'Goiânia',
    percentual: 0,
    candidatos: partial.candidato ? [partial.candidato] : [],
    ...partial,
  };
}

describe('buildElectoralHeatSeries', () => {
  it('separa os pontos por candidato e preserva a ordem da seleção', () => {
    const series = buildElectoralHeatSeries(
      [
        point({ candidato: 'Bruno', votos: 10, latitude: -16.7 }),
        point({ candidato: 'Ana', votos: 40 }),
        point({ candidato: 'Ana', votos: 10, longitude: -49.3 }),
      ],
      ['Ana', 'Bruno'],
    );

    expect(series.map((item) => item.label)).toEqual(['Ana', 'Bruno']);
    expect(series[0].votos).toBe(50);
    expect(series[0].color).not.toBe(series[1].color);
    expect(series[0].latLngs).toHaveLength(2);
    expect(series[0].maxIntensity).toBe(40);
  });
});

describe('markerRadiusForVotes', () => {
  it('aumenta o marker conforme a quantidade de votos', () => {
    expect(markerRadiusForVotes(100, 100)).toBeGreaterThan(markerRadiusForVotes(25, 100));
    expect(markerRadiusForVotes(0, 100)).toBe(7);
  });
});

describe('buildSectionMarkers', () => {
  it('usa cor distinta por candidato e desloca pontos no mesmo local', () => {
    const markers = buildSectionMarkers(
      [
        point({ candidato: 'Ana', votos: 80, secao: 10 }),
        point({ candidato: 'Bruno', votos: 20, secao: 10 }),
      ],
      ['Ana', 'Bruno'],
    );

    expect(markers).toHaveLength(2);
    expect(markers[0].color).not.toBe(markers[1].color);
    expect(markers.some((item) => item.latitude !== -16.68 || item.longitude !== -49.25)).toBe(true);
    expect(markers[1].radius).toBeGreaterThan(markers[0].radius);
  });
});
