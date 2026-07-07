/** Chat-Fenster mit Nachrichtenverlauf und Eingabefeld. */

import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';
import { MessageBubble } from './MessageBubble';
import { ProjectUploadPanel } from './ProjectUploadPanel';
import { TypingIndicator } from './TypingIndicator';
import { VoiceControls } from './VoiceControls';
import { useWebSocket, type Choice } from './hooks/useWebSocket';
import type { WidgetConfig } from './lib/config';
import { hasContactIntent, isContactChoice } from './lib/contactIntent';
import { buildProjectSummary } from './lib/projectSummary';

interface ChatWindowProps {
  config: WidgetConfig;
  visitorId: string;
}

interface ContactFormData {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  best_reachability: string;
  additional_notes: string;
  contact_consent_confirmed: boolean;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  choices?: Choice[];
}

export function ChatWindow({ config, visitorId }: ChatWindowProps) {
  const [input, setInput] = useState('');
  const [mode, setMode] = useState<'text' | 'voice'>('text');
  const [conversationId, setConversationId] = useState<string | null>(null);
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
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleIncomingMessage = useCallback(
    (message: ChatMessage) => {
      if (hasContactIntent(message.content)) {
        setShowContactForm(true);
      }
      setChatMessages((prev) => [
        ...prev,
        {
          role: message.role,
          content: message.content,
          choices: message.choices,
        },
      ]);
    },
    [],
  );

  const { send, sendAction, connected, connecting, typing } = useWebSocket({
    url: config.apiUrl,
    studio: config.studio,
    visitorId,
    onMessage: handleIncomingMessage,
    onSession: setConversationId,
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages.length, typing]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || !connected) return;
    if (hasContactIntent(text)) {
      setShowContactForm(true);
    }
    setChatMessages((prev) => [...prev, { role: 'user', content: text }]);
    send(text);
    setInput('');
  };

  const handleChoice = (choice: Choice) => {
    if (!connected) return;
    setChatMessages((prev) => [...prev, { role: 'user', content: choice.label }]);
    if (isContactChoice(choice)) {
      setShowContactForm(true);
      return;
    }
    sendAction(choice.id, choice.label);
  };

  const renderUploadPanel = () => (
    <ProjectUploadPanel
      config={config}
      visitorId={visitorId}
      conversationId={conversationId}
      connected={connected}
      send={send}
      onConversationAssigned={setConversationId}
      onLocalMessage={handleIncomingMessage}
    />
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const updateContactField = (
    field: keyof ContactFormData,
    value: string | boolean,
  ) => {
    setContactForm((current) => ({ ...current, [field]: value }));
  };

  const submitContactForm = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const projectSummary = buildProjectSummary(chatMessages);
    if (!conversationId) {
      setContactStatus('Bitte warten Sie kurz, bis die Chat-Sitzung verbunden ist.');
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
          voice_session_id: `text_chat_${conversationId}`,
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
      setChatMessages((prev) => [...prev, { role: 'assistant', content: sentText }]);
      setShowContactForm(false);
    } catch {
      setContactStatus('Die Kontaktdaten konnten gerade nicht übermittelt werden. Bitte versuchen Sie es später erneut.');
    }
  };

  const renderContactPanel = () => {
    const projectSummary = buildProjectSummary(chatMessages);

    return (
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
    );
  };

  return (
    <>
      <div className="widget-header">
        <div className="widget-header-mark" aria-hidden="true">KI</div>
        <div className="widget-header-copy">
          <div className="widget-header-title">{config.agentName} - Küchen Expert Assistent</div>
          <div className="widget-header-subtitle">
            {mode === 'voice'
              ? 'Sprachmodus für erste Orientierung'
              : connecting
                ? 'Verbindet mit dem Assistenten'
                : connected
                  ? 'Online für Ihr Küchenprojekt'
                  : 'Textchat gerade offline'}
          </div>
        </div>
        <span className={`widget-status-dot ${connected || mode === 'voice' ? 'widget-status-dot--online' : ''}`} />
      </div>

      <div className="widget-mode-tabs" role="tablist" aria-label="Chat-Modus">
        <button
          className={`widget-mode-tab ${mode === 'text' ? 'widget-mode-tab--active' : ''}`}
          onClick={() => setMode('text')}
          type="button"
        >
          Textchat
        </button>
        <button
          className={`widget-mode-tab ${mode === 'voice' ? 'widget-mode-tab--active' : ''}`}
          onClick={() => setMode('voice')}
          type="button"
          disabled={!config.voiceEnabled}
        >
          Sprachchat
        </button>
      </div>

      {mode === 'voice' ? (
        <>
          <VoiceControls
            config={config}
            visitorId={visitorId}
            onConversationReady={setConversationId}
          />
          {renderUploadPanel()}
        </>
      ) : (
        <>
          <div className="widget-messages">
            {chatMessages.map((msg, i) => (
              <div
                className={`widget-message-group widget-message-group--${msg.role}`}
                key={`${msg.role}-${i}`}
              >
                <MessageBubble role={msg.role} content={msg.content} />
                {msg.role === 'assistant' && i === chatMessages.length - 1 && msg.choices?.length ? (
                  <div className="widget-choice-list">
                    {msg.choices.map((choice) => (
                      <button
                        className="widget-choice-button"
                        disabled={!connected}
                        key={choice.id}
                        onClick={() => handleChoice(choice)}
                        type="button"
                      >
                        {choice.label}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
            {typing && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>

          {showContactForm && renderContactPanel()}

          {renderUploadPanel()}

          <div className="widget-input-area">
            <textarea
              className="widget-input"
              placeholder="Schreiben Sie eine Nachricht..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
            />
            <button
              className="widget-send-button"
              onClick={handleSend}
              disabled={!connected || !input.trim()}
              aria-label="Senden"
            >
              ➤
            </button>
          </div>
        </>
      )}
    </>
  );
}
