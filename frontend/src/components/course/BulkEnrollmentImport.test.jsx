import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { BulkEnrollmentImport, allMapped, mappingFrom } from './BulkEnrollmentImport';
import { apiGet, apiPost } from '../../lib/api';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock('../../lib/api', () => ({
  apiGet: jest.fn(),
  apiPost: jest.fn(),
}));

const flush = () => act(() => new Promise(r => setTimeout(r, 0)));

const previewBody = (courseId) => ({
  total_rows: 2,
  preview_rows: [{ row: 2, name: 'Ada', email: 'ada@example.test', sessions: ['Day 1'] }],
  sessions: [{ label: 'Day 1', course_id: courseId }],
  report: { dry_run: true, counts: { created: 1, enrolled: 1, skipped: 0, errors: 1 },
    errors: [{ row: 3, email: '', error: 'Missing or invalid email' }] },
});

describe('mapping helpers', () => {
  test('mappingFrom keeps only chosen courses', () => {
    expect(mappingFrom([{ label: 'A', course_id: 'c1' }, { label: 'B', course_id: null }])).toEqual({ A: 'c1' });
  });
  test('allMapped needs every session chosen', () => {
    expect(allMapped([{ label: 'A', course_id: 'c1' }])).toBe(true);
    expect(allMapped([{ label: 'A', course_id: 'c1' }, { label: 'B', course_id: null }])).toBe(false);
    expect(allMapped([])).toBe(false);
  });
});

describe('BulkEnrollmentImport', () => {
  let container;
  let root;

  beforeEach(() => {
    apiGet.mockReset().mockResolvedValue([{ id: 'c-day1', title: 'Day One', visibility: 'private' }]);
    apiPost.mockReset();
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  async function upload() {
    const input = container.querySelector('[data-testid="import-file"]');
    const file = new File(['name,email,sessions\nAda,ada@example.test,Day 1\n'], 'roster.csv', { type: 'text/csv' });
    Object.defineProperty(input, 'files', { value: [file] });
    await act(async () => { input.dispatchEvent(new Event('change', { bubbles: true })); });
    await flush(); await flush();
  }

  test('upload → preview → map → confirm → report', async () => {
    apiPost
      .mockResolvedValueOnce(previewBody(null))        // first preview: unmapped
      .mockResolvedValueOnce(previewBody('c-day1'))    // after mapping
      .mockResolvedValueOnce({ counts: { created: 1, enrolled: 1, skipped: 0, errors: 1 },
        errors: [{ row: 3, email: '', error: 'Missing or invalid email' }] });

    act(() => root.render(<BulkEnrollmentImport />));
    await flush();
    expect(apiGet).toHaveBeenCalledWith('/api/enrollment-imports/courses');

    await upload();
    expect(apiPost).toHaveBeenCalledWith('/api/enrollment-imports/preview',
      { csv: 'name,email,sessions\nAda,ada@example.test,Day 1\n', session_map: {} });
    expect(container.textContent).toContain('ada@example.test');
    expect(container.querySelector('[data-testid="import-errors"]').textContent).toContain('Row 3');
    const confirm = container.querySelector('[data-testid="import-confirm"]');
    expect(confirm.disabled).toBe(true);

    const select = container.querySelector('[data-testid="map-Day 1"]');
    expect(select.textContent).toContain('Day One (private)');
    await act(async () => {
      Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set.call(select, 'c-day1');
      select.dispatchEvent(new Event('change', { bubbles: true }));
    });
    await flush();
    expect(apiPost).toHaveBeenLastCalledWith('/api/enrollment-imports/preview',
      expect.objectContaining({ session_map: { 'Day 1': 'c-day1' } }));
    expect(container.querySelector('[data-testid="import-confirm"]').disabled).toBe(false);

    await act(async () => { container.querySelector('[data-testid="import-confirm"]').click(); });
    await flush();
    expect(apiPost).toHaveBeenLastCalledWith('/api/enrollment-imports',
      expect.objectContaining({ session_map: { 'Day 1': 'c-day1' } }));
    const report = container.querySelector('[data-testid="import-report"]');
    expect(report.textContent).toContain('Import finished');
    expect(container.querySelector('[data-testid="import-report-counts"]').textContent).toContain('enrollments added');
  });

  test('shows the server error for an unusable file', async () => {
    apiPost.mockRejectedValueOnce(new Error('The file needs a header row with these columns: name, email, sessions'));
    act(() => root.render(<BulkEnrollmentImport />));
    await flush();
    await upload();
    expect(container.querySelector('[data-testid="import-error"]').textContent).toContain('name, email, sessions');
    expect(container.querySelector('[data-testid="import-preview"]')).toBeNull();
  });
});
