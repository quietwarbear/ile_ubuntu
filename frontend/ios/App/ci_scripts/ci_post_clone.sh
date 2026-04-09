#!/bin/sh
set -e

# Install Node.js via nvm (Xcode Cloud doesn't include it by default)
export NVM_DIR="$HOME/.nvm"
if [ ! -d "$NVM_DIR" ]; then
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
fi
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm install 22
nvm use 22

cd $CI_PRIMARY_REPOSITORY_PATH/frontend
npm install --legacy-peer-deps

# Patch RevenueCat SPM to accept capacitor-swift-pm 8.x (it ships requiring 7.x)
sed -i '' 's/from: "7.0.0"/from: "8.0.0"/' node_modules/@revenuecat/purchases-capacitor/Package.swift

GENERATE_SOURCEMAP=false CI=false npm run build
npx cap sync ios
