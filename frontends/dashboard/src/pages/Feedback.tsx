import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import type { Feedback as FeedbackItem } from '../lib/types';

export function Feedback() {
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get<FeedbackItem[]>('/feedback/')
      .then(setFeedback)
      .catch((err) => setError(err instanceof Error ? err.message : 'Fehler beim Laden'));
  }, []);

  return (
    <div>
      <h1 className="mb-2 text-2xl font-bold text-gray-900">Feedback</h1>
      <p className="mb-8 text-gray-500">Bewertungen und Korrekturen zu Lisa-Antworten</p>
      {error && <div className="mb-4 text-sm text-red-600">{error}</div>}
      <div className="grid gap-3">
        {feedback.map((item) => (
          <article key={item.id} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="text-sm font-medium text-gray-900">Nachricht {item.message_id}</div>
              <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-700">{item.rating ?? 'ohne Rating'}</span>
            </div>
            <p className="mt-3 whitespace-pre-wrap text-sm text-gray-700">{item.correction || 'Keine Korrektur hinterlegt.'}</p>
            <div className="mt-2 text-xs text-gray-500">{new Date(item.created_at).toLocaleString('de-DE')}</div>
          </article>
        ))}
        {feedback.length === 0 && <div className="rounded-lg border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">Noch kein Feedback vorhanden.</div>}
      </div>
    </div>
  );
}
