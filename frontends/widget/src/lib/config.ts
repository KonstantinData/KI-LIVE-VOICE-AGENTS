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
  agentSubtitle: string;
  welcomeMessage: string;
  voiceEnabled: boolean;
  uploadEnabled: boolean;
  contactFormEnabled: boolean;
  voiceConsentVersion: string;
}

interface RuntimeWidgetConfig {
  agent_name?: string;
  agent_subtitle?: string;
  welcome_message?: string;
  primary_color?: string;
  voice_enabled?: boolean;
  upload_enabled?: boolean;
  contact_form_enabled?: boolean;
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

function explicitAttribute(
  script: HTMLOrSVGScriptElement | null,
  name: string,
): string | null {
  if (!script?.hasAttribute(name)) return null;
  return script.getAttribute(name);
}

function explicitBooleanAttribute(
  script: HTMLOrSVGScriptElement | null,
  ...names: string[]
): boolean | null {
  for (const name of names) {
    const value = explicitAttribute(script, name);
    if (value === null) continue;
    return value === 'true';
  }
  return null;
}

function loadConfigFromScript(script: HTMLOrSVGScriptElement | null): WidgetConfig {
  const apiUrl = script?.getAttribute('data-api') ?? getDefaultApiUrl();
  const voiceEnabled = explicitBooleanAttribute(script, 'data-voice-enabled', 'data-voice') ?? false;
  const uploadEnabled = explicitBooleanAttribute(script, 'data-upload-enabled', 'data-upload') ?? true;
  const contactFormEnabled = explicitBooleanAttribute(script, 'data-contact-form-enabled') ?? true;

  return {
    studio: script?.getAttribute('data-studio') ?? 'default',
    apiUrl,
    apiHttpUrl: script?.getAttribute('data-api-http') ?? toHttpUrl(apiUrl),
    primaryColor: script?.getAttribute('data-color') ?? '#101921',
    accentColor: script?.getAttribute('data-accent-color') ?? '#FF9900',
    agentName: script?.getAttribute('data-agent') ?? 'KEA',
    agentSubtitle: script?.getAttribute('data-agent-subtitle') ?? 'KI-Assistent',
    welcomeMessage:
      script?.getAttribute('data-welcome') ??
      'Hallo, ich bin KEA, der Küchen Expert Assistent von Mein Küchenexperte. Möchten Sie Ihr Küchenprojekt kurz einordnen?',
    voiceEnabled,
    uploadEnabled,
    contactFormEnabled,
    voiceConsentVersion: script?.getAttribute('data-voice-consent-version') ?? 'voice-v1',
  };
}

function runtimeConfigUrl(config: WidgetConfig): string {
  const url = new URL('/widget-config/', config.apiHttpUrl);
  url.searchParams.set('studio', config.studio);
  return url.toString();
}

function runtimeConfigTimeoutMs(script: HTMLOrSVGScriptElement | null): number {
  const raw = script?.getAttribute('data-runtime-config-timeout-ms');
  const parsed = raw ? Number.parseInt(raw, 10) : 1500;
  if (!Number.isFinite(parsed)) return 1500;
  return Math.min(Math.max(parsed, 300), 5000);
}

function mergeRuntimeConfig(
  base: WidgetConfig,
  runtime: RuntimeWidgetConfig,
  script: HTMLOrSVGScriptElement | null,
): WidgetConfig {
  const explicitVoice = explicitBooleanAttribute(script, 'data-voice-enabled', 'data-voice');
  const explicitUpload = explicitBooleanAttribute(script, 'data-upload-enabled', 'data-upload');
  const explicitContactForm = explicitBooleanAttribute(script, 'data-contact-form-enabled');
  const useRuntimeTheme = script?.getAttribute('data-runtime-theme') === 'true';

  return {
    ...base,
    primaryColor:
      explicitAttribute(script, 'data-color') ??
      (useRuntimeTheme ? runtime.primary_color : undefined) ??
      base.primaryColor,
    agentName:
      explicitAttribute(script, 'data-agent') ??
      runtime.agent_name ??
      base.agentName,
    agentSubtitle:
      explicitAttribute(script, 'data-agent-subtitle') ??
      runtime.agent_subtitle ??
      base.agentSubtitle,
    welcomeMessage:
      explicitAttribute(script, 'data-welcome') ??
      runtime.welcome_message ??
      base.welcomeMessage,
    voiceEnabled:
      explicitVoice ??
      runtime.voice_enabled ??
      base.voiceEnabled,
    uploadEnabled:
      explicitUpload ??
      runtime.upload_enabled ??
      base.uploadEnabled,
    contactFormEnabled:
      explicitContactForm ??
      runtime.contact_form_enabled ??
      base.contactFormEnabled,
  };
}

export function loadConfig(): WidgetConfig {
  return loadConfigFromScript(getScriptTag());
}

export async function loadConfigAsync(): Promise<WidgetConfig> {
  const script = getScriptTag();
  const base = loadConfigFromScript(script);
  if (script?.getAttribute('data-runtime-config') === 'false') return base;
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    runtimeConfigTimeoutMs(script),
  );

  try {
    const response = await fetch(runtimeConfigUrl(base), {
      headers: { Accept: 'application/json' },
      credentials: 'omit',
      signal: controller.signal,
    });
    if (!response.ok) return base;
    const runtime = (await response.json()) as RuntimeWidgetConfig;
    return mergeRuntimeConfig(base, runtime, script);
  } catch {
    return base;
  } finally {
    window.clearTimeout(timeout);
  }
}
