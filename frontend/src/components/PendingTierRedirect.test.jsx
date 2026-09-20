import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import PendingTierRedirect from './PendingTierRedirect';
import { hasPendingTier } from '../lib/pendingTier';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}), { virtual: true });
jest.mock('../lib/pendingTier', () => ({
  hasPendingTier: jest.fn(),
}));

describe('PendingTierRedirect', () => {
  let container;
  let root;

  beforeEach(() => {
    mockNavigate.mockClear();
    hasPendingTier.mockReset();
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  test("routes an authenticated visitor's remembered plan to subscriptions", () => {
    hasPendingTier.mockReturnValue(true);

    act(() => {
      root.render(<PendingTierRedirect />);
    });

    expect(mockNavigate).toHaveBeenCalledWith('/subscriptions', { replace: true });
  });

  test('leaves the current route alone when no plan was remembered', () => {
    hasPendingTier.mockReturnValue(false);

    act(() => {
      root.render(<PendingTierRedirect />);
    });

    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
