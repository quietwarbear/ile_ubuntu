/**
 * Platform utilities for Ile Ubuntu
 * Handles differences between web, iOS, and Android
 */

import { Capacitor } from "@capacitor/core";

export const Platform = {
  isNative: () => Capacitor.isNativePlatform(),
  isWeb: () => !Capacitor.isNativePlatform(),
  isIOS: () => Capacitor.isNativePlatform() && Capacitor.getPlatform() === "ios",
  isAndroid: () => Capacitor.isNativePlatform() && Capacitor.getPlatform() === "android",
  name: () => Capacitor.getPlatform(), // 'web' | 'ios' | 'android'
};

/**
 * Safe area inset CSS variables for native apps
 * iOS notch/home indicator, Android system bars
 */
export const applySafeAreaStyles = () => {
  if (Platform.isNative()) {
    document.documentElement.style.setProperty(
      "--safe-area-top",
      "env(safe-area-inset-top)"
    );
    document.documentElement.style.setProperty(
      "--safe-area-bottom",
      "env(safe-area-inset-bottom)"
    );
    document.documentElement.style.setProperty(
      "--safe-area-left",
      "env(safe-area-inset-left)"
    );
    document.documentElement.style.setProperty(
      "--safe-area-right",
      "env(safe-area-inset-right)"
    );
    document.body.classList.add("native-app");
  }
};

/**
 * Initialize native plugins (status bar, keyboard, etc.)
 */
export const initializeNativePlugins = async () => {
  if (!Platform.isNative()) return;

  try {
    // Status bar
    const { StatusBar, Style } = await import(
      /* webpackIgnore: true */ "@capacitor/status-bar"
    );
    await StatusBar.setStyle({ style: Style.Dark });
    if (Platform.isAndroid()) {
      await StatusBar.setBackgroundColor({ color: "#050814" });
    }
  } catch (e) {
    console.warn("[IleUbuntu] StatusBar plugin error:", e);
  }

  try {
    // Keyboard
    const { Keyboard } = await import(
      /* webpackIgnore: true */ "@capacitor/keyboard"
    );
    Keyboard.addListener("keyboardWillShow", (info) => {
      document.body.style.setProperty("--keyboard-height", `${info.keyboardHeight}px`);
      document.body.classList.add("keyboard-open");
    });
    Keyboard.addListener("keyboardWillHide", () => {
      document.body.style.setProperty("--keyboard-height", "0px");
      document.body.classList.remove("keyboard-open");
    });
  } catch (e) {
    console.warn("[IleUbuntu] Keyboard plugin error:", e);
  }

  try {
    // App lifecycle (back button on Android)
    const { App } = await import(/* webpackIgnore: true */ "@capacitor/app");
    App.addListener("backButton", ({ canGoBack }) => {
      if (canGoBack) {
        window.history.back();
      } else {
        App.exitApp();
      }
    });
  } catch (e) {
    console.warn("[IleUbuntu] App plugin error:", e);
  }
};
