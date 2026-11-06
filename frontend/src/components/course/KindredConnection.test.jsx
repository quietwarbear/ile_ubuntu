import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { KindredConnection } from './KindredConnection';
import { apiDelete, apiGet, apiPost } from '../../lib/api';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

jest.mock('../../lib/api', () => ({ apiGet: jest.fn(), apiPost: jest.fn(), apiDelete: jest.fn() }));

const flush = () => act(() => new Promise((r) => setTimeout(r, 0)));
let container;
let root;

const mount = async () => {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => root.render(<KindredConnection />));
  await flush();
};
const button = (text) => [...container.querySelectorAll('button')].find((b) => b.textContent === text);

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  jest.clearAllMocks();
});

test('creates a key and shows it once with a label', async () => {
  apiGet.mockResolvedValue({ active: false });
  apiPost.mockResolvedValue({ key: 'kh_secretvalue1234', active: true, last4: '1234' });
  await mount();
  await act(async () => button('Create a key').click());
  await flush();
  expect(apiPost).toHaveBeenCalledWith('/api/kindred-handoff/key', {});
  const input = container.querySelector('#kindred-key-value');
  expect(input.value).toBe('kh_secretvalue1234');
  expect(container.querySelector('label[for="kindred-key-value"]')).not.toBeNull();
});

test('an active key shows only its last four and can be disconnected', async () => {
  apiGet.mockResolvedValue({ active: true, last4: 'wxyz' });
  apiDelete.mockResolvedValue({ active: false });
  jest.spyOn(window, 'confirm').mockReturnValue(true);
  await mount();
  expect(container.querySelector('[data-testid="kindred-key-active"]').textContent).toContain('wxyz');
  expect(container.querySelector('#kindred-key-value')).toBeNull();
  await act(async () => button('Disconnect').click());
  await flush();
  expect(apiDelete).toHaveBeenCalledWith('/api/kindred-handoff/key');
  expect(button('Create a key')).toBeTruthy();
});

test('making a new key asks first when one is active', async () => {
  apiGet.mockResolvedValue({ active: true, last4: 'wxyz' });
  jest.spyOn(window, 'confirm').mockReturnValue(false);
  await mount();
  await act(async () => button('Make a new key').click());
  expect(apiPost).not.toHaveBeenCalled();
});

test('errors are announced', async () => {
  apiGet.mockResolvedValue({ active: false });
  apiPost.mockRejectedValue(new Error('Only someone who teaches a course can connect Kindred to it.'));
  await mount();
  await act(async () => button('Create a key').click());
  await flush();
  expect(container.querySelector('[role="alert"]').textContent).toContain('teaches a course');
});
