import { L } from '@/lib/leaflet-global';
import 'leaflet.heat';
import { useEffect } from 'react';
import { useMap } from 'react-leaflet';

import type { ElectoralHeatSeries } from '@/modules/gestao-eleitoral/electoral-heatmap';
import type { MapMode } from '@/modules/gestao-eleitoral/types';

interface ElectoralHeatmapLayersProps {
  series: ElectoralHeatSeries[];
  mapMode: MapMode;
}

export function ElectoralHeatmapLayers({ series, mapMode }: ElectoralHeatmapLayersProps) {
  const map = useMap();

  useEffect(() => {
    const radius = mapMode === 'zona' ? 48 : 32;
    const blur = mapMode === 'zona' ? 36 : 24;
    const layers = series
      .filter((item) => item.latLngs.length > 0)
      .map((item) =>
        L.heatLayer(item.latLngs, {
          radius,
          blur,
          max: item.maxIntensity,
          maxZoom: 6,
          minOpacity: 0.4,
          gradient: item.gradient,
        }).addTo(map),
      );

    return () => {
      layers.forEach((layer) => map.removeLayer(layer));
    };
  }, [map, mapMode, series]);

  return null;
}
