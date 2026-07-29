import { jsPDF } from 'jspdf';

import type { PessoaDetalhe } from './types';
import type { InteracaoPessoa } from '@/modules/comunicacao/types';

interface ElectoralLabels {
  municipality?: string;
  state?: string;
  zone?: string;
  section?: string;
  pollingPlace?: string;
  pollingPlaceAddress?: string;
}

interface RegistrationPdfInput {
  person: PessoaDetalhe;
  interactions: InteracaoPessoa[];
  photo?: Blob | null;
  electoral: ElectoralLabels;
  civilStatus?: string;
  addressLabels: Map<number, string>;
}

const notInformed = 'Não informado';

function date(value: string | null) {
  if (!value) return notInformed;
  const [year, month, day] = value.split('-');
  return year && month && day ? `${day}/${month}/${year}` : value;
}

function dateTime(value: string) {
  return new Intl.DateTimeFormat('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value));
}

function age(birthDate: string | null) {
  if (!birthDate) return notInformed;
  const birth = new Date(`${birthDate}T12:00:00`);
  const today = new Date();
  let years = today.getFullYear() - birth.getFullYear();
  if (
    today.getMonth() < birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate())
  )
    years -= 1;
  return `${years} anos`;
}

function filename(name: string) {
  const safe = name
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9]+/g, '-');
  return `ficha-cadastral-${safe.replace(/^-|-$/g, '').toLowerCase()}.pdf`;
}

function blobToDataUrl(blob: Blob) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

