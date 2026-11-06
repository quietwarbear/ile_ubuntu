import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { AccessEndedNotice } from './AccessEndedNotice';
import { EnrolledStudents } from './EnrolledStudents';
import { apiPut } from '../../lib/api';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../../lib/api', () => ({ apiPut: jest.fn(), apiPost: jest.fn(), apiDelete: jest.fn() }));

let container; let root;
beforeEach(() => {
  apiPut.mockReset().mockResolvedValue({});
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); });

test('the ended notice names the course and the date', () => {
  act(() => root.render(<AccessEndedNotice endedAt={new Date('2026-01-31T12:00:00Z')} courseTitle="Weekend sessions" />));
  const card = container.querySelector('[data-testid="access-ended"]');
  expect(card.textContent).toContain('Your access has ended');
  expect(card.textContent).toContain('Weekend sessions');
  expect(card.textContent).toContain('2026');
});

const rows = [
  { id: 'e1', user_id: 'u1', user_name: 'Ada Lovelace', user_email: 'ada@example.test', enrolled_at: '2026-01-01',
    access_ends_at: '2026-01-31T23:59:59+00:00', access_ended: true, overridden: false },
  { id: 'e2', user_id: 'u2', user_name: 'Grace', user_email: 'grace@example.test', enrolled_at: '2026-01-01',
    access_ends_at: null, access_ended: false, overridden: true },
];

test('roster shows each person and staff can override or reset', async () => {
  const onChanged = jest.fn();
  act(() => root.render(<EnrolledStudents courseId="c1" enrollments={rows} onChanged={onChanged} />));
  expect(container.querySelector('[data-testid="access-u1"]').textContent).toBe('Access ended');
  expect(container.querySelector('[data-testid="access-u2"]').textContent).toBe('Access forever (set for this person)');
  expect(container.querySelector('[data-testid="access-inherit-u1"]')).toBeNull();

  await act(async () => { container.querySelector('[data-testid="access-forever-u1"]').click(); });
  expect(apiPut).toHaveBeenLastCalledWith('/api/courses/c1/enrollments/u1/access', { access_ends_at: null });
  await act(async () => { container.querySelector('[data-testid="access-inherit-u2"]').click(); });
  expect(apiPut).toHaveBeenLastCalledWith('/api/courses/c1/enrollments/u2/access', { inherit: true });
  expect(onChanged).toHaveBeenCalledTimes(2);
});
