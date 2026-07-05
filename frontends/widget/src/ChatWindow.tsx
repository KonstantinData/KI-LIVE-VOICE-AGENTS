/** Chat-Fenster mit Nachrichtenverlauf und Eingabefeld. */

import { useCallback, useEffect, useRef, useState } from 'react';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';
import { VoiceControls } from './VoiceControls';
import { useWebSocket } from './hooks/useWebSocket';
import type { WidgetConfig } from './lib/config';

interface ChatWindowProps {
  config: WidgetConfig;
  visitorId: string;
}

const MAX_UPLOAD_FILES = 10;

export function ChatWindow({ config, visitorId }: ChatWindowProps) {
  const [input, setInput] = useState('');
  const [mode, setMode] = useState<'text' | 'voice'>('text');
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [uploadAnalysisConsent, setUploadAnalysisConsent] = useState(false);
  const [showUploadInfo, setShowUploadInfo] = useState(false);
  const [chatMessages, setChatMessages] = useState<
    { role: 'user' | 'assistant'; content: string }[]
  >([{ role: 'assistant', content: config.welcomeMessage }]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadContextGreeting() {
      try {
        const response = await fetch(`${config.apiHttpUrl}/voice/context`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            studio: config.studio,
            visitor_id: visitorId,
            consent_granted: true,
            consent_version: config.voiceConsentVersion,
          }),
        });
        if (!response.ok) return;
        const data = (await response.json()) as { greeting?: string };
        const greeting = data.greeting?.trim();
        if (!cancelled && greeting) {
          setChatMessages([{ role: 'assistant', content: greeting }]);
        }
      } catch {
        // Keep the static fallback greeting when context lookup is unavailable.
      }
    }

    void loadContextGreeting();
    return () => {
      cancelled = true;
    };
  }, [config.apiHttpUrl, config.studio, config.voiceConsentVersion, visitorId]);

  const handleIncomingMessage = useCallback(
    (message: { role: 'user' | 'assistant'; content: string }) => {
      setChatMessages((prev) => [
        ...prev,
        { role: message.role, content: message.content },
      ]);
    },
    [],
  );

  const { send, connected, connecting, typing } = useWebSocket({
    url: config.apiUrl,
    studio: config.studio,
    visitorId,
    onMessage: handleIncomingMessage,
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages.length, typing]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || !connected) return;
    setChatMessages((prev) => [...prev, { role: 'user', content: text }]);
    send(text);
    setInput('');
  };

  const uploadSingleProjectFile = async (file: File, index: number, total: number) => {
    const progress = total > 1 ? ` (${index + 1}/${total})` : '';
    const form = new FormData();
    form.append('studio', config.studio);
    form.append('visitor_id', visitorId);
    form.append('consent_granted', 'true');
    form.append('consent_version', config.voiceConsentVersion);
    form.append('ai_analysis_consent', String(uploadAnalysisConsent));
    form.append('file', file);

    setUploadStatus(`Datei wird sicher hochgeladen${progress}...`);
    const response = await fetch(`${config.apiHttpUrl}/uploads/project-file`, {
      method: 'POST',
      body: form,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload.success) {
      throw new Error(`upload_failed_${response.status}`);
    }

    const filename = String(payload.filename || file.name);
    const userMessage = `Ich habe die Projektdatei "${filename}" hochgeladen.`;
    if (mode === 'voice') {
      setMode('text');
    }
    setChatMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    if (connected) {
      send(
        `${userMessage} Bitte frage mich kurz, ob ich zu der Datei bestimmte Angaben machen möchte oder ob wir darüber sprechen sollen.`,
      );
    } else {
      setChatMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: String(
            payload.message || 'Die Datei wurde hochgeladen und für die Beratung gespeichert.',
          ),
        },
      ]);
    }
  };

  const uploadProjectFiles = async (files: FileList | File[] | null) => {
    const selectedFiles = Array.from(files ?? []);
    if (selectedFiles.length === 0 || uploading) return;
    if (selectedFiles.length > MAX_UPLOAD_FILES) {
      setUploadStatus(`Bitte wählen Sie höchstens ${MAX_UPLOAD_FILES} Dateien auf einmal aus.`);
      if (fileInputRef.current) fileInputRef.current.value = '';
      if (cameraInputRef.current) cameraInputRef.current.value = '';
      return;
    }
    if (!uploadAnalysisConsent) {
      setUploadStatus('Bitte bestätigen Sie zuerst die KI-gestützte Einordnung der Datei.');
      return;
    }

    setUploading(true);
    try {
      let uploaded = 0;
      for (const [index, file] of selectedFiles.entries()) {
        await uploadSingleProjectFile(file, index, selectedFiles.length);
        uploaded += 1;
      }
      setUploadStatus(
        uploaded === 1
          ? 'Upload abgeschlossen.'
          : `${uploaded} Dateien wurden hochgeladen.`,
      );
    } catch {
      setUploadStatus('Mindestens eine Datei konnte nicht hochgeladen werden. Bitte prüfen Sie Format und Größe.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
      if (cameraInputRef.current) cameraInputRef.current.value = '';
    }
  };

  const renderUploadPanel = () => (
    <div className="widget-upload-panel">
      <div className="widget-upload-row">
        <div className="widget-upload-actions">
          <button
            className="widget-upload-button"
            disabled={uploading}
            onClick={() => fileInputRef.current?.click()}
            type="button"
          >
            Datei
          </button>
          <button
            className="widget-upload-button"
            disabled={uploading}
            onClick={() => cameraInputRef.current?.click()}
            type="button"
          >
            Foto
          </button>
        </div>
        <button
          aria-label="Hinweis zu Datei-Uploads"
          className="widget-upload-info"
          onClick={() => setShowUploadInfo((visible) => !visible)}
          type="button"
        >
          i
        </button>
      </div>
      <input
        accept="application/pdf,image/png,image/jpeg"
        hidden
        multiple
        onChange={(event) => void uploadProjectFiles(event.currentTarget.files)}
        ref={fileInputRef}
        type="file"
      />
      <input
        accept="image/png,image/jpeg"
        capture="environment"
        hidden
        onChange={(event) => void uploadProjectFiles(event.currentTarget.files)}
        ref={cameraInputRef}
        type="file"
      />
      <label className="widget-upload-consent">
        <input
          checked={uploadAnalysisConsent}
          onChange={(event) => setUploadAnalysisConsent(event.currentTarget.checked)}
          type="checkbox"
        />
        <span>
          Datei zur KI-gestützten Projekteinordnung hochladen und privat speichern.
        </span>
      </label>
      {showUploadInfo && (
        <div className="widget-upload-note">
          PDF, PNG oder JPEG bis 10 MB. Fotos helfen KEA, die bestehende Situation konkreter einzuordnen.
        </div>
      )}
      {uploadStatus && <div className="widget-upload-status">{uploadStatus}</div>}
    </div>
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
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
          Sprache
        </button>
      </div>

      {mode === 'voice' ? (
        <>
          <VoiceControls config={config} visitorId={visitorId} />
          {renderUploadPanel()}
        </>
      ) : (
        <>
          <div className="widget-messages">
            {chatMessages.map((msg, i) => (
              <MessageBubble key={i} role={msg.role} content={msg.content} />
            ))}
            {typing && <TypingIndicator />}
            <div ref={messagesEndRef} />
          </div>

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
