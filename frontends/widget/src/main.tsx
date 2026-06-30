/**
 * Entry Point — Mountet das Widget in einem Shadow DOM.
 *
 * Shadow DOM isoliert das Widget-CSS von der Kunden-Website.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { Widget } from './Widget';
import { loadConfig } from './lib/config';
import widgetStyles from './styles/widget.css?inline';

function generateVisitorId(): string {
  const key = 'ki_team_visitor_id';
  let id = sessionStorage.getItem(key);
  if (!id) {
    id = `v_${Math.random().toString(36).slice(2)}_${Date.now()}`;
    sessionStorage.setItem(key, id);
  }
  return id;
}

function mount(): void {
  const config = loadConfig();
  const visitorId = generateVisitorId();

  // Container und Shadow DOM erstellen
  const container = document.createElement('div');
  container.id = 'ki-team-widget-root';
  document.body.appendChild(container);

  const shadow = container.attachShadow({ mode: 'open' });
  const mountPoint = document.createElement('div');
  shadow.appendChild(mountPoint);

  // CSS in Shadow DOM laden
  const style = document.createElement('style');
  style.textContent = widgetStyles;
  shadow.appendChild(style);

  ReactDOM.createRoot(mountPoint).render(
    <React.StrictMode>
      <Widget config={config} visitorId={visitorId} />
    </React.StrictMode>,
  );
}

// Auto-Mount wenn DOM bereit ist
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mount);
} else {
  mount();
}
