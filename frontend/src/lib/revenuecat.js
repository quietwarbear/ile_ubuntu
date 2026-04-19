/**
 * RevenueCat integration for iOS/Android in-app purchases via Capacitor
 * Falls back gracefully on web platforms (where Stripe handles payments)
 */

import { Capacitor } from "@capacitor/core";

const REVENUECAT_IOS_KEY = process.env.REACT_APP_REVENUECAT_IOS_KEY;
const REVENUECAT_ANDROID_KEY = process.env.REACT_APP_REVENUECAT_ANDROID_KEY;

// Map tier names to RevenueCat product IDs
export const TIER_TO_PRODUCT_ID = {
  scholar: {
    monthly: "com.ileubuntu.scholar.monthly",
    annual: "com.ileubuntu.scholar.annual",
  },
  elder_circle: {
    monthly: "com.ileubuntu.elder.monthly",
    annual: "com.ileubuntu.elder.annual",
  },
};

// Reverse lookup: product ID → { tier, period }
export const PRODUCT_ID_TO_TIER = {};
Object.entries(TIER_TO_PRODUCT_ID).forEach(([tier, periods]) => {
  Object.entries(periods).forEach(([period, productId]) => {
    PRODUCT_ID_TO_TIER[productId] = { tier, period };
  });
});

let revenueCatInitialized = false;

/**
 * Get the correct RevenueCat API key for the current platform
 */
const getApiKey = () => {
  const platform = Capacitor.getPlatform();
  if (platform === "ios") return REVENUECAT_IOS_KEY;
  if (platform === "android") return REVENUECAT_ANDROID_KEY;
  return null;
};

/**
 * Initialize RevenueCat SDK (iOS/Android only)
 * Safe to call on web — will no-op
 */
export const initializeRevenueCat = async () => {
  if (revenueCatInitialized) return;

  const isNative = Capacitor.isNativePlatform();
  if (!isNative) {
    console.log("[IleUbuntu] RevenueCat: skipping init (not native)");
    return;
  }

  const apiKey = getApiKey();
  if (!apiKey) {
    console.warn("[IleUbuntu] RevenueCat: API key not configured for", Capacitor.getPlatform());
    return;
  }

  try {
    const { Purchases } = await import(
      "@revenuecat/purchases-capacitor"
    );

    await Purchases.configure({
      apiKey,
      appUserID: null, // Will be set after login via syncRevenueCatUser
    });

    revenueCatInitialized = true;
    console.log("[IleUbuntu] RevenueCat initialized successfully on", Capacitor.getPlatform());
  } catch (error) {
    console.error("[IleUbuntu] Failed to initialize RevenueCat:", error);
  }
};

/**
 * Fetch offerings from RevenueCat (native only)
 * Returns structured offerings or null on web/error
 */
export const fetchOfferings = async () => {
  if (!Capacitor.isNativePlatform() || !revenueCatInitialized) {
    return null;
  }

  try {
    const { Purchases } = await import(
      "@revenuecat/purchases-capacitor"
    );
    const offerings = await Purchases.getOfferings();
    return offerings;
  } catch (error) {
    console.error("[IleUbuntu] Error fetching RevenueCat offerings:", error);
    return null;
  }
};

/**
 * Get package (product) from offerings by product ID
 * Native only
 */
export const getPackageByProductId = async (productId) => {
  if (!Capacitor.isNativePlatform() || !revenueCatInitialized) {
    return null;
  }

  try {
    const { Purchases } = await import(
      "@revenuecat/purchases-capacitor"
    );
    const offerings = await Purchases.getOfferings();

    if (offerings?.current?.availablePackages) {
      return offerings.current.availablePackages.find(
        (pkg) => pkg.product.identifier === productId
      );
    }

    return null;
  } catch (error) {
    console.error("[IleUbuntu] Error fetching package:", error);
    return null;
  }
};

/**
 * Make purchase on iOS/Android
 * Handles transaction and receipt validation
 */
export const makePurchase = async (productId) => {
  if (!Capacitor.isNativePlatform() || !revenueCatInitialized) {
    throw new Error("RevenueCat purchase not available on this platform");
  }

  try {
    const { Purchases } = await import(
      "@revenuecat/purchases-capacitor"
    );

    const pkg = await getPackageByProductId(productId);
    if (!pkg) {
      throw new Error(`Product ${productId} not found in offerings`);
    }

    const purchaseResult = await Purchases.purchasePackage({ aPackage: pkg });

    if (purchaseResult?.customerInfo?.entitlements?.active) {
      return {
        success: true,
        customerInfo: purchaseResult.customerInfo,
        message: "Purchase successful",
      };
    }

    return {
      success: false,
      message: "Purchase failed or cancelled",
    };
  } catch (error) {
    // User cancelled
    if (error.code === "1" || error.message?.includes("cancelled")) {
      return { success: false, message: "Purchase cancelled", cancelled: true };
    }
    console.error("[IleUbuntu] Purchase error:", error);
    throw error;
  }
};

/**
 * Get current customer info (active subscriptions)
 * Native only
 */
export const getCustomerInfo = async () => {
  if (!Capacitor.isNativePlatform() || !revenueCatInitialized) {
    return null;
  }

  try {
    const { Purchases } = await import(
      "@revenuecat/purchases-capacitor"
    );
    const info = await Purchases.getCustomerInfo();
    return info?.customerInfo || null;
  } catch (error) {
    console.error("[IleUbuntu] Error getting customer info:", error);
    return null;
  }
};

/**
 * Restore purchases (for users who reinstall or switch devices)
 * Native only
 */
export const restorePurchases = async () => {
  if (!Capacitor.isNativePlatform() || !revenueCatInitialized) {
    throw new Error("Restore not available on this platform");
  }

  try {
    const { Purchases } = await import(
      "@revenuecat/purchases-capacitor"
    );
    const result = await Purchases.restorePurchases();
    return result?.customerInfo || null;
  } catch (error) {
    console.error("[IleUbuntu] Error restoring purchases:", error);
    throw error;
  }
};

/**
 * Sync customer ID with RevenueCat (call after user login)
 * Native only
 */
export const syncRevenueCatUser = async (userId) => {
  if (!Capacitor.isNativePlatform() || !revenueCatInitialized) {
    return;
  }

  try {
    const { Purchases } = await import(
      "@revenuecat/purchases-capacitor"
    );
    await Purchases.logIn({ appUserID: userId });
    console.log("[IleUbuntu] RevenueCat user synced:", userId);
  } catch (error) {
    console.error("[IleUbuntu] Error syncing RevenueCat user:", error);
  }
};

/**
 * Log out from RevenueCat (call on user logout)
 * Native only
 */
export const logOutRevenueCat = async () => {
  if (!Capacitor.isNativePlatform() || !revenueCatInitialized) {
    return;
  }

  try {
    const { Purchases } = await import(
      "@revenuecat/purchases-capacitor"
    );
    await Purchases.logOut();
    console.log("[IleUbuntu] RevenueCat user logged out");
  } catch (error) {
    console.error("[IleUbuntu] Error logging out RevenueCat:", error);
  }
};

/**
 * Check if running on a native platform (iOS or Android)
 */
export const isNative = () => Capacitor.isNativePlatform();

/**
 * Check if running on iOS
 */
export const isIOS = () =>
  Capacitor.isNativePlatform() && Capacitor.getPlatform() === "ios";

/**
 * Check if running on Android
 */
export const isAndroid = () =>
  Capacitor.isNativePlatform() && Capacitor.getPlatform() === "android";
