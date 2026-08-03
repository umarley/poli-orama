import { Button, Space, Typography } from 'antd';
import L from 'leaflet';
import { useEffect, useMemo, useState } from 'react';
import {
  CircleMarker,
  MapContainer,
  Polygon,
  Polyline,
  TileLayer,
  useMap,
  useMapEvents,
} from 'react-leaflet';

import type { TerritorioMalhaGeometry } from '@/modules/territorios/types';

import 'leaflet/dist/leaflet.css';

type LatLngTuple = [number, number];

interface TerritoryMeshEditorProps {
  value?: TerritorioMalhaGeometry | null;
  onChange?: (geometry: TerritorioMalhaGeometry | null) => void;
  color: string;
  center?: LatLngTuple;
  zoom?: number;
  active?: boolean;
}

function geometryToLatLngs(geometry: TerritorioMalhaGeometry): LatLngTuple[] {
  if (geometry.type === 'Polygon') {
    const ring = geometry.coordinates[0] as number[][];
    return ring.slice(0, -1).map(([lng, lat]) => [lat, lng]);
  }
  const firstPolygon = geometry.coordinates[0] as number[][][];
  const ring = firstPolygon[0];
  return ring.slice(0, -1).map(([lng, lat]) => [lat, lng]);
}

function latLngsToPolygon(points: LatLngTuple[]): TerritorioMalhaGeometry {
  const ring = points.map(([lat, lng]) => [lng, lat]);
  const first = ring[0];
  const last = ring[ring.length - 1];
  if (first[0] !== last[0] || first[1] !== last[1]) {
    ring.push(first);
  }
  return {
    type: 'Polygon',
    coordinates: [ring],
  };
}

function MapLayoutFix({
  center,
  zoom,
  geometry,
  isDrawing,
}: {
  center: LatLngTuple;
  zoom: number;
  geometry?: TerritorioMalhaGeometry | null;
  isDrawing: boolean;
}) {
  const map = useMap();

  useEffect(() => {
    const invalidate = () => {
      map.invalidateSize({ animate: false, pan: false });
    };

    invalidate();
    const timers = [0, 100, 300, 600].map((delay) => window.setTimeout(invalidate, delay));

    const container = map.getContainer();
    const observer =
      typeof ResizeObserver !== 'undefined'
        ? new ResizeObserver(() => invalidate())
        : null;
    observer?.observe(container);

    const intersectionObserver =
      typeof IntersectionObserver !== 'undefined'
        ? new IntersectionObserver(
            (entries) => {
              if (entries.some((entry) => entry.isIntersecting)) invalidate();
            },
            { threshold: 0.1 },
          )
        : null;
    intersectionObserver?.observe(container);

    let scrollParent: HTMLElement | null = container.parentElement;
    while (scrollParent) {
      const style = window.getComputedStyle(scrollParent);
      if (style.overflowY === 'auto' || style.overflowY === 'scroll') break;
      scrollParent = scrollParent.parentElement;
    }
    scrollParent?.addEventListener('scroll', invalidate, { passive: true });

    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
      observer?.disconnect();
      intersectionObserver?.disconnect();
      scrollParent?.removeEventListener('scroll', invalidate);
    };
  }, [map, isDrawing]);

  useEffect(() => {
    map.setView(center, zoom, { animate: false });
    const timer = window.setTimeout(() => map.invalidateSize({ animate: false, pan: false }), 0);
    return () => window.clearTimeout(timer);
  }, [center, map, zoom]);

  useEffect(() => {
    if (!geometry) return;
    const bounds = L.geoJSON(geometry).getBounds();
    if (!bounds.isValid()) return;
    map.fitBounds(bounds, { padding: [24, 24], animate: false });
    const timer = window.setTimeout(() => map.invalidateSize({ animate: false, pan: false }), 0);
    return () => window.clearTimeout(timer);
  }, [geometry, map]);

  return null;
}

