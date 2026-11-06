import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { NativeCoursePurchase } from './NativeCoursePurchase';
import { apiGet, apiPost } from '../../lib/api';
import { loadCourseProduct, purchaseCourseProduct, restoreCourseProducts } from '../../lib/coursePurchases';
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../../lib/api', () => ({ apiGet: jest.fn(), apiPost: jest.fn() }));
jest.mock('../../lib/coursePurchases', () => ({ coursePurchasePlatform: () => 'ios', loadCourseProduct: jest.fn(), purchaseCourseProduct: jest.fn(), restoreCourseProducts: jest.fn() }));
const flush = () => act(() => new Promise(resolve => setTimeout(resolve, 0)));
let container, root, granted;
beforeEach(() => {
  jest.clearAllMocks();
  apiGet.mockResolvedValue({ available: true, products: { ios: 'ios.course' } });
  loadCourseProduct.mockResolvedValue({ identifier: 'ios.course', priceString: '$3.00' });
  granted = jest.fn(); container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); });
async function render() { act(() => root.render(<NativeCoursePurchase courseId="course" userId="learner" onAccessGranted={granted} />)); await flush(); }
async function click(id) { act(() => container.querySelector(`[data-testid="${id}"]`).click()); await flush(); }
test('shows localized store price without requiring membership', async () => {
  await render(); expect(container.textContent).toContain('Buy course · $3.00'); expect(container.textContent).toContain('No membership required'); expect(loadCourseProduct).toHaveBeenCalledWith('ios.course','learner');
});
test('cancellation cannot enroll the learner', async () => {
  apiPost.mockResolvedValue({ enrolled:false }); purchaseCourseProduct.mockResolvedValue({ cancelled:true }); await render(); await click('buy-course'); expect(granted).not.toHaveBeenCalled(); expect(apiPost).toHaveBeenCalledTimes(1);
});
test('only server confirmation unlocks the store purchase', async () => {
  apiPost.mockResolvedValueOnce({ enrolled:false }).mockResolvedValueOnce({ enrolled:true }); purchaseCourseProduct.mockResolvedValue({ cancelled:false }); await render(); await click('buy-course'); expect(purchaseCourseProduct).toHaveBeenCalledTimes(1); expect(apiPost).toHaveBeenLastCalledWith('/api/courses/course/confirm-purchase',{}); expect(granted).toHaveBeenCalledTimes(1);
});
test('existing web or store access skips the charge sheet', async () => {
  apiPost.mockResolvedValue({ enrolled:true }); await render(); await click('buy-course'); expect(purchaseCourseProduct).not.toHaveBeenCalled(); expect(granted).toHaveBeenCalledTimes(1);
});
test('confirmation outage offers a retry without charging again', async () => {
  apiPost.mockResolvedValueOnce({ enrolled:false }).mockRejectedValueOnce(new Error('Please try again.')); purchaseCourseProduct.mockResolvedValue({ cancelled:false }); await render(); await click('buy-course'); expect(container.querySelector('[data-testid="buy-course"]')).toBeNull(); expect(container.querySelector('[data-testid="confirm-course-purchase"]')).not.toBeNull(); apiPost.mockResolvedValue({ enrolled:true }); await click('confirm-course-purchase'); expect(purchaseCourseProduct).toHaveBeenCalledTimes(1); expect(granted).toHaveBeenCalledTimes(1);
});
test('restore works when the store product is unavailable', async () => {
  loadCourseProduct.mockRejectedValue(new Error('Unavailable')); restoreCourseProducts.mockResolvedValue({}); apiPost.mockResolvedValue({ enrolled:true }); await render(); await click('restore-course-purchases'); expect(restoreCourseProducts).toHaveBeenCalledWith('learner'); expect(granted).toHaveBeenCalledTimes(1); expect(purchaseCourseProduct).not.toHaveBeenCalled();
});
test('an unconfigured course cannot open a charge sheet', async () => {
  apiGet.mockResolvedValue({ available:false }); await render(); await click('buy-course'); expect(purchaseCourseProduct).not.toHaveBeenCalled(); expect(container.textContent).toContain('not available yet');
});
