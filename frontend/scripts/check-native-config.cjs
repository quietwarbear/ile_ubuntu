/* Fail before creating an app build with missing purchase configuration. */
const fs = require('fs');
const path = require('path');
const config = { ...process.env };
for (const name of ['.env.production.local', '.env.production', '.env.local', '.env']) {
  const file = path.join(__dirname, '..', name);
  if (!fs.existsSync(file)) continue;
  for (const line of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const match = /^([A-Z0-9_]+)\s*=\s*(.*)$/.exec(line.trim());
    if (match && config[match[1]] === undefined) config[match[1]] = match[2].replace(/^['"]|['"]$/g, '');
  }
}
const required = { REACT_APP_REVENUECAT_IOS_KEY: /^appl_\w+$/, REACT_APP_REVENUECAT_ANDROID_KEY: /^goog_\w+$/, REACT_APP_BACKEND_URL: /^https:\/\// };
const missing = Object.entries(required).filter(([key, pattern]) => !pattern.test(config[key] || '')).map(([key]) => key);
if (missing.length) { console.error('Native build configuration missing or invalid: ' + missing.join(', ')); process.exit(1); }
console.log('Native configuration ready: production API and both app-store SDK keys.');
