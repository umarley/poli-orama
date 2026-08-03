export function formatPhoneContact(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 11);
  if (!digits) return '';
  if (digits.length <= 2) return `(${digits}`;

  const areaCode = digits.slice(0, 2);
  const number = digits.slice(2);
  if (number.length <= 4) return `(${areaCode}) ${number}`;
  if (number.length <= 8) {
    return `(${areaCode}) ${number.slice(0, 4)}-${number.slice(4)}`;
  }
  return `(${areaCode}) ${number.slice(0, 5)}-${number.slice(5)}`;
}

export function isValidPhoneContact(value: string): boolean {
  const digits = value.replace(/\D/g, '');
  return digits.length === 10 || digits.length === 11;
}
