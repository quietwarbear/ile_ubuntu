// Course access end dates (I6). The server refuses lesson content, files and
// video after the end with "access_ended:<ISO date>" (same shape as the
// tier_limit:… errors parseTierError reads).

export function parseAccessEnded(message) {
  if (typeof message !== 'string' || !message.startsWith('access_ended:')) return null;
  const iso = message.slice('access_ended:'.length);
  const date = iso ? new Date(iso) : null;
  return { endedAt: date && !Number.isNaN(date.getTime()) ? date : null };
}

// Mongo hands back UTC datetimes without a zone; read those as UTC.
function parseStored(value) {
  if (value instanceof Date) return value;
  const text = String(value);
  const zoned = /([zZ]|[+-]\d\d:?\d\d)$/.test(text) || text.length <= 10;
  return new Date(zoned ? text : `${text}Z`);
}

export function formatAccessDate(value) {
  if (!value) return '';
  const date = parseStored(value);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
}

// <input type="date"> value (local day) → ISO end of that day in the
// organizer's own time zone. '' → null (forever).
export function endOfDayIso(dateValue) {
  if (!dateValue) return null;
  const [y, m, d] = dateValue.split('-').map(Number);
  if (!y || !m || !d) return null;
  return new Date(y, m - 1, d, 23, 59, 59).toISOString();
}

// ISO → value for <input type="date"> in local time; '' for none.
export function toDateInput(iso) {
  if (!iso) return '';
  const date = parseStored(iso);
  if (Number.isNaN(date.getTime())) return '';
  const pad = n => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function accessSummary(iso) {
  return iso ? `Access until ${formatAccessDate(iso)}` : 'Access forever';
}
