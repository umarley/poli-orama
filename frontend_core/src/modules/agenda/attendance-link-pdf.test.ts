import { beforeEach, describe, expect, it, vi } from 'vitest';

const { pdf, toDataURL } = vi.hoisted(() => ({
  toDataURL: vi.fn(),
  pdf: {
    internal: { pageSize: { getWidth: () => 210 } },
    setFillColor: vi.fn(),
    rect: vi.fn(),
    setTextColor: vi.fn(),
    setFont: vi.fn(),
    setFontSize: vi.fn(),
    text: vi.fn(),
    splitTextToSize: vi.fn((text: string) => [text]),
    setDrawColor: vi.fn(),
    roundedRect: vi.fn(),
    addImage: vi.fn(),
    save: vi.fn(),
  },
}));

vi.mock('qrcode', () => ({ default: { toDataURL } }));
vi.mock('jspdf', () => ({
  jsPDF: function JsPdfMock() {
    return pdf;
  },
}));

import { buildPublicAttendanceUrl, generateAttendanceLinkPdf } from './attendance-link-pdf';

describe('PDF do link público de presença', () => {
  beforeEach(() => vi.clearAllMocks());

  it('monta a URL pública com o UUID do evento', () => {
    expect(buildPublicAttendanceUrl('abc-123', 'https://app.example.test/')).toBe(
      'https://app.example.test/presenca/abc-123',
    );
  });

  it('insere no PDF um QR Code direcionado ao formulário público', async () => {
    toDataURL.mockResolvedValueOnce('data:image/png;base64,qr-code');

    await generateAttendanceLinkPdf({
      uuid_publico: 'abc-123',
      titulo: 'Encontro comunitário',
      data_inicio: '2026-08-13T19:00:00-03:00',
      data_fim: '2026-08-13T21:00:00-03:00',
    });

    expect(toDataURL).toHaveBeenCalledWith(
      `${window.location.origin}/presenca/abc-123`,
      expect.objectContaining({ errorCorrectionLevel: 'H' }),
    );
    expect(pdf.addImage).toHaveBeenCalledWith(
      'data:image/png;base64,qr-code',
      'PNG',
      expect.any(Number),
      expect.any(Number),
      92,
      92,
    );
    expect(pdf.save).toHaveBeenCalledWith('presenca-encontro-comunitario.pdf');
  });

  it('aplica a cor primaria do tenant na faixa do PDF', async () => {
    toDataURL.mockResolvedValueOnce('data:image/png;base64,qr-code');

    await generateAttendanceLinkPdf(
      {
        uuid_publico: 'abc-123',
        titulo: 'Encontro comunitario',
        data_inicio: '2026-08-13T19:00:00-03:00',
        data_fim: null,
      },
      '#12A4EF',
    );

    expect(pdf.setFillColor).toHaveBeenNthCalledWith(1, 18, 164, 239);
  });

  it.each([null, '', 'azul', '#12345G'])(
    'mantem a cor azul padrao quando a cor primaria for %s',
    async (primaryColor) => {
      toDataURL.mockResolvedValueOnce('data:image/png;base64,qr-code');

      await generateAttendanceLinkPdf(
        {
          uuid_publico: 'abc-123',
          titulo: 'Encontro comunitario',
          data_inicio: '2026-08-13T19:00:00-03:00',
          data_fim: null,
        },
        primaryColor,
      );

      expect(pdf.setFillColor).toHaveBeenNthCalledWith(1, 23, 37, 84);
    },
  );
});
