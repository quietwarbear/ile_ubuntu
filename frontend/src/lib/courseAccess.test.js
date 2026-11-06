import { parseAccessEnded, formatAccessDate, endOfDayIso, toDateInput, accessSummary } from './courseAccess';

test('reads the server access_ended code', () => {
  expect(parseAccessEnded('access_ended:2026-01-31T23:59:59+00:00').endedAt.toISOString())
    .toBe('2026-01-31T23:59:59.000Z');
  expect(parseAccessEnded('access_ended:')).toEqual({ endedAt: null });
  expect(parseAccessEnded('tier_limit:3')).toBeNull();
  expect(parseAccessEnded(undefined)).toBeNull();
});

test('date input round-trips through end of local day', () => {
  const iso = endOfDayIso('2026-12-31');
  const d = new Date(iso);
  expect([d.getFullYear(), d.getMonth(), d.getDate(), d.getHours()]).toEqual([2026, 11, 31, 23]);
  expect(toDateInput(iso)).toBe('2026-12-31');
  expect(endOfDayIso('')).toBeNull();
  expect(toDateInput(null)).toBe('');
});

test('zone-less server datetimes are read as UTC', () => {
  expect(toDateInput('2026-06-15T12:00:00')).toBe(toDateInput('2026-06-15T12:00:00Z'));
});

test('summaries', () => {
  expect(accessSummary(null)).toBe('Access forever');
  expect(accessSummary('2026-06-15T12:00:00Z')).toContain('2026');
  expect(formatAccessDate('nonsense')).toBe('');
});
