import { jsPDF } from 'jspdf';

import type { TerritorioDetalhe, TerritorioPessoaVinculada } from './types';
import { formatInteger } from '@/utils/number-format';

interface TerritoryReportPdfInput {
  detail: TerritorioDetalhe;
}

const notInformed = 'Não informado';

type Ring = number[][];
type PolygonCoords = Ring[];
type MultiPolygonCoords = PolygonCoords[];

function filename(name: string) {
  const safe = name
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9]+/g, '-');
  return `relatorio-territorio-${safe.replace(/^-|-$/g, '').toLowerCase()}.pdf`;
}

function generatedAtLabel() {
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'long',
    timeStyle: 'short',
  }).format(new Date());
}

function parseHexColor(hex: string): { r: number; g: number; b: number } {
  const normalized = hex.trim().replace('#', '');
  if (normalized.length === 3) {
    return {
      r: Number.parseInt(normalized[0] + normalized[0], 16),
      g: Number.parseInt(normalized[1] + normalized[1], 16),
      b: Number.parseInt(normalized[2] + normalized[2], 16),
    };
  }
  if (normalized.length >= 6) {
    return {
      r: Number.parseInt(normalized.slice(0, 2), 16),
      g: Number.parseInt(normalized.slice(2, 4), 16),
      b: Number.parseInt(normalized.slice(4, 6), 16),
    };
  }
  return { r: 24, g: 67, b: 108 };
}

function collectRings(geometry: NonNullable<TerritorioDetalhe['geometry']>): Ring[] {
  if (geometry.type === 'Polygon') {
    return geometry.coordinates as PolygonCoords;
  }
  return (geometry.coordinates as MultiPolygonCoords).flat();
}

function computeBounds(rings: Ring[]) {
  let minLng = Infinity;
  let maxLng = -Infinity;
  let minLat = Infinity;
  let maxLat = -Infinity;

  for (const ring of rings) {
    for (const [lng, lat] of ring) {
      minLng = Math.min(minLng, lng);
      maxLng = Math.max(maxLng, lng);
      minLat = Math.min(minLat, lat);
      maxLat = Math.max(maxLat, lat);
    }
  }

  return { minLng, maxLng, minLat, maxLat };
}

function computeGeoMetrics(bounds: ReturnType<typeof computeBounds>) {
  const lngSpan = Math.max(bounds.maxLng - bounds.minLng, 0.0001);
  const latSpan = Math.max(bounds.maxLat - bounds.minLat, 0.0001);
  const midLat = (bounds.minLat + bounds.maxLat) / 2;
  const lngSpanAtMidLat = lngSpan * Math.cos((midLat * Math.PI) / 180);
  const aspectRatio = lngSpanAtMidLat / latSpan;

  return { lngSpan, latSpan, midLat, lngSpanAtMidLat, aspectRatio };
}

interface GeometryImageResult {
  dataUrl: string;
  aspectRatio: number;
}

function renderGeometryImage(
  geometry: NonNullable<TerritorioDetalhe['geometry']>,
  color: string,
  maxWidth = 960,
  maxHeight = 540,
): GeometryImageResult | null {
  const rings = collectRings(geometry);
  if (rings.length === 0) return null;

  const bounds = computeBounds(rings);
  const { latSpan, midLat, lngSpanAtMidLat, aspectRatio } = computeGeoMetrics(bounds);
  const padding = 36;

  let width = maxWidth;
  let height = maxWidth / aspectRatio;
  if (height > maxHeight) {
    height = maxHeight;
    width = maxHeight * aspectRatio;
  }
  width = Math.max(Math.round(width), 1);
  height = Math.max(Math.round(height), 1);

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  const { r, g, b } = parseHexColor(color);
  const cosMidLat = Math.cos((midLat * Math.PI) / 180);
  const drawWidth = width - padding * 2;
  const drawHeight = height - padding * 2;
  const scale = Math.min(drawWidth / lngSpanAtMidLat, drawHeight / latSpan);
  const offsetX = padding + (drawWidth - lngSpanAtMidLat * scale) / 2;
  const offsetY = padding + (drawHeight - latSpan * scale) / 2;

  ctx.fillStyle = '#f7f8fa';
  ctx.fillRect(0, 0, width, height);

  const project = (lng: number, lat: number) => {
    const x = offsetX + (lng - bounds.minLng) * cosMidLat * scale;
    const y = offsetY + (bounds.maxLat - lat) * scale;
    return { x, y };
  };

  for (const ring of rings) {
    if (ring.length === 0) continue;
    ctx.beginPath();
    const first = project(ring[0][0], ring[0][1]);
    ctx.moveTo(first.x, first.y);
    for (let index = 1; index < ring.length; index += 1) {
      const point = project(ring[index][0], ring[index][1]);
      ctx.lineTo(point.x, point.y);
    }
    ctx.closePath();
    ctx.fillStyle = `rgba(${r}, ${g}, ${b}, 0.28)`;
    ctx.fill();
    ctx.strokeStyle = `rgb(${r}, ${g}, ${b})`;
    ctx.lineWidth = 2;
    ctx.stroke();
  }

  return { dataUrl: canvas.toDataURL('image/png'), aspectRatio: width / height };
}

