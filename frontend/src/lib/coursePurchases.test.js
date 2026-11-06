import { Capacitor } from '@capacitor/core';
import { Purchases } from '@revenuecat/purchases-capacitor';
import { initializeRevenueCat } from './revenuecat';
import { loadCourseProduct, purchaseCourseProduct, restoreCourseProducts, needsCoursePurchase } from './coursePurchases';
jest.mock('@capacitor/core', () => ({ Capacitor: { isNativePlatform: jest.fn(() => true), getPlatform: () => 'android' } }));
jest.mock('./revenuecat', () => ({ initializeRevenueCat: jest.fn() }));
jest.mock('@revenuecat/purchases-capacitor', () => ({ Purchases: { logIn: jest.fn(), getAppUserID: jest.fn(), getProducts: jest.fn(), purchaseStoreProduct: jest.fn(), restorePurchases: jest.fn() } }));
beforeEach(() => { jest.clearAllMocks(); Capacitor.isNativePlatform.mockReturnValue(true); Purchases.getAppUserID.mockResolvedValue({ appUserID:'learner' }); });
test('waits for initialization, binds the authenticated account, and fetches non-subscriptions', async () => {
  Purchases.getProducts.mockResolvedValue({ products:[{ identifier:'course', priceString:'$3.00' }] });
  expect((await loadCourseProduct('course','learner')).priceString).toBe('$3.00');
  expect(initializeRevenueCat).toHaveBeenCalled(); expect(Purchases.logIn).toHaveBeenCalledWith({ appUserID:'learner' });
  expect(Purchases.getProducts).toHaveBeenCalledWith({ productIdentifiers:['course'], type:'NON_SUBSCRIPTION' });
});
test('account mismatch cannot open a charge sheet', async () => {
  Purchases.getAppUserID.mockResolvedValue({ appUserID:'other' });
  await expect(purchaseCourseProduct({},'learner')).rejects.toThrow('sign in again'); expect(Purchases.purchaseStoreProduct).not.toHaveBeenCalled();
});
test('store cancellation is handled without an error or grant', async () => {
  Purchases.purchaseStoreProduct.mockRejectedValue({ code:'1' }); expect(await purchaseCourseProduct({},'learner')).toEqual({ cancelled:true });
});
test('pending store approval does not claim confirmed access', async () => {
  Purchases.purchaseStoreProduct.mockRejectedValue({ code:'20' }); expect(await purchaseCourseProduct({},'learner')).toEqual({ cancelled:false, pending:true });
});
test('already owned products restore instead of charging again', async () => {
  Purchases.purchaseStoreProduct.mockRejectedValue({ code:'6' }); expect((await purchaseCourseProduct({},'learner')).restored).toBe(true); expect(Purchases.restorePurchases).toHaveBeenCalledTimes(1);
});
test('restore binds the signed-in account', async () => {
  await restoreCourseProducts('learner'); expect(Purchases.logIn).toHaveBeenCalledWith({ appUserID:'learner' }); expect(Purchases.restorePurchases).toHaveBeenCalledTimes(1);
});


test('existing faculty enrollment rights do not produce a store charge', () => {
  const course = { is_premium:true, premium_price:3 };
  expect(needsCoursePurchase({ role:'student' },course)).toBe(true);
  for (const role of ['faculty','elder','admin']) expect(needsCoursePurchase({ role },course)).toBe(false);
});
