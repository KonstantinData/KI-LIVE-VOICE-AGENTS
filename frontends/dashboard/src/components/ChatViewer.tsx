import type { Message } from '../lib/types';

interface ChatViewerProps {
  messages: Message[];
}

export function ChatViewer({ messages }: ChatViewerProps) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="space-y-3">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`max-w-3xl rounded-lg px-3 py-2 text-sm ${
              message.role === 'user'
                ? 'ml-auto bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-900'
            }`}
          >
            <div className="whitespace-pre-wrap">{message.content}</div>
            <div className={`mt-1 text-[11px] ${message.role === 'user' ? 'text-primary-100' : 'text-gray-500'}`}>
              {message.role} · {new Date(message.created_at).toLocaleString('de-DE')}
            </div>
          </div>
        ))}
        {messages.length === 0 && (
          <div className="py-8 text-center text-sm text-gray-500">Keine Nachrichten vorhanden.</div>
        )}
      </div>
    </div>
  );
}
