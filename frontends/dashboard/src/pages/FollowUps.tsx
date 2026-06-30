import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import type { FollowUp } from '../lib/types';

export function FollowUps() {
  const [followups, setFollowups] = useState<FollowUp[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get<FollowUp[]>('/followups/')
      .then(setFollowups)
      .catch((err) => setError(err instanceof Error ? err.message : 'Fehler beim Laden'));
  }, []);

  return (
    <div>
      <h1 className="mb-2 text-2xl font-bold text-gray-900">Follow-ups</h1>
      <p className="mb-8 text-gray-500">Nachfass-Aufgaben aus Chat und Terminprozess</p>
      {error && <div className="mb-4 text-sm text-red-600">{error}</div>}
      <div className="grid gap-3">
        {followups.map((followup) => (
          <article key={followup.id} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="font-medium text-gray-900">{followup.type}</div>
              <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-700">{followup.status}</span>
            </div>
            <div className="mt-1 text-sm text-gray-500">{new Date(followup.scheduled_at).toLocaleString('de-DE')} · {followup.channel}</div>
            <p className="mt-3 whitespace-pre-wrap text-sm text-gray-700">{followup.content || 'Kein Inhalt hinterlegt.'}</p>
          </article>
        ))}
        {followups.length === 0 && <div className="rounded-lg border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">Keine Follow-ups vorhanden.</div>}
      </div>
    </div>
  );
}
