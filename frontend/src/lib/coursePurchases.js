import { Capacitor } from '@capacitor/core';
import { initializeRevenueCat } from './revenuecat';

export const coursePurchasePlatform = () => Capacitor.isNativePlatform() ? Capacitor.getPlatform() : null;

// Match the existing server enrollment policy: platform faculty+ can enroll
// without buying. Do not send those accounts to a store charge sheet.
export const needsCoursePurchase = (user, course) => !!(coursePurchasePlatform() && course?.is_premium && course.premium_price > 0 && !['faculty', 'elder', 'admin'].includes(user?.role));

async function purchasesFor(userId) {
  if (!userId || !coursePurchasePlatform()) throw new Error('Sign in to purchase this course.');
  await initializeRevenueCat();
  const { Purchases } = await import('@revenuecat/purchases-capacitor');
  await Purchases.logIn({ appUserID: userId });
  const current = await Purchases.getAppUserID();
  if (current.appUserID !== userId) throw new Error('Please sign in again before purchasing.');
  return Purchases;
}

export async function loadCourseProduct(productId, userId) {
  const Purchases = await purchasesFor(userId);
  // Direct products keep course purchases independent of the membership offering.
  const { products } = await Purchases.getProducts({ productIdentifiers: [productId], type: 'NON_SUBSCRIPTION' });
  const product = products.find(p => p.identifier === productId);
  if (!product) throw new Error('This course is not available to purchase in this store yet.');
  return product;
}

export async function purchaseCourseProduct(product, userId) {
  const Purchases = await purchasesFor(userId);
  try {
    const result = await Purchases.purchaseStoreProduct({ product });
    return { cancelled: false, customerInfo: result.customerInfo };
  } catch (error) {
    if (error.userCancelled || String(error.code) === '1') return { cancelled: true };
    if (String(error.code) === '20') return { cancelled: false, pending: true };
    if (String(error.code) === '6') {
      await Purchases.restorePurchases();
      return { cancelled: false, restored: true };
    }
    throw error;
  }
}

export async function restoreCourseProducts(userId) {
  const Purchases = await purchasesFor(userId);
  return Purchases.restorePurchases();
}
