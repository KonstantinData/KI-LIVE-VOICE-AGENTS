/**
 * VoiceControls — Browser WebRTC voice mode for KEA.
 *
 * What: Starts/stops an OpenAI Realtime voice session after consent.
 * Does: Gets an ephemeral client secret from the backend and connects by WebRTC.
 * Why: The standard OpenAI API key must stay server-side; microphone capture
 *      must start only after explicit user action.
 * Who: ChatWindow renders this when data-voice-enabled is true.
 */

import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import type { WidgetConfig } from './lib/config';
import { hasContactIntent } from './lib/contactIntent';
import { buildProjectSummary } from './lib/projectSummary';

type VoiceState = 'idle' | 'connecting' | 'live' | 'paused' | 'error';
type AddressMode = 'du' | 'sie';
type VoiceMessageRole = 'user' | 'assistant';

interface VoiceMessage {
  id: string;
  role: VoiceMessageRole;
  content: string;
}

interface VoiceControlsProps {
  config: WidgetConfig;
  visitorId: string;
  onConversationReady?: (conversationId: string) => void;
}

interface VoiceSessionResponse {
  client_secret: string;
  conversation_id: string;
  model: string;
  voice: string;
  voice_session_id: string;
}

type TranscriptRole = 'user' | 'assistant';

interface ContactFormData {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  best_reachability: string;
  additional_notes: string;
  contact_consent_confirmed: boolean;
}

