import dayjs from 'dayjs';
import { jsPDF } from 'jspdf';
import QRCode from 'qrcode';

import type { AgendaEventDetail } from '@/modules/agenda/types';

const DEFAULT_BANNER_COLOR: [number, number, number] = [23, 37, 84];

function getBannerColor(primaryColor?: string | null): [number, number, number] {
  const match = primaryColor?.trim().match(/^#([0-9a-f]{6})(?:[0-9a-f]{2})?$/i);
  if (!match) return DEFAULT_BANNER_COLOR;

  return [
    Number.parseInt(match[1].slice(0, 2), 16),
    Number.parseInt(match[1].slice(2, 4), 16),
    Number.parseInt(match[1].slice(4, 6), 16),
  ];
}

export function buildPublicAttendanceUrl(publicId: string, origin = window.location.origin) {
  return `${origin.replace(/\/$/, '')}/presenca/${encodeURIComponent(publicId)}`;
}

export async function createAttendanceLinkPdf(
  event: Pick<AgendaEventDetail, 'uuid_publico' | 'titulo' | 'data_inicio' | 'data_fim'>,
  origin = window.location.origin,
  primaryColor?: string | null,
) {
  const publicUrl = buildPublicAttendanceUrl(event.uuid_publico, origin);
  const qrCode = await QRCode.toDataURL(publicUrl, {
    width: 600,
    margin: 2,
    errorCorrectionLevel: 'H',
    color: { dark: '#172554', light: '#FFFFFF' },
  });
  const pdf = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait' });
  const pageWidth = pdf.internal.pageSize.getWidth();

  pdf.setFillColor(...getBannerColor(primaryColor));
  pdf.rect(0, 0, pageWidth, 45, 'F');
  pdf.setTextColor(255, 255, 255);
  pdf.setFont('helvetica', 'bold');
  pdf.setFontSize(22);
  pdf.text('Confirme sua presença', pageWidth / 2, 21, { align: 'center' });
  pdf.setFont('helvetica', 'normal');
  pdf.setFontSize(11);
  pdf.text('Aponte a câmera do celular para o QR Code', pageWidth / 2, 31, {
    align: 'center',
  });

  pdf.setTextColor(15, 23, 42);
  pdf.setFont('helvetica', 'bold');
  pdf.setFontSize(17);
  const titleLines = pdf.splitTextToSize(event.titulo, 170) as string[];
  pdf.text(titleLines, pageWidth / 2, 62, { align: 'center' });

  const titleBottom = 62 + Math.max(titleLines.length - 1, 0) * 7;
  const eventDate = dayjs(event.data_inicio);
  const eventEnd = event.data_fim ? dayjs(event.data_fim) : null;
  pdf.setFont('helvetica', 'normal');
  pdf.setFontSize(12);
  pdf.setTextColor(71, 85, 105);
  pdf.text(`Data: ${eventDate.format('DD/MM/YYYY')}`, pageWidth / 2, titleBottom + 13, {
    align: 'center',
  });
  pdf.text(
    `Horário: ${eventDate.format('HH:mm')}${eventEnd ? ` às ${eventEnd.format('HH:mm')}` : ''}`,
    pageWidth / 2,
    titleBottom + 21,
    { align: 'center' },
  );

  const qrSize = 92;
  const qrY = titleBottom + 32;
  pdf.setDrawColor(226, 232, 240);
  pdf.setFillColor(255, 255, 255);
  pdf.roundedRect((pageWidth - qrSize - 10) / 2, qrY - 5, qrSize + 10, qrSize + 10, 4, 4, 'FD');
  pdf.addImage(qrCode, 'PNG', (pageWidth - qrSize) / 2, qrY, qrSize, qrSize);

  pdf.setTextColor(71, 85, 105);
  pdf.setFontSize(9);
  const urlLines = pdf.splitTextToSize(publicUrl, 165) as string[];
  pdf.text(urlLines, pageWidth / 2, qrY + qrSize + 15, { align: 'center' });
  pdf.setFontSize(10);
  pdf.text('O formulário não exige login.', pageWidth / 2, qrY + qrSize + 29, {
    align: 'center',
  });

  const safeTitle = event.titulo
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .toLowerCase();
  return {
    pdf,
    publicUrl,
    fileName: `presenca-${safeTitle || event.uuid_publico}.pdf`,
  };
}

export async function generateAttendanceLinkPdf(
  event: Pick<AgendaEventDetail, 'uuid_publico' | 'titulo' | 'data_inicio' | 'data_fim'>,
  primaryColor?: string | null,
) {
  const result = await createAttendanceLinkPdf(event, window.location.origin, primaryColor);
  result.pdf.save(result.fileName);
  return result.publicUrl;
}
