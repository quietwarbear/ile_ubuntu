import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./App";
import { initAnalytics } from "./lib/analytics";

initAnalytics();

const rootEl = document.getElementById("root");
const app = (
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Public routes ship as prerendered HTML (scripts/prerender.js) so crawlers
// see real content. Hydrate that snapshot for anonymous visitors; signed-in
// members skip straight to a fresh client render (their first paint is the
// app, not a flash of the marketing page the snapshot contains).
let hasSession = false;
try {
  hasSession = !!localStorage.getItem("session_id") || document.cookie.includes("session_id=");
} catch (e) { /* storage unavailable */ }

if (rootEl.hasChildNodes() && !hasSession) {
  ReactDOM.hydrateRoot(rootEl, app);
} else {
  if (rootEl.hasChildNodes()) rootEl.innerHTML = "";
  ReactDOM.createRoot(rootEl).render(app);
}
