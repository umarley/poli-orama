const integerFormatter = new Intl.NumberFormat('pt-BR', {
  maximumFractionDigits: 0,
});

export function formatInteger(value: number | string | null | undefined): string {
  const numericValue = Number(value ?? 0);
  return integerFormatter.format(Number.isFinite(numericValue) ? numericValue : 0);
}

export function formatNumber(
  value: number | string | null | undefined,
  minimumFractionDigits = 0,
  maximumFractionDigits = 2,
): string {
  const numericValue = Number(value ?? 0);
  return new Intl.NumberFormat('pt-BR', {
    minimumFractionDigits,
    maximumFractionDigits,
  }).format(Number.isFinite(numericValue) ? numericValue : 0);
}

export function formatPercent(
  value: number | string | null | undefined,
  fractionDigits = 1,
): string {
  return `${formatNumber(value, fractionDigits, fractionDigits)}%`;
}