export async function generatePersonRegistrationPdf(
  input: RegistrationPdfInput,
  options: { download?: boolean } = {},
) {
  const { person, electoral } = input;
  const pdf = new jsPDF({ unit: 'mm', format: 'a4' });
  const width = pdf.internal.pageSize.getWidth();
  const height = pdf.internal.pageSize.getHeight();
  const margin = 15;
  const contentWidth = width - margin * 2;
  let y = 16;

  const ensureSpace = (needed: number) => {
    if (y + needed <= height - 17) return;
    pdf.addPage();
    y = 17;
  };
  const section = (title: string) => {
    ensureSpace(13);
    pdf.setFillColor(238, 244, 250);
    pdf.roundedRect(margin, y, contentWidth, 8, 1.5, 1.5, 'F');
    pdf.setTextColor(24, 67, 108);
    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(10);
    pdf.text(title.toUpperCase(), margin + 3, y + 5.4);
    pdf.setTextColor(35, 35, 35);
    y += 12;
  };
  const field = (label: string, value: string, x: number, fieldWidth: number, lineY = y) => {
    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(7.5);
    pdf.setTextColor(90, 90, 90);
    pdf.text(label.toUpperCase(), x, lineY);
    pdf.setFont('helvetica', 'normal');
    pdf.setFontSize(9.5);
    pdf.setTextColor(30, 30, 30);
    const lines = pdf.splitTextToSize(value || notInformed, fieldWidth);
    pdf.text(lines, x, lineY + 4.5);
    return lines.length;
  };

  pdf.setFillColor(24, 67, 108);
  pdf.rect(0, 0, width, 31, 'F');
  pdf.setTextColor(255, 255, 255);
  pdf.setFont('helvetica', 'bold');
  pdf.setFontSize(17);
  pdf.text('FICHA CADASTRAL DO ELEITOR', margin, 14);
  pdf.setFont('helvetica', 'normal');
  pdf.setFontSize(9);
  pdf.text(
    `Cadastro #${person.id}  -  Emitida em ${dateTime(new Date().toISOString())}`,
    margin,
    21,
  );
  pdf.text('Uso interno do escritório político / comitê', margin, 26);
  y = 39;

  const photoWidth = 34;
  const photoHeight = 42;
  pdf.setDrawColor(190, 198, 205);
  pdf.setFillColor(247, 248, 250);
  pdf.roundedRect(margin, y, photoWidth, photoHeight, 2, 2, 'FD');
  if (input.photo) {
    try {
      const photoData = await blobToDataUrl(input.photo);
      const format = input.photo.type.includes('png') ? 'PNG' : 'JPEG';
      pdf.addImage(
        photoData,
        format,
        margin + 1,
        y + 1,
        photoWidth - 2,
        photoHeight - 2,
        undefined,
        'FAST',
      );
    } catch {
      pdf.setFontSize(8);
      pdf.setTextColor(120, 120, 120);
      pdf.text('Foto indisponível', margin + photoWidth / 2, y + 22, { align: 'center' });
    }
  } else {
    pdf.setFontSize(8);
    pdf.setTextColor(120, 120, 120);
    pdf.text('Sem foto', margin + photoWidth / 2, y + 22, { align: 'center' });
  }
  const infoX = margin + photoWidth + 7;
  const infoWidth = contentWidth - photoWidth - 7;
  pdf.setTextColor(25, 25, 25);
  pdf.setFont('helvetica', 'bold');
  pdf.setFontSize(16);
  pdf.text(pdf.splitTextToSize(person.nome_completo, infoWidth), infoX, y + 6);
  field(
    'Nome social / apelido',
    [person.nome_social, person.apelido].filter(Boolean).join(' / ') || notInformed,
    infoX,
    infoWidth,
    y + 17,
  );
  field(
    'Nascimento',
    `${date(person.data_nascimento)}  -  ${age(person.data_nascimento)}`,
    infoX,
    62,
    y + 29,
  );
  field(
    'Segmento do cadastro',
    person.tipos.map((item) => item.nome).join(', ') || notInformed,
    infoX + 67,
    infoWidth - 67,
    y + 29,
  );
  y += 49;

  section('Identificação e contato');
  const cpf = person.documentos.find((item) => item.tipo_documento === 'cpf')?.numero;
  const rg = person.documentos.find((item) => item.tipo_documento === 'rg')?.numero;
  const mainContact = person.contatos.find((item) => item.principal) ?? person.contatos[0];
  field('CPF', cpf || notInformed, margin, 55);
  field('RG', rg || notInformed, margin + 61, 48);
  field('Estado civil', input.civilStatus || notInformed, margin + 115, 65);
  y += 13;
  field(
    'Contato principal',
    mainContact ? `${mainContact.valor} (${mainContact.tipo_contato})` : notInformed,
    margin,
    85,
  );
  field(
    'Tags / grupos',
    person.tags.map((item) => item.nome).join(', ') || notInformed,
    margin + 91,
    89,
  );
  y += 14;

  section('Dados eleitorais');
  field('Título de eleitor', person.eleitor?.titulo_eleitor || notInformed, margin, 58);
  field('Situação', person.eleitor?.situacao_titulo || notInformed, margin + 64, 40);
  field(
    'Município / UF',
    [electoral.municipality, electoral.state].filter(Boolean).join(' - ') || notInformed,
    margin + 110,
    70,
  );
  y += 13;
  field('Zona', electoral.zone || notInformed, margin, 37);
  field('Seção', electoral.section || notInformed, margin + 43, 37);
  field('Local de votação', electoral.pollingPlace || notInformed, margin + 86, 94);
  y += 13;
  field(
    'Endereço do local de votação',
    electoral.pollingPlaceAddress || notInformed,
    margin,
    contentWidth,
  );
  y += 14;

  section('Endereço e perfil político');
  const addressLink = person.enderecos.find((item) => item.principal) ?? person.enderecos[0];
  const address = addressLink?.endereco;
  const addressText = address
    ? [
        [address.logradouro, address.numero].filter(Boolean).join(', '),
        address.complemento,
        address.bairro_texto,
        address.codigo_municipio_ibge
          ? input.addressLabels.get(address.codigo_municipio_ibge)
          : null,
        address.cep ? `CEP ${address.cep}` : null,
      ]
        .filter(Boolean)
        .join(' - ')
    : notInformed;
  field('Endereço principal', addressText, margin, contentWidth);
  y += 14;
  field(
    'Comunidades',
    person.comunidades.map((item) => item.nome).join(', ') || notInformed,
    margin,
    85,
  );
  field(
    'Temas de interesse',
    person.complemento_politico?.temas_interesse.join(', ') || notInformed,
    margin + 91,
    89,
  );
  y += 14;
  field(
    'Vínculo / cargo político',
    [person.complemento_politico?.vinculo_politico, person.complemento_politico?.cargo_funcao]
      .filter(Boolean)
      .join(' - ') || notInformed,
    margin,
    85,
  );
  field(
    'Engajamento',
    person.nivel_engajamento?.toString() ||
      person.complemento_politico?.nivel_engajamento?.toString() ||
      notInformed,
    margin + 91,
    40,
  );
  y += 15;
  if (person.observacoes || person.complemento_politico?.observacoes) {
    const observations = [person.observacoes, person.complemento_politico?.observacoes]
      .filter(Boolean)
      .join(' | ');
    const lines = field('Observações do cadastro', observations, margin, contentWidth);
    y += 7 + lines * 4;
  }

  section('Últimas visitas e interações');
  if (!input.interactions.length) {
    pdf.setFont('helvetica', 'italic');
    pdf.setFontSize(9);
    pdf.setTextColor(105, 105, 105);
    pdf.text('Nenhuma visita ou interação registrada.', margin, y);
    y += 9;
  } else {
    for (const interaction of input.interactions.slice(0, 5)) {
      const title =
        interaction.assunto || interaction.tipo_interacao_nome || 'Interação registrada';
      const details = [
        interaction.conteudo,
        interaction.resultado ? `Resultado: ${interaction.resultado}` : null,
      ]
        .filter(Boolean)
        .join(' - ');
      const detailLines = pdf.splitTextToSize(details || 'Sem detalhes.', contentWidth - 5);
      const blockHeight = 10 + detailLines.length * 3.6;
      ensureSpace(blockHeight);
      pdf.setDrawColor(210, 215, 220);
      pdf.line(margin, y - 2, margin, y + blockHeight - 4);
      pdf.setFont('helvetica', 'bold');
      pdf.setFontSize(8.5);
      pdf.setTextColor(35, 35, 35);
      pdf.text(`${dateTime(interaction.data_interacao)}  -  ${title}`, margin + 4, y);
      pdf.setFont('helvetica', 'normal');
      pdf.setFontSize(8);
      pdf.setTextColor(80, 80, 80);
      pdf.text(
        `${interaction.canal_comunicacao_nome || 'Canal não informado'}  -  ${interaction.direcao === 'entrada' ? 'Entrada' : 'Saída'}`,
        margin + 4,
        y + 4.2,
      );
      pdf.text(detailLines, margin + 4, y + 8.2);
      y += blockHeight;
    }
  }

  section('Anotações da visita');
  ensureSpace(42);
  pdf.setDrawColor(170, 175, 180);
  for (let index = 0; index < 7; index += 1) {
    pdf.line(margin, y + index * 6, width - margin, y + index * 6);
  }

  const totalPages = pdf.getNumberOfPages();
  for (let page = 1; page <= totalPages; page += 1) {
    pdf.setPage(page);
    pdf.setFont('helvetica', 'normal');
    pdf.setFontSize(7);
    pdf.setTextColor(115, 115, 115);
    pdf.text('Documento confidencial - uso interno da campanha', margin, height - 8);
    pdf.text(`Página ${page} de ${totalPages}`, width - margin, height - 8, { align: 'right' });
  }

  const fileName = filename(person.nome_completo);
  if (options.download !== false) pdf.save(fileName);
  return { pdf, fileName };
}
