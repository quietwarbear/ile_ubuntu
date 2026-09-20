import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./App";
import { initAnalytics } from "./lib/analytics";
import { initSentry } from "./lib/sentry";

initSentry();
initAnalytics();

const rootEl = document.getElementById("root");
const app = (
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Public routes ship as client-generated snapshots (scripts/prerender.js) so
// crawlers and no-JS visitors see real content. Those snapshots are not React
// server-rendered output and do not contain hydration markers, so attempting
// to hydrate them produces React error #418. Preserve the snapshot until the
// bundle is ready, then replace it with a normal client render.
if (rootEl.hasChildNodes()) rootEl.innerHTML = "";
ReactDOM.createRoot(rootEl).render(app);