function makeVoiceSessionId(): string {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `voice_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}

function waitForIceGatheringComplete(peer: RTCPeerConnection): Promise<void> {
  if (peer.iceGatheringState === 'complete') {
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    const timeout = window.setTimeout(() => {
      peer.removeEventListener('icegatheringstatechange', handleStateChange);
      resolve();
    }, 2500);

    function handleStateChange() {
      if (peer.iceGatheringState === 'complete') {
        window.clearTimeout(timeout);
        peer.removeEventListener('icegatheringstatechange', handleStateChange);
        resolve();
      }
    }

    peer.addEventListener('icegatheringstatechange', handleStateChange);
  });
}

export function VoiceControls({ config, visitorId, onConversationReady }: VoiceControlsProps) {
  const [state, setState] = useState<VoiceState>('idle');
  const [status, setStatus] = useState('Bitte wählen Sie zuerst Du oder Sie.');
  const [addressMode, setAddressMode] = useState<AddressMode | null>(null);
  const [showContactForm, setShowContactForm] = useState(false);
  const [contactStatus, setContactStatus] = useState('');
  const [contactForm, setContactForm] = useState<ContactFormData>({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    best_reachability: '',
    additional_notes: '',
    contact_consent_confirmed: false,
  });
  const [voiceMessages, setVoiceMessages] = useState<VoiceMessage[]>([
    {
      id: 'initial-greeting',
      role: 'assistant',
      content: `Hallo, ich bin ${config.agentName}, der Küchen Expert Assistent von Mein Küchenexperte. Wie darf ich Sie hier im Chat ansprechen: per Du oder per Sie?`,
    },
  ]);
  const projectSummary = buildProjectSummary(voiceMessages);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dcRef = useRef<RTCDataChannel | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const conversationIdRef = useRef<string | null>(null);
  const voiceSessionIdRef = useRef<string | null>(null);
  const storedTranscriptEventsRef = useRef<Set<string>>(new Set());
  const addressModeRef = useRef<AddressMode | null>(null);
  const greetingSentRef = useRef(false);
  const pausedRef = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const cleanup = (
    nextState: VoiceState = 'idle',
    nextStatus = addressModeRef.current
      ? 'Sprachmodus bereit.'
      : 'Bitte wählen Sie zuerst Du oder Sie.',
  ) => {
    void endVoiceSession();
    dcRef.current?.close();
    dcRef.current = null;
    pcRef.current?.close();
    pcRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    audioRef.current?.remove();
    audioRef.current = null;
    conversationIdRef.current = null;
    voiceSessionIdRef.current = null;
    storedTranscriptEventsRef.current = new Set();
    greetingSentRef.current = false;
    pausedRef.current = false;
    setState(nextState);
    setStatus(nextStatus);
  };

  useEffect(() => () => cleanup(), []);

  useEffect(() => {
    addressModeRef.current = addressMode;
  }, [addressMode]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [voiceMessages.length]);

  const appendVoiceMessage = (role: VoiceMessageRole, content: string) => {
    const normalized = content.trim();
    if (!normalized) return;
    if (hasContactIntent(normalized)) {
      setShowContactForm(true);
    }
    setVoiceMessages((prev) => [
      ...prev,
      {
        id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        role,
        content: normalized,
      },
    ]);
  };

  const chooseAddressMode = (mode: AddressMode) => {
    setAddressMode(mode);
    addressModeRef.current = mode;
    appendVoiceMessage('user', mode === 'du' ? 'Bitte per Du.' : 'Bitte per Sie.');
    appendVoiceMessage(
      'assistant',
      mode === 'du'
        ? `Hallo, ich bin ${config.agentName}. Dann bleiben wir gerne beim Du. Wenn du möchtest, kannst du jetzt das Gespräch starten.`
        : `Hallo, ich bin ${config.agentName}. Dann bleiben wir gerne beim Sie. Wenn Sie möchten, können Sie jetzt das Gespräch starten.`,
    );
    setStatus('Sprachmodus bereit.');
  };

  const createVoiceSession = async (): Promise<VoiceSessionResponse> => {
    const response = await fetch(`${config.apiHttpUrl}/voice/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        studio: config.studio,
        visitor_id: visitorId,
        consent_granted: true,
        consent_version: config.voiceConsentVersion,
        session_id: makeVoiceSessionId(),
        address_mode: addressModeRef.current ?? 'sie',
      }),
    });
    if (!response.ok) {
      throw new Error(`voice_session_failed_${response.status}`);
    }
    return response.json() as Promise<VoiceSessionResponse>;
  };

  const persistTranscript = async (
    role: TranscriptRole,
    transcript: unknown,
    providerEventId: unknown,
    itemId: unknown,
  ) => {
    const text = typeof transcript === 'string' ? transcript.trim() : '';
    const conversationId = conversationIdRef.current;
    const voiceSessionId = voiceSessionIdRef.current;
    if (!text || !conversationId || !voiceSessionId || pausedRef.current) return;

    const eventKey =
      typeof providerEventId === 'string' && providerEventId
        ? providerEventId
        : `${role}:${typeof itemId === 'string' ? itemId : ''}:${text}`;
    if (storedTranscriptEventsRef.current.has(eventKey)) return;
    storedTranscriptEventsRef.current.add(eventKey);
    appendVoiceMessage(role, text);

    try {
      const response = await fetch(`${config.apiHttpUrl}/voice/transcript`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          studio: config.studio,
          visitor_id: visitorId,
          conversation_id: conversationId,
          voice_session_id: voiceSessionId,
          role,
          transcript: text,
          provider_event_id: typeof providerEventId === 'string' ? providerEventId : null,
          item_id: typeof itemId === 'string' ? itemId : null,
          consent_granted: true,
          consent_version: config.voiceConsentVersion,
        }),
      });
      if (!response.ok) {
        storedTranscriptEventsRef.current.delete(eventKey);
      }
    } catch {
      storedTranscriptEventsRef.current.delete(eventKey);
    }
  };

  const endVoiceSession = async () => {
    const conversationId = conversationIdRef.current;
    const voiceSessionId = voiceSessionIdRef.current;
    if (!conversationId || !voiceSessionId) return;

    try {
      await fetch(`${config.apiHttpUrl}/voice/session/end`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          studio: config.studio,
          visitor_id: visitorId,
          conversation_id: conversationId,
          voice_session_id: voiceSessionId,
          close_reason: 'user_ended',
          consent_granted: true,
          consent_version: config.voiceConsentVersion,
        }),
        keepalive: true,
      });
    } catch {
      // The voice UI must close even if finalization cannot be reached.
    }
  };

  const submitContactForm = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const conversationId = conversationIdRef.current;
    const voiceSessionId = voiceSessionIdRef.current;
    const projectSummary = buildProjectSummary(voiceMessages);
    if (!conversationId || !voiceSessionId) {
      setContactStatus('Bitte starten Sie zuerst kurz den Sprachmodus, damit wir die Anfrage zuordnen können.');
      return;
    }
    if (!contactForm.contact_consent_confirmed) {
      setContactStatus('Bitte bestätigen Sie die Datenschutzhinweise.');
      return;
    }

    setContactStatus('Kontaktdaten werden sicher übermittelt...');
    try {
      const response = await fetch(`${config.apiHttpUrl}/voice/contact-handoff`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          studio: config.studio,
          visitor_id: visitorId,
          conversation_id: conversationId,
          voice_session_id: voiceSessionId,
          first_name: contactForm.first_name,
          last_name: contactForm.last_name,
          email: contactForm.email,
          phone: contactForm.phone || null,
          best_reachability: contactForm.best_reachability || null,
          project_summary: projectSummary,
          additional_notes: contactForm.additional_notes || null,
          contact_consent_confirmed: contactForm.contact_consent_confirmed,
          consent_granted: true,
          consent_version: config.voiceConsentVersion,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.success) {
        setContactStatus('Die Kontaktdaten konnten gerade nicht übermittelt werden. Bitte versuchen Sie es später erneut.');
        return;
      }
      const sentText = payload.emails_sent
        ? 'Ihre Anfrage wurde übermittelt. Die Bestätigungs-E-Mail ist unterwegs.'
        : 'Ihre Anfrage wurde gespeichert. Die E-Mail-Bestätigung wird intern nachgefasst.';
      setContactStatus(sentText);
      appendVoiceMessage('assistant', sentText);
      setShowContactForm(false);
    } catch {
      setContactStatus('Die Kontaktdaten konnten gerade nicht übermittelt werden. Bitte versuchen Sie es später erneut.');
    }
  };

  const updateContactField = (
    field: keyof ContactFormData,
    value: string | boolean,
  ) => {
    setContactForm((current) => ({ ...current, [field]: value }));
  };

  const connectRealtime = async (session: VoiceSessionResponse, stream: MediaStream) => {
    const pc = new RTCPeerConnection();
    pcRef.current = pc;

    const audio = document.createElement('audio');
    audio.autoplay = true;
    audio.setAttribute('playsinline', 'true');
    audio.style.display = 'none';
    audioRef.current = audio;
    document.body.appendChild(audio);

    pc.ontrack = (event) => {
      audio.srcObject = event.streams[0];
    };
    pc.onconnectionstatechange = () => {
      if (pc.connectionState === 'failed' || pc.connectionState === 'disconnected') {
        cleanup('error', 'Sprachverbindung unterbrochen. Textchat bleibt verfügbar.');
      }
    };

    const dc = pc.createDataChannel('oai-events');
    dcRef.current = dc;
    dc.onopen = () => {
      if (greetingSentRef.current) return;
      greetingSentRef.current = true;
      const mode = addressModeRef.current ?? 'sie';
      const instructions =
        mode === 'du'
          ? 'Die Begrüßung und Selbstvorstellung wurden im Widget bereits angezeigt. Wiederhole nicht, wer du bist. Sage nur: "Worum geht es bei deinem Küchenprojekt?"'
          : 'Die Begrüßung und Selbstvorstellung wurden im Widget bereits angezeigt. Wiederholen Sie nicht, wer Sie sind. Sagen Sie nur: "Worum geht es bei Ihrem Küchenprojekt?"';
      dc.send(JSON.stringify({ type: 'response.create', response: { instructions } }));
    };
    dc.onmessage = (event) => {
      try {
        const payload = JSON.parse(String(event.data));
        if (payload.type === 'error') {
          setState('error');
          setStatus('Sprachmodus nicht erreichbar. Textchat bleibt verfügbar.');
        }
        if (pausedRef.current) {
          return;
        }
        if (payload.type === 'input_audio_buffer.speech_started') {
          setStatus(`Ich höre zu. Sie können ${config.agentName} jederzeit unterbrechen.`);
        }
        if (payload.type === 'response.audio.delta' || payload.type === 'response.output_audio.delta') {
          setStatus(`${config.agentName} antwortet...`);
        }
        if (payload.type === 'response.done') {
          setStatus('Sprachmodus aktiv. Sie können weiter sprechen.');
        }
        if (payload.type === 'conversation.item.input_audio_transcription.completed') {
          void persistTranscript('user', payload.transcript, payload.event_id, payload.item_id);
        }
        if (payload.type === 'response.output_audio_transcript.done') {
          void persistTranscript(
            'assistant',
            payload.transcript,
            payload.event_id,
            payload.response_id,
          );
        }
      } catch {
        // Non-JSON realtime events are ignored by the compact widget UI.
      }
    };

    stream.getTracks().forEach((track) => pc.addTrack(track, stream));
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    await waitForIceGatheringComplete(pc);

    const localSdp = pc.localDescription?.sdp ?? offer.sdp ?? '';

    const realtimeResponse = await fetch('https://api.openai.com/v1/realtime/calls', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${session.client_secret}`,
        'Content-Type': 'application/sdp',
      },
      body: localSdp,
    });
    if (!realtimeResponse.ok) {
      throw new Error(`realtime_connect_failed_${realtimeResponse.status}`);
    }

    const remoteSdp = await realtimeResponse.text();
    if (!remoteSdp.trim()) {
      throw new Error('realtime_connect_failed_empty_sdp');
    }

    await pc.setRemoteDescription({
      type: 'answer',
      sdp: remoteSdp,
    });
  };

  const startVoice = async () => {
    if (!addressModeRef.current) {
      setStatus('Bitte wählen Sie zuerst Du oder Sie.');
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || !globalThis.RTCPeerConnection) {
      setState('error');
      setStatus('Dieser Browser unterstützt den Sprachmodus hier nicht.');
      return;
    }

    setState('connecting');
    setStatus('Mikrofon wird angefragt...');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;
      setStatus('Verbinde Sprachmodus...');
      const session = await createVoiceSession();
      conversationIdRef.current = session.conversation_id;
      voiceSessionIdRef.current = session.voice_session_id;
      onConversationReady?.(session.conversation_id);
      await connectRealtime(session, stream);
      pausedRef.current = false;
      setState('live');
      setStatus(`Sprachmodus aktiv. Sie können ${config.agentName} unterbrechen.`);
    } catch (error) {
      const name = error instanceof DOMException ? error.name : '';
      cleanup(
        'error',
        name === 'NotAllowedError' || name === 'SecurityError'
          ? 'Mikrofonzugriff wurde nicht erlaubt.'
          : 'Sprachmodus nicht erreichbar. Textchat bleibt verfügbar.',
      );
    }
  };

  const togglePause = () => {
    if (!streamRef.current) return;
    const paused = state !== 'paused';
    streamRef.current.getAudioTracks().forEach((track) => {
      track.enabled = !paused;
    });
    pcRef.current?.getReceivers().forEach((receiver) => {
      if (receiver.track?.kind === 'audio') {
        receiver.track.enabled = !paused;
      }
    });
    if (audioRef.current) {
      audioRef.current.muted = paused;
      if (paused) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      } else {
        void audioRef.current.play().catch(() => undefined);
      }
    }
    if (paused && dcRef.current?.readyState === 'open') {
      dcRef.current.send(JSON.stringify({ type: 'response.cancel' }));
      dcRef.current.send(JSON.stringify({ type: 'output_audio_buffer.clear' }));
    }
    pausedRef.current = paused;
    setState(paused ? 'paused' : 'live');
    setStatus(
      paused
        ? 'Gespräch pausiert. Das Mikrofon ist aus.'
        : `Gespräch läuft weiter. ${config.agentName} hört wieder zu.`,
    );
  };

  return (
    <div className={`voice-panel voice-panel--${state}`} aria-label={status} aria-live="polite">
      <div className="voice-chat-log">
        {voiceMessages.map((message) => (
          <div
            className={`voice-chat-row voice-chat-row--${message.role}`}
            key={message.id}
          >
            <div className="voice-chat-label">
              {message.role === 'assistant' ? config.agentName : 'Kunde'}
            </div>
            <div className={`message-bubble message-bubble--${message.role}`}>
              {message.content}
            </div>
          </div>
        ))}
        {!addressMode && (
          <div className="voice-tone-choice" aria-label="Anrede auswählen">
            <button
              className="voice-tone-button"
              onClick={() => chooseAddressMode('du')}
              type="button"
            >
              Du
            </button>
            <button
              className="voice-tone-button voice-tone-button--primary"
              onClick={() => chooseAddressMode('sie')}
              type="button"
            >
              Sie
            </button>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {showContactForm && (
        <form className="voice-contact-form" onSubmit={submitContactForm}>
          <div className="voice-form-grid">
            <label>
              <span>Vorname</span>
              <input
                autoComplete="given-name"
                minLength={2}
                onInput={(event) => updateContactField('first_name', event.currentTarget.value)}
                required
                type="text"
                value={contactForm.first_name}
              />
            </label>
            <label>
              <span>Nachname</span>
              <input
                autoComplete="family-name"
                minLength={2}
                onInput={(event) => updateContactField('last_name', event.currentTarget.value)}
                required
                type="text"
                value={contactForm.last_name}
              />
            </label>
          </div>
          <label>
            <span>E-Mail-Adresse</span>
            <input
              autoComplete="email"
              onInput={(event) => updateContactField('email', event.currentTarget.value)}
              required
              type="email"
              value={contactForm.email}
            />
          </label>
          <label>
            <span>Telefon optional</span>
            <input
              autoComplete="tel"
              onInput={(event) => updateContactField('phone', event.currentTarget.value)}
              type="tel"
              value={contactForm.phone}
            />
          </label>
          <label>
            <span>Beste Erreichbarkeit optional</span>
            <input
              onInput={(event) => updateContactField('best_reachability', event.currentTarget.value)}
              placeholder="z. B. werktags ab 18 Uhr"
              type="text"
              value={contactForm.best_reachability}
            />
          </label>
          <div className="voice-summary-preview">
            <span>Zusammenfassung</span>
            <p>{projectSummary}</p>
          </div>
          <label>
            <span>Weitere Hinweise optional</span>
            <textarea
              maxLength={1600}
              onInput={(event) => updateContactField('additional_notes', event.currentTarget.value)}
              rows={2}
              value={contactForm.additional_notes}
            />
          </label>
          <label className="voice-consent-row">
            <input
              checked={contactForm.contact_consent_confirmed}
              onChange={(event) => updateContactField('contact_consent_confirmed', event.currentTarget.checked)}
              required
              type="checkbox"
            />
            <span>
              Ich bin einverstanden, dass Mein Küchenexperte meine Angaben zur
              Bearbeitung meiner Anfrage, zur Kontaktaufnahme und zum Versand
              einer Zusammenfassung verarbeitet. Ich kann diese Einwilligung
              jederzeit mit Wirkung für die Zukunft widerrufen.
            </span>
          </label>
          <button className="voice-button voice-button--primary" type="submit">
            Anfrage senden
          </button>
          {contactStatus && <div className="voice-form-status">{contactStatus}</div>}
        </form>
      )}

      <div className="voice-controls">
        <span className={`voice-dot voice-dot--${state}`} />
        <button
          className="voice-button voice-button--primary"
          onClick={state === 'idle' || state === 'error' ? startVoice : () => cleanup()}
          disabled={state === 'connecting' || !addressMode}
          type="button"
        >
          {state === 'idle' || state === 'error' ? 'Sprechen starten' : 'Gespräch beenden'}
        </button>
        <button
          className="voice-button"
          onClick={togglePause}
          disabled={state !== 'live' && state !== 'paused'}
          type="button"
        >
          {state === 'paused' ? 'Weiter sprechen' : 'Gespräch pausieren'}
        </button>
      </div>
    </div>
  );
}
