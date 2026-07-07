import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ChatViewer } from '../components/ChatViewer';
import { api } from '../lib/api';
import type { Conversation, Message } from '../lib/types';

export function Conversations() {
  const [searchParams] = useSearchParams();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get<Conversation[]>('/conversations/')
      .then((rows) => {
        setConversations(rows);
        const requestedId = searchParams.get('conversation');
        setSelected(rows.find((row) => row.id === requestedId) ?? rows[0] ?? null);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Fehler beim Laden'));
  }, [searchParams]);

  useEffect(() => {
    if (!selected) {
      setMessages([]);
      return;
    }
    api.get<Message[]>(`/conversations/${selected.id}/messages`)
      .then(setMessages)
      .catch((err) => setError(err instanceof Error ? err.message : 'Fehler beim Laden'));
  }, [selected]);

  return (
    <div>
      <h1 className="mb-2 text-2xl font-bold text-gray-900">Gespräche</h1>
      <p className="mb-8 text-gray-500">Chat-Verläufe aus dem Widget</p>
      {error && <div className="mb-4 text-sm text-red-600">{error}</div>}
      <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
        <div className="rounded-lg border border-gray-200 bg-white">
          {conversations.map((conversation) => (
            <button
              key={conversation.id}
              className={`block w-full border-b border-gray-100 px-4 py-3 text-left text-sm hover:bg-gray-50 ${
                selected?.id === conversation.id ? 'bg-primary-50' : ''
              }`}
              onClick={() => setSelected(conversation)}
            >
              <div className="font-medium text-gray-900">{conversation.visitor_id}</div>
              <div className="text-xs text-gray-500">{conversation.status} · {new Date(conversation.updated_at).toLocaleString('de-DE')}</div>
            </button>
          ))}
          {conversations.length === 0 && <div className="p-4 text-sm text-gray-500">Keine Gespräche vorhanden.</div>}
        </div>
        <ChatViewer messages={messages} />
      </div>
    </div>
  );
}
