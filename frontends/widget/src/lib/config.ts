/**
 * Widget-Konfiguration aus data-Attributen des Script-Tags.
 *
 * Einbindung:
 * <script
 *   src="https://widget.mein-kuechenexperte.de/v1/loader.js"
 *   data-studio="mein-kuechenexperte"
 *   data-api="wss://api.mein-kuechenexperte.de"
 * ></script>
 */

export interface WidgetConfig {
  studio: string;
  apiUrl: string;
  apiHttpUrl: string;
  primaryColor: string;
  accentColor: string;
  agentName: string;
  welcomeMessage: string;
  voiceEnabled: boolean;
  voiceConsentVersion: string;
}

function getScriptTag(): HTMLOrSVGScriptElement | null {
  return document.currentScript ?? document.querySelector('script[data-studio]');
}

function getDefaultApiUrl(): string {
  return import.meta.env.PROD ? 'wss://api.mein-kuechenexperte.de' : 'ws://localhost:8000';
}

function toHttpUrl(url: string): string {
  if (url.startsWith('wss://')) return url.replace('wss://', 'https://');
  if (url.startsWith('ws://')) return url.replace('ws://', 'http://');
  return url.replace(/\/$/, '');
}

export function loadConfig(): WidgetConfig {
  const script = getScriptTag();
  const apiUrl = script?.getAttribute('data-api') ?? getDefaultApiUrl();
  const voiceEnabled =
    script?.getAttribute('data-voice-enabled') === 'true' ||
    script?.getAttribute('data-voice') === 'true';

  return {
    studio: script?.getAttribute('data-studio') ?? 'default',
    apiUrl,
    apiHttpUrl: script?.getAttribute('data-api-http') ?? toHttpUrl(apiUrl),
    primaryColor: script?.getAttribute('data-color') ?? '#101921',
    accentColor: script?.getAttribute('data-accent-color') ?? '#FF9900',
    agentName: script?.getAttribute('data-agent') ?? 'KEA',
    welcomeMessage:
      script?.getAttribute('data-welcome') ??
      'Hallo, ich bin KEA, der Küchen Expert Assistent von Mein Küchenexperte. Möchten Sie Ihr Küchenprojekt kurz einordnen?',
    voiceEnabled,
    voiceConsentVersion: script?.getAttribute('data-voice-consent-version') ?? 'voice-v1',
  };
}
