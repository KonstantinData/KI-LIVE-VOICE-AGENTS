import { useMemo, useRef, useState } from 'react';
import type { WidgetConfig } from './lib/config';

const MAX_UPLOAD_FILES = 10;

interface ProjectUploadPanelProps {
  config: WidgetConfig;
  visitorId: string;
  conversationId: string | null;
  connected: boolean;
  send: (text: string) => void;
  onConversationAssigned: (conversationId: string) => void;
  onLocalMessage: (message: { role: 'user' | 'assistant'; content: string }) => void;
}

interface PendingProjectFile {
  id: string;
  file: File;
}

function fileKey(file: File): string {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function formatFileSize(size: number): string {
  if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

export function ProjectUploadPanel({
  config,
  visitorId,
  conversationId,
  connected,
  send,
  onConversationAssigned,
  onLocalMessage,
}: ProjectUploadPanelProps) {
  const [pendingFiles, setPendingFiles] = useState<PendingProjectFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [uploadAnalysisConsent, setUploadAnalysisConsent] = useState(false);
  const [showUploadInfo, setShowUploadInfo] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const pendingSize = useMemo(
    () => pendingFiles.reduce((sum, item) => sum + item.file.size, 0),
    [pendingFiles],
  );
  const uploadSelectionDisabled = uploading || !uploadAnalysisConsent;

  const addPendingFiles = (files: FileList | File[] | null) => {
    const selected = Array.from(files ?? []);
    if (selected.length === 0 || uploadSelectionDisabled) return;
    setPendingFiles((current) => {
      const existing = new Set(current.map((item) => fileKey(item.file)));
      const next = [...current];
      for (const file of selected) {
        if (next.length >= MAX_UPLOAD_FILES) break;
        const key = fileKey(file);
        if (existing.has(key)) continue;
        existing.add(key);
        next.push({ id: `${key}:${Math.random().toString(36).slice(2)}`, file });
      }
      return next;
    });
    if (selected.length + pendingFiles.length > MAX_UPLOAD_FILES) {
      setUploadStatus(`Es sind höchstens ${MAX_UPLOAD_FILES} Dateien pro Upload möglich.`);
    } else {
      setUploadStatus('');
    }
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (cameraInputRef.current) cameraInputRef.current.value = '';
  };

  const removePendingFile = (id: string) => {
    setPendingFiles((current) => current.filter((item) => item.id !== id));
  };

  const uploadSingleProjectFile = async (
    file: File,
    index: number,
    total: number,
    activeConversationId: string | null,
  ) => {
    const form = new FormData();
    form.append('studio', config.studio);
    form.append('visitor_id', visitorId);
    if (activeConversationId) form.append('conversation_id', activeConversationId);
    form.append('consent_granted', 'true');
    form.append('consent_version', config.voiceConsentVersion);
    form.append('ai_analysis_consent', String(uploadAnalysisConsent));
    form.append('file', file);

    const progress = total > 1 ? ` (${index + 1}/${total})` : '';
    setUploadStatus(`Datei wird sicher hochgeladen${progress}...`);
    const response = await fetch(`${config.apiHttpUrl}/uploads/project-file`, {
      method: 'POST',
      body: form,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload.success) throw new Error(`upload_failed_${response.status}`);
    const assignedConversationId =
      typeof payload.conversation_id === 'string' ? payload.conversation_id : null;
    if (assignedConversationId) onConversationAssigned(assignedConversationId);
    return {
      filename: String(payload.filename || file.name),
      conversationId: assignedConversationId,
    };
  };

  const uploadPendingFiles = async () => {
    if (pendingFiles.length === 0 || uploading) return;
    if (!uploadAnalysisConsent) {
      setUploadStatus('Bitte setzen Sie zuerst das Häkchen für die KI-gestützte Projekteinordnung.');
      return;
    }

    setUploading(true);
    const files = pendingFiles.map((item) => item.file);
    try {
      const uploadedNames: string[] = [];
      let activeConversationId = conversationId;
      for (const [index, file] of files.entries()) {
        const upload = await uploadSingleProjectFile(
          file,
          index,
          files.length,
          activeConversationId,
        );
        uploadedNames.push(upload.filename);
        activeConversationId = upload.conversationId ?? activeConversationId;
      }
      const userMessage =
        uploadedNames.length === 1
          ? `Ich habe die Projektdatei "${uploadedNames[0]}" hochgeladen.`
          : `Ich habe ${uploadedNames.length} Projektdateien hochgeladen: ${uploadedNames.join(', ')}.`;
      onLocalMessage({ role: 'user', content: userMessage });
      if (connected) {
        send(`${userMessage} Bitte beziehe die Dateien in diese Beratung ein.`);
      } else {
        onLocalMessage({
          role: 'assistant',
          content: 'Die Dateien wurden hochgeladen und für die Beratung gespeichert.',
        });
      }
      setPendingFiles([]);
      setUploadStatus(
        uploadedNames.length === 1
          ? 'Upload abgeschlossen.'
          : `${uploadedNames.length} Dateien wurden hochgeladen.`,
      );
    } catch {
      setUploadStatus('Mindestens eine Datei konnte nicht hochgeladen werden. Bitte prüfen Sie Format und Größe.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="widget-upload-panel">
      <label className="widget-upload-consent">
        <input checked={uploadAnalysisConsent} onChange={(event) => setUploadAnalysisConsent(event.currentTarget.checked)} type="checkbox" />
        <span>Datei zur KI-gestützten Projekteinordnung hochladen und privat speichern.</span>
      </label>
      <div className="widget-upload-row">
        <div className="widget-upload-actions">
          <button className="widget-upload-button" disabled={uploadSelectionDisabled} onClick={() => fileInputRef.current?.click()} type="button">
            Datei
          </button>
          <button className="widget-upload-button" disabled={uploadSelectionDisabled} onClick={() => cameraInputRef.current?.click()} type="button">
            Foto
          </button>
        </div>
        <button aria-label="Hinweis zu Datei-Uploads" className="widget-upload-info" onClick={() => setShowUploadInfo((visible) => !visible)} type="button">
          i
        </button>
      </div>
      <input accept="application/pdf,image/png,image/jpeg" disabled={uploadSelectionDisabled} hidden multiple onChange={(event) => addPendingFiles(event.currentTarget.files)} ref={fileInputRef} type="file" />
      <input accept="image/png,image/jpeg" disabled={uploadSelectionDisabled} hidden multiple onChange={(event) => addPendingFiles(event.currentTarget.files)} ref={cameraInputRef} type="file" />
      {pendingFiles.length > 0 && (
        <div className="widget-upload-queue">
          <div className="widget-upload-queue-summary">
            {pendingFiles.length} Datei{pendingFiles.length === 1 ? '' : 'en'} ausgewählt · {formatFileSize(pendingSize)}
          </div>
          {pendingFiles.map(({ id, file }) => (
            <div className="widget-upload-queue-item" key={id}>
              <span>{file.name}</span>
              <small>{formatFileSize(file.size)}</small>
              <button disabled={uploading} onClick={() => removePendingFile(id)} type="button">
                Entfernen
              </button>
            </div>
          ))}
        </div>
      )}
      <button className="widget-upload-submit" disabled={uploadSelectionDisabled || pendingFiles.length === 0} onClick={uploadPendingFiles} type="button">
        Jetzt hochladen
      </button>
      {showUploadInfo && (
        <div className="widget-upload-note">
          PDF, PNG oder JPEG bis 10 MB. Sie können mehrere Dateien auswählen, vor dem Upload prüfen und einzelne Dateien wieder entfernen.
        </div>
      )}
      {uploadStatus && <div className="widget-upload-status">{uploadStatus}</div>}
    </div>
  );
}
