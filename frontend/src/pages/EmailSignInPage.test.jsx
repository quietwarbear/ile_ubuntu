import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import EmailSignInPage, { appCallbackUrl, isPhoneBrowser } from './EmailSignInPage';
import LoginPage from './LoginPage';
import { apiPost, setCookie } from '../lib/api';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

// react-router-dom v7 doesn't resolve under this Jest; the repo mocks it
// virtually (see PendingTierRedirect.test.jsx).
let mockSearch = '';
jest.mock('react-router-dom', () => ({
  useSearchParams: () => [new URLSearchParams(mockSearch)],
  Link: ({ to, children, ...rest }) => <a href={to} {...rest}>{children}</a>,
}), { virtual: true });
const MemoryRouter = ({ initialEntries = ['/'], children }) => {
  mockSearch = (initialEntries[0].split('?')[1] || '');
  return children;
};

jest.mock('../lib/api', () => ({
  apiPost: jest.fn(),
  setCookie: jest.fn(),
}));

const flush = () => act(() => new Promise(r => setTimeout(r, 0)));

describe('helpers', () => {
  test('phone browsers get the app option, the app itself does not', () => {
    expect(isPhoneBrowser({ userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0)' }, {})).toBe(true);
    expect(isPhoneBrowser({ userAgent: 'Mozilla/5.0 (Linux; Android 15)' }, {})).toBe(true);
    expect(isPhoneBrowser({ userAgent: 'Mozilla/5.0 (Macintosh)' }, {})).toBe(false);
    expect(isPhoneBrowser({ userAgent: 'iPhone' }, { Capacitor: { isNativePlatform: () => true } })).toBe(false);
  });
  test('app hand-off uses the callback the app already handles', () => {
    expect(appCallbackUrl('abc')).toBe('ileubuntu://auth/email/callback?session_id=abc');
  });
});

describe('EmailSignInPage', () => {
  let container;
  let root;

  beforeEach(() => {
    apiPost.mockReset();
    setCookie.mockReset();
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  const render = (url) => act(() => root.render(
    <MemoryRouter initialEntries={[url]}><EmailSignInPage /></MemoryRouter>,
  ));

  test('does not use the link until the button is pressed', async () => {
    apiPost.mockResolvedValueOnce({ state: 'valid' });
    render('/signin-link?token=tok');
    await flush();
    expect(apiPost).toHaveBeenCalledTimes(1);
    expect(apiPost).toHaveBeenCalledWith('/api/auth/email-link/status', { token: 'tok' });
    expect(container.querySelector('[data-testid="signin-web"]')).not.toBeNull();
  });

  test('pressing Sign in redeems the link and stores the session', async () => {
    apiPost.mockResolvedValueOnce({ state: 'valid' })
      .mockResolvedValueOnce({ session_id: 'sess-1' });
    const replace = jest.fn();
    const original = window.location;
    delete window.location;
    window.location = { ...original, replace };
    try {
      render('/signin-link?token=tok');
      await flush();
      await act(async () => { container.querySelector('[data-testid="signin-web"]').click(); });
      await flush();
      expect(apiPost).toHaveBeenLastCalledWith('/api/auth/email-link/redeem', { token: 'tok' });
      expect(setCookie).toHaveBeenCalledWith('session_id', 'sess-1', 7);
      expect(replace).toHaveBeenCalledWith('/dashboard');
    } finally {
      window.location = original;
    }
  });

  test('an expired link offers a new one', async () => {
    apiPost.mockResolvedValueOnce({ state: 'expired' })
      .mockResolvedValueOnce({ message: 'on its way' });
    render('/signin-link?token=old&app=1');
    await flush();
    const form = container.querySelector('[data-testid="request-new-link"]');
    expect(form.textContent).toContain('expired');
    const input = form.querySelector('input[type="email"]');
    await act(async () => {
      Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(input, 'ada@example.test');
      input.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await act(async () => { form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); });
    await flush();
    expect(apiPost).toHaveBeenLastCalledWith('/api/auth/email-link', { email: 'ada@example.test', app: true });
    expect(container.querySelector('[data-testid="request-new-link-info"]').textContent).toBe('on its way');
  });

  test('a link without a token goes straight to asking for a new one', async () => {
    render('/signin-link');
    await flush();
    expect(apiPost).not.toHaveBeenCalled();
    expect(container.querySelector('[data-testid="request-new-link"]')).not.toBeNull();
  });
});

describe('LoginPage sign-in link mode', () => {
  let container;
  let root;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    global.fetch = jest.fn().mockResolvedValue({
      ok: true, json: async () => ({ message: "If there's an account for that email, a sign-in link is on its way." }),
    });
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    delete global.fetch;
  });

  test('asks for a link with just an email', async () => {
    act(() => root.render(<MemoryRouter><LoginPage onLogin={jest.fn()} onPasswordLogin={jest.fn()} /></MemoryRouter>));
    await act(async () => { container.querySelector('[data-testid="email-link-mode"]').click(); });
    expect(container.querySelector('input[type="password"]')).toBeNull();

    const input = container.querySelector('input[type="email"]');
    await act(async () => {
      Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set.call(input, 'ada@example.test');
      input.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await act(async () => { container.querySelector('[data-testid="login-button"]').click(); });
    await flush();

    const [url, init] = global.fetch.mock.calls.find(([u]) => String(u).includes('/api/auth/'));
    expect(url).toMatch(/\/api\/auth\/email-link$/);
    expect(JSON.parse(init.body)).toEqual({ email: 'ada@example.test', app: false });
    expect(container.textContent).toContain('sign-in link is on its way');
  });
});
