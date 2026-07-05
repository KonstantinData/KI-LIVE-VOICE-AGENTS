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
          <div className="widget-header-title">{config.agentName} - Küchen Expert Assistent</div>
          <div className="widget-header-subtitle">Datenschutzhinweis</div>
        </div>
      </div>

      <div className="consent-body">
        <p className="consent-intro">
          <strong>{config.agentName}</strong> ist ein{' '}
          <strong>KI-Assistent (kein Mensch)</strong>, der Ihnen bei Küchen- und
          Einrichtungsfragen hilft.
        </p>

        <p className="consent-section-title">Was wir verarbeiten:</p>
        <ul className="consent-list">
          <li>Nachrichteninhalte Ihrer Chat-Konversation</li>
          <li>Im Sprachmodus: Mikrofon-Audio zur Live-Verarbeitung</li>
          <li>Im Sprachmodus: finale Transkripte zur Gesprächsdokumentation</li>
          <li>Projektdaten, die Sie {config.agentName} freiwillig mitteilen</li>
          <li>
            Kontaktdaten wie Name, E-Mail-Adresse und Telefonnummer nur dann,
            wenn Sie diese im separaten Kontaktformular manuell eingeben
          </li>
          <li>
            Hochgeladene Projektdateien wie Fotos, PNG/JPEG-Bilder oder PDFs,
            wenn Sie diese freiwillig zur Küchenberatung bereitstellen
          </li>
          <li>Eine inhaltliche Zusammenfassung für Rückmeldung und Beratung</li>
          <li>Anonyme Besucherkennung (Sitzungs-ID)</li>
          <li>Zeitstempel der Nachrichten</li>
        </ul>

        <p className="consent-section-title">Kontaktdaten im Sprachmodus:</p>
        <p className="consent-text">
          Name, E-Mail-Adresse und Telefonnummer werden aus Datenschutzgründen
          nicht per Sprache abgefragt. Wenn eine Kontaktaufnahme gewünscht ist,
          erfolgt die Eingabe manuell über ein separates Formular im Widget.
          Diese Kontaktdaten werden nicht an OpenAI übermittelt, sondern direkt
          an Mein Küchenexperte gesendet und in der von Mein Küchenexperte
          betriebenen Serverumgebung zur Bearbeitung Ihrer Anfrage gespeichert.
        </p>

        <p className="consent-section-title">Projektdateien &amp; Fotos:</p>
        <p className="consent-text">
          Sie können optional Fotos oder PDF-Unterlagen hochladen, damit KEA und
          das Team Ihre bestehende Raumsituation besser einordnen können.
          Hochgeladene Dateien werden privat gespeichert und nicht öffentlich
          bereitgestellt. Wenn Sie der KI-gestützten Einordnung zustimmen, können
          Bildinhalte zur Projektberatung automatisiert zusammengefasst werden.
        </p>

        <p className="consent-section-title">Rechtsgrundlage &amp; Speicherdauer:</p>
        <p className="consent-text">
          Verarbeitung auf Grundlage Ihrer Einwilligung (Art. 6 Abs. 1 lit. a DSGVO).
          Daten werden nach <strong>90 Tagen</strong> automatisch gelöscht, sofern
          keine gesetzliche Aufbewahrungspflicht oder weitere Geschäftsbeziehung
          entgegensteht.
        </p>

        <p className="consent-text">
          Mikrofonzugriff erfolgt erst nach einem zusätzlichen Klick im Sprachmodus.
          Roh-Audio wird standardmäßig nicht gespeichert.
          Für eine E-Mail-Bestätigung kann ein eingesetzter E-Mail-Dienstleister
          eingebunden werden; Details dazu finden Sie in der Datenschutzerklärung.
          Sie können Ihre Einwilligung jederzeit mit Wirkung für die Zukunft widerrufen.
          Kontakt &amp;
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
        <button className="consent-btn consent-btn--accept" onClick={onAccept}>
          Zustimmen
        </button>
      </div>
    </>
  );
}
