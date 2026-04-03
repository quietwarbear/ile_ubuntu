# Ile Ubuntu - Native App Deployment Guide

## Overview
Ile Ubuntu uses Capacitor to wrap the React web app for iOS and Android distribution.
Subscriptions are handled by RevenueCat (native) and Stripe (web fallback).

## App Configuration
- **App ID**: `com.ubuntumarket.ileubuntu`
- **App Name**: Ile Ubuntu
- **Web Dir**: `build`
- **Domain**: ile-ubuntu.org

## Prerequisites
- Node.js 18+ and Yarn
- Xcode 15+ (for iOS)
- Android Studio (for Android)
- Apple Developer Account
- Google Play Console access
- RevenueCat account

## Initial Setup

### 1. Install Dependencies
```bash
cd frontend
yarn install
```

### 2. Build the Web App
```bash
yarn build
```

### 3. Initialize Capacitor Platforms
```bash
npx cap add ios
npx cap add android
npx cap sync
```

## Environment Variables
Add these to your `.env` file:
```
REACT_APP_REVENUECAT_IOS_KEY=appl_your_ios_key_here
REACT_APP_REVENUECAT_ANDROID_KEY=goog_your_android_key_here
REACT_APP_BACKEND_URL=https://ile-ubuntu.org
```

## Subscription Products

### App Store (iOS)
Create these in App Store Connect under a "Ile Ubuntu Plans" subscription group:

| Product ID | Display Name | Price |
|---|---|---|
| com.ileubuntu.scholar.monthly | Scholar Monthly | $19.99/mo |
| com.ileubuntu.scholar.annual | Scholar Annual | $199.99/yr |
| com.ileubuntu.elder.monthly | Elder Circle Monthly | $49.99/mo |
| com.ileubuntu.elder.annual | Elder Circle Annual | $499.99/yr |

### Google Play (Android)
Create these in Play Console under Monetization > Subscriptions:

| Product ID | Base Plan | Price |
|---|---|---|
| ile_ubuntu_scholar | scholar-monthly | $19.99/mo |
| ile_ubuntu_scholar | scholar-yearly | $199.99/yr |
| ile_ubuntu_elder | elder-monthly | $49.99/mo |
| ile_ubuntu_elder | elder-yearly | $499.99/yr |

### RevenueCat Setup
1. Create a new project "Ile Ubuntu" in RevenueCat
2. Add iOS and Android apps
3. Create entitlements: `scholar_access`, `elder_access`
4. Create offerings with packages mapped to store products
5. Copy API keys to `.env`

## iOS Build & Deploy

### Open in Xcode
```bash
yarn build
npx cap sync ios
npx cap open ios
```

### In Xcode:
1. Set signing team and bundle ID (`com.ubuntumarket.ileubuntu`)
2. Set deployment target to iOS 16.0+
3. Add In-App Purchase capability
4. Add Push Notifications capability
5. Archive → Distribute to App Store

### Splash Screen (iOS)
Replace the default splash screen assets in `ios/App/App/Assets.xcassets/Splash.imageset/`

### App Icons (iOS)
Replace icons in `ios/App/App/Assets.xcassets/AppIcon.appiconset/`

## Android Build & Deploy

### Open in Android Studio
```bash
yarn build
npx cap sync android
npx cap open android
```

### In Android Studio:
1. Update `android/app/build.gradle` with signing config
2. Set minSdkVersion to 24
3. Build → Generate Signed Bundle (AAB)
4. Upload to Google Play Console

### Splash Screen (Android)
Update `android/app/src/main/res/values/styles.xml` and splash drawable

## Development Workflow
```bash
# Web development
yarn start

# Build and sync to mobile
yarn build:mobile

# Open iOS
npx cap open ios

# Open Android
npx cap open android

# Live reload (dev only)
npx cap run ios --livereload --external
npx cap run android --livereload --external
```

## Subscription Flow

### Web (Stripe)
1. User selects tier + billing period
2. Frontend calls `/api/subscriptions/checkout`
3. Redirects to Stripe Checkout
4. On success, backend updates user tier

### Native (RevenueCat)
1. User selects tier + billing period
2. Frontend calls RevenueCat `makePurchase()`
3. On success, frontend calls `/api/subscriptions/activate-mobile`
4. Backend updates user tier
5. RevenueCat handles renewals, cancellations, refunds via webhooks

## Notes
- Explorer tier is always free (no store product needed)
- Faculty, Elder, and Admin roles bypass all tier restrictions
- The `tier_gating.py` middleware enforces access control server-side
