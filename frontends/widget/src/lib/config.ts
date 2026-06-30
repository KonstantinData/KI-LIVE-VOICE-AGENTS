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
  primaryColor: string;
  agentName: string;
  welcomeMessage: string;
}

function getScriptTag(): HTMLOrSVGScriptElement | null {
  return document.currentScript ?? document.querySelector('script[data-studio]');
}

function getDefaultApiUrl(): string {
  return import.meta.env.PROD ? 'wss://api.mein-kuechenexperte.de' : 'ws://localhost:8000';
}

export function loadConfig(): WidgetConfig {
  const script = getScriptTag();

  return {
    studio: script?.getAttribute('data-studio') ?? 'default',
    apiUrl: script?.getAttribute('data-api') ?? getDefaultApiUrl(),
    primaryColor: script?.getAttribute('data-color') ?? '#2563eb',
    agentName: script?.getAttribute('data-agent') ?? 'Lisa',
    welcomeMessage:
      script?.getAttribute('data-welcome') ??
      'Hallo! Ich bin Lisa. Wie kann ich Ihnen helfen?',
  };
}