function DrawClickHandler({
  enabled,
  onPoint,
}: {
  enabled: boolean;
  onPoint: (point: LatLngTuple) => void;
}) {
  useMapEvents({
    click(event) {
      if (!enabled) return;
      onPoint([event.latlng.lat, event.latlng.lng]);
    },
  });
  return null;
}

export function TerritoryMeshEditor({
  value,
  onChange,
  color,
  center = [-15.78, -47.93],
  zoom = 12,
  active = true,
}: TerritoryMeshEditorProps) {
  const [draftPoints, setDraftPoints] = useState<LatLngTuple[]>([]);
  const [isDrawing, setIsDrawing] = useState(false);

  const applyChange = (geometry: TerritorioMalhaGeometry | null) => {
    onChange?.(geometry);
  };

  const savedPoints = useMemo(
    () => (value ? geometryToLatLngs(value) : []),
    [value],
  );

  const displayPoints = isDrawing ? draftPoints : savedPoints;
  const canFinish = isDrawing && draftPoints.length >= 3;

  const startDrawing = () => {
    setDraftPoints(savedPoints);
    setIsDrawing(true);
  };

  const finishDrawing = () => {
    if (draftPoints.length < 3) return;
    applyChange(latLngsToPolygon(draftPoints));
    setIsDrawing(false);
    setDraftPoints([]);
  };

  const clearDrawing = () => {
    setDraftPoints([]);
    setIsDrawing(false);
    applyChange(null);
  };

  return (
    <div>
      <Space wrap style={{ marginBottom: 8 }}>
        {!isDrawing ? (
          <Button type="primary" onClick={startDrawing} disabled={!active}>
            {value ? 'Redesenhar malha' : 'Desenhar malha'}
          </Button>
        ) : (
          <>
            <Button type="primary" disabled={!canFinish} onClick={finishDrawing}>
              Concluir polígono
            </Button>
            <Button onClick={() => setIsDrawing(false)}>Cancelar</Button>
          </>
        )}
        {value || isDrawing ? (
          <Button danger onClick={clearDrawing}>
            Limpar malha
          </Button>
        ) : null}
      </Space>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 8 }}>
        {!active
          ? 'Carregando mapa...'
          : isDrawing
            ? 'Clique no mapa para adicionar vértices. Mínimo de 3 pontos para concluir.'
            : 'Desenhe o limite territorial clicando no mapa para definir os vértices do polígono.'}
      </Typography.Paragraph>
      <div
        className="territory-mesh-editor-map"
        style={{ height: 320, width: '100%', borderRadius: 8, overflow: 'hidden' }}
      >
        {active ? (
          <MapContainer
            key={`territory-mesh-map-${center[0]}-${center[1]}-${zoom}`}
            center={center}
            zoom={zoom}
            scrollWheelZoom
            style={{ height: '100%', width: '100%', minHeight: 320 }}
          >
          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapLayoutFix center={center} zoom={zoom} geometry={value} isDrawing={isDrawing} />
          <DrawClickHandler
            enabled={isDrawing}
            onPoint={(point) => setDraftPoints((current) => [...current, point])}
          />
          {displayPoints.length >= 2 ? (
            <Polyline
              positions={displayPoints}
              pathOptions={{ color, weight: 2, dashArray: isDrawing ? '6 4' : undefined }}
            />
          ) : null}
          {displayPoints.length >= 3 && !isDrawing ? (
            <Polygon
              positions={displayPoints}
              pathOptions={{
                color,
                fillColor: color,
                fillOpacity: 0.25,
                weight: 2,
              }}
            />
          ) : null}
          {isDrawing
            ? displayPoints.map((point, index) => (
                <CircleMarker
                  key={`${point[0]}-${point[1]}-${index}`}
                  center={point}
                  radius={6}
                  pathOptions={{ color, fillColor: color, fillOpacity: 0.95, weight: 2 }}
                />
              ))
            : null}
        </MapContainer>
        ) : (
          <div
            style={{
              height: '100%',
              width: '100%',
              background: '#f7f8fa',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#8c8c8c',
            }}
          >
            Preparando mapa...
          </div>
        )}
      </div>
    </div>
  );
}