function fitImageSize(
  aspectRatio: number,
  maxWidth: number,
  maxHeight: number,
): { width: number; height: number } {
  let width = maxWidth;
  let height = width / aspectRatio;
  if (height > maxHeight) {
    height = maxHeight;
    width = height * aspectRatio;
  }
  return { width, height };
}

function formatPhone(value: string | null | undefined): string {
  if (!value) return notInformed;
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

export async function generateTerritoryReportPdf(
  input: TerritoryReportPdfInput,
  options: { download?: boolean } = {},
) {
  const { detail } = input;
  const pdf = new jsPDF({ unit: 'mm', format: 'a4' });
  const width = pdf.internal.pageSize.getWidth();
  const height = pdf.internal.pageSize.getHeight();
  const margin = 15;
  const contentWidth = width - margin * 2;
  let y = 16;

  const ensureSpace = (needed: number) => {
    if (y + needed <= height - 18) return;
    pdf.addPage();
    y = 16;
  };

  const sectionTitle = (title: string) => {
    ensureSpace(12);
    pdf.setFillColor(238, 244, 250);
    pdf.roundedRect(margin, y, contentWidth, 8, 1.5, 1.5, 'F');
    pdf.setTextColor(24, 67, 108);
    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(10);
    pdf.text(title.toUpperCase(), margin + 3, y + 5.4);
    pdf.setTextColor(35, 35, 35);
    y += 11;
  };

  const field = (label: string, value: string, fieldWidth = contentWidth / 2 - 2) => {
    ensureSpace(12);
    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(7.5);
    pdf.setTextColor(90, 90, 90);
    pdf.text(label.toUpperCase(), margin, y);
    pdf.setFont('helvetica', 'normal');
    pdf.setFontSize(9.5);
    pdf.setTextColor(30, 30, 30);
    const lines = pdf.splitTextToSize(value || notInformed, fieldWidth);
    pdf.text(lines, margin, y + 4.5);
    y += 4.5 + lines.length * 4.2 + 2.5;
  };

  const isMunicipio = detail.tipo_codigo === 'municipio';
  const isEstado = detail.tipo_codigo === 'estado';

  pdf.setFillColor(24, 67, 108);
  pdf.rect(0, 0, width, 31, 'F');
  pdf.setTextColor(255, 255, 255);
  pdf.setFont('helvetica', 'bold');
  pdf.setFontSize(17);
  pdf.text('RELATÓRIO DO TERRITÓRIO', margin, 14);
  pdf.setFont('helvetica', 'normal');
  pdf.setFontSize(9);
  pdf.text(detail.territorio_nome, margin, 21);
  pdf.text(`Gerado em ${generatedAtLabel()}`, margin, 26);
  y = 38;

  sectionTitle('Identificação');
  field('Território', detail.territorio_nome);
  field('Tipo', detail.tipo_nome);
  if (isMunicipio) {
    field(
      'Município',
      detail.municipio_nome
        ? `${detail.municipio_nome}${detail.uf ? ` / ${detail.uf}` : ''}`
        : notInformed,
    );
  }
  field(
    'Estado',
    detail.estado_nome
      ? `${detail.estado_nome}${detail.uf ? ` (${detail.uf})` : ''}`
      : notInformed,
  );

  sectionTitle('Indicadores');
  field(
    'Total de habitantes',
    detail.habitantes != null ? formatInteger(detail.habitantes) : notInformed,
  );
  field('Total de eleitores', formatInteger(detail.quantidade_eleitores));
  field('Pessoas vinculadas', formatInteger(detail.quantidade_pessoas));

  sectionTitle('Malha geográfica');
  if (detail.geometry) {
    const mapImage = renderGeometryImage(detail.geometry, detail.cor);
    if (mapImage) {
      const maxMapHeight = 78;
      const mapSize = fitImageSize(mapImage.aspectRatio, contentWidth, maxMapHeight);
      ensureSpace(mapSize.height + 4);
      const mapX = margin + (contentWidth - mapSize.width) / 2;
      pdf.addImage(mapImage.dataUrl, 'PNG', mapX, y, mapSize.width, mapSize.height);
      y += mapSize.height + 4;
      pdf.setFont('helvetica', 'italic');
      pdf.setFontSize(8);
      pdf.setTextColor(105, 105, 105);
      pdf.text(
        isEstado
          ? 'Malha oficial da unidade federativa (IBGE).'
          : 'Malha oficial do município (IBGE).',
        margin,
        y,
      );
      y += 6;
    } else {
      field('Mapa', 'Não foi possível renderizar a malha geográfica.');
    }
  } else {
    field('Mapa', 'Malha geográfica indisponível para este território.');
  }

  if (isMunicipio && detail.pessoas.length > 0) {
    sectionTitle('Pessoas vinculadas');
    renderPeopleTable(pdf, detail.pessoas, {
      margin,
      contentWidth,
      pageHeight: height,
      getY: () => y,
      setY: (value) => {
        y = value;
      },
      ensureSpace,
    });
  }

  const totalPages = pdf.getNumberOfPages();
  for (let page = 1; page <= totalPages; page += 1) {
    pdf.setPage(page);
    pdf.setFont('helvetica', 'normal');
    pdf.setFontSize(7);
    pdf.setTextColor(115, 115, 115);
    pdf.text('Relatório territorial - uso interno da campanha', margin, height - 8);
    pdf.text(`Página ${page} de ${totalPages}`, width - margin, height - 8, { align: 'right' });
  }

  const fileName = filename(detail.territorio_nome);
  if (options.download !== false) pdf.save(fileName);
  return { pdf, fileName };
}

function renderPeopleTable(
  pdf: jsPDF,
  people: TerritorioPessoaVinculada[],
  ctx: {
    margin: number;
    contentWidth: number;
    pageHeight: number;
    getY: () => number;
    setY: (value: number) => void;
    ensureSpace: (needed: number) => void;
  },
) {
  const rowHeight = 8;
  const headerHeight = 7;
  const columns = [
    { label: 'Nome', width: 0.38 },
    { label: 'Telefone', width: 0.22 },
    { label: 'E-mail', width: 0.24 },
    { label: 'Papel', width: 0.16 },
  ] as const;

  const drawHeader = () => {
    ctx.ensureSpace(headerHeight + rowHeight);
    let x = ctx.margin;
    pdf.setFillColor(238, 244, 250);
    pdf.rect(ctx.margin, ctx.getY(), ctx.contentWidth, headerHeight, 'F');
    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(8);
    pdf.setTextColor(24, 67, 108);
    for (const column of columns) {
      const colWidth = ctx.contentWidth * column.width;
      pdf.text(column.label, x + 1.5, ctx.getY() + 4.8);
      x += colWidth;
    }
    ctx.setY(ctx.getY() + headerHeight);
  };

  drawHeader();

  pdf.setFont('helvetica', 'normal');
  pdf.setFontSize(8);
  pdf.setTextColor(35, 35, 35);

  for (const person of people) {
    ctx.ensureSpace(rowHeight + 2);
    if (ctx.getY() + rowHeight > ctx.pageHeight - 18) {
      pdf.addPage();
      ctx.setY(16);
      drawHeader();
    }

    const values = [
      person.nome_completo,
      formatPhone(person.telefone),
      person.email ?? notInformed,
      person.papel,
    ];
    let x = ctx.margin;
    pdf.setDrawColor(225, 228, 232);
    pdf.line(ctx.margin, ctx.getY(), ctx.margin + ctx.contentWidth, ctx.getY());

    values.forEach((value, index) => {
      const colWidth = ctx.contentWidth * columns[index].width;
      const lines = pdf.splitTextToSize(value, colWidth - 3);
      pdf.text(lines.slice(0, 2), x + 1.5, ctx.getY() + 5.2);
      x += colWidth;
    });
    ctx.setY(ctx.getY() + rowHeight);
  }
}
