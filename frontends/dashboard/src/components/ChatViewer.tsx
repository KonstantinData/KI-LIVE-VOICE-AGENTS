import { useState } from 'react';
import { api } from '../lib/api';
import type { Message } from '../lib/types';

interface ChatViewerProps {
  messages: Message[];
}

interface ProjectUploadCall {
  type: 'project_upload';
  file_id: string;
  original_filename: string;
  content_type: string;
  file_deleted?: boolean;
}

function projectUploads(message: Message): ProjectUploadCall[] {
  return (message.tool_calls ?? []).filter((call): call is ProjectUploadCall => {
    if (!call || typeof call !== 'object') {
      return false;
    }
    const upload = call as Record<string, unknown>;
    return (
      upload.type === 'project_upload'
      && typeof upload.file_id === 'string'
      && typeof upload.original_filename === 'string'
      && typeof upload.content_type === 'string'
    );
  });
}

export function ChatViewer({ messages }: ChatViewerProps) {
  const [downloadError, setDownloadError] = useState('');

  async function downloadUpload(upload: ProjectUploadCall) {
    setDownloadError('');
    try {
      await api.download(
        `/uploads/project-files/${encodeURIComponent(upload.file_id)}`,
        upload.original_filename,
      );
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : 'Download fehlgeschlagen');
    }
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      {downloadError && <div className="mb-3 text-sm text-red-600">{downloadError}</div>}
      <div className="space-y-3">
        {messages.map((message) => {
          const uploads = projectUploads(message);
          return (
            <div
              key={message.id}
              className={`max-w-3xl rounded-lg px-3 py-2 text-sm ${
                message.role === 'user'
                  ? 'ml-auto bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <div className="whitespace-pre-wrap">{message.content}</div>
              {uploads.length > 0 && (
                <div className="mt-3 space-y-2">
                  {uploads.map((upload) => (
                    <button
                      key={upload.file_id}
                      type="button"
                      className={`block rounded border px-3 py-2 text-left text-xs ${
                        message.role === 'user'
                          ? 'border-primary-200 bg-white text-primary-700'
                          : 'border-gray-200 bg-white text-gray-700'
                      } disabled:cursor-not-allowed disabled:opacity-60`}
                      disabled={upload.file_deleted}
                      onClick={() => downloadUpload(upload)}
                    >
                      <span className="block font-medium">
                        {upload.file_deleted ? 'Datei gelöscht' : 'Datei herunterladen'}
                      </span>
                      <span className="block">{upload.original_filename}</span>
                    </button>
                  ))}
                </div>
              )}
              <div className={`mt-1 text-[11px] ${message.role === 'user' ? 'text-primary-100' : 'text-gray-500'}`}>
                {message.role} · {new Date(message.created_at).toLocaleString('de-DE')}
              </div>
            </div>
          );
        })}
        {messages.length === 0 && (
          <div className="py-8 text-center text-sm text-gray-500">Keine Nachrichten vorhanden.</div>
        )}
      </div>
    </div>
  );
}
