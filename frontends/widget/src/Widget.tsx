/**
 * Widget — Chat-Button + Chat-Fenster + DSGVO-Consent-Gate.
 *
 * What:    Main widget shell managing open/close and consent state.
 * Does:    Shows ConsentBanner on first open; only renders ChatWindow after consent.
 *          Persists consent decision in sessionStorage for the browser session.
 * Why:     Art. 6/7 DSGVO + TTDSG § 25 require explicit consent before any
 *          personal data processing. WebSocket MUST NOT connect before consent.
 * Who:     main.tsx mounts this as the React root.
 * Depends: React, ChatWindow, ConsentBanner, WidgetConfig
 */

import { useState } from 'react';
import { ChatWindow } from './ChatWindow';
import { ConsentBanner } from './ConsentBanner';
import type { WidgetConfig } from './lib/config';

const CONSENT_KEY = 'lisa_consent_v1';

interface WidgetProps {
  config: WidgetConfig;
  visitorId: string;
}

export function Widget({ config, visitorId }: WidgetProps) {
  const [open, setOpen] = useState(false);
  // Initialize from sessionStorage so consent persists across open/close within session
  const [consentGiven, setConsentGiven] = useState(
    () => sessionStorage.getItem(CONSENT_KEY) === '1',
  );

  const handleAccept = () => {
    sessionStorage.setItem(CONSENT_KEY, '1');
    setConsentGiven(true);
  };

  const handleDecline = () => {
    setOpen(false);
  };

  return (
    <>
      {open && (
        <div className="widget-window">
          {consentGiven ? (
            <ChatWindow config={config} visitorId={visitorId} />
          ) : (
            <ConsentBanner
              config={config}
              onAccept={handleAccept}
              onDecline={handleDecline}
            />
          )}
        </div>
      )}
      <button
        className="widget-button"
        style={{ '--primary-color': config.primaryColor } as React.CSSProperties}
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? 'Chat schließen' : 'Chat öffnen'}
      >
        {open ? '✕' : '💬'}
      </button>
    </>
  );
}
