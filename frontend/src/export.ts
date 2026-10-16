/** Stock request keys also work over plain HTTP inside a local cluster. */
export function createRequestKey(): string {
  if (typeof globalThis.crypto.randomUUID === 'function') return `web-${globalThis.crypto.randomUUID()}`;
  const random = globalThis.crypto.getRandomValues(new Uint8Array(16));
  return 'web-' + Array.from(random, value => value.toString(16).padStart(2, '0')).join('');
}

/** Neutralize spreadsheet formulas before quoting fields for RFC 4180 CSV. */
export function inventoryCsv(rows: (string | number)[][]): string {
  return rows.map(row => row.map(value => {
    const original = String(value);
    const safe = /^\s*[=+@-]/.test(original) || /^[\t\r\n]/.test(original) ? "'" + original : original;
    return '"' + safe.replace(/"/g, '""') + '"';
  }).join(',')).join('\r\n');
}
