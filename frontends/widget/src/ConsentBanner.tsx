/**
 * ConsentBanner — DSGVO/TTDSG consent gate before WebSocket connect.
 *
 * What:    Consent banner displayed before the chat starts.
 * Does:    Informs users about KI processing; blocks chat until explicit consent.
 * Why:     Art. 6 Abs. 1 + Art. 7 DSGVO + TTDSG § 25 — consent required before
 *          any personal data processing (visitor ID, messages, timestamps).
 *          EU AI Act Art. 50 — must disclose AI nature before interaction starts.
 * Who:     Widget.tsx renders this when consentGiven === false.
 * Depends: React, WidgetConfig
 */

import type { WidgetConfig } from './lib/config';

interface ConsentBannerProps {
  config: WidgetConfig;
  onAccept: () => void;
  onDecline: () => void;
}

export function ConsentBanner({ config, onAccept, onDecline }: ConsentBannerProps) {
  return (
    <>
      <div className="widget-header">
        <div>
          <div className="widget-header-title">{config.agentName} — KI-Assistentin</div>
          <div className="widget-header-subtitle">Datenschutzhinweis</div>
        </div>
      </div>

      <div className="consent-body">
        <p className="consent-intro">
          <strong>{config.agentName}</strong> ist eine{' '}
          <strong>KI-Assistentin (kein Mensch)</strong>, die Ihnen bei Küchen- und
          Einrichtungsfragen hilft.
        </p>

        <p className="consent-section-title">Was wir verarbeiten:</p>
        <ul className="consent-list">
          <li>Nachrichteninhalte Ihrer Chat-Konversation</li>
          <li>Anonyme Besucherkennung (Sitzungs-ID)</li>
          <li>Zeitstempel der Nachrichten</li>
        </ul>

        <p className="consent-section-title">Rechtsgrundlage &amp; Speicherdauer:</p>
        <p className="consent-text">
          Verarbeitung auf Grundlage Ihrer Einwilligung (Art. 6 Abs. 1 lit. a DSGVO).
          Daten werden nach <strong>90 Tagen</strong> automatisch gelöscht.
        </p>

        <p className="consent-text">
          Sie können Ihre Einwilligung jederzeit widerrufen. Kontakt &amp;
          Datenschutzerklärung:{' '}
          <a
            className="consent-link"
            href="/datenschutz"
            target="_blank"
            rel="noopener noreferrer"
          >
            Datenschutz
          </a>
        </p>
      </div>

      <div className="consent-actions">
        <button className="consent-btn consent-btn--decline" onClick={onDecline}>
          Ablehnen
        </button>
        <button
          className="consent-btn consent-btn--accept"
          style={{ '--primary-color': config.primaryColor } as React.CSSProperties}
          onClick={onAccept}
        >
          Zustimmen &amp; Chatten
        </button>
      </div>
    </>
  );
}
