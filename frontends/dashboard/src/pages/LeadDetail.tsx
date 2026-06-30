import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ScoreBadge } from '../components/ScoreBadge';
import { api } from '../lib/api';
import type { Lead } from '../lib/types';

export function LeadDetail() {
  const { id } = useParams();
  const [lead, setLead] = useState<Lead | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    api.get<Lead>(`/leads/${id}`)
      .then(setLead)
      .catch((err) => setError(err instanceof Error ? err.message : 'Fehler beim Laden'));
  }, [id]);

  if (error) return <div className="text-sm text-red-600">{error}</div>;
  if (!lead) return <div className="text-sm text-gray-500">Lead wird geladen...</div>;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{lead.name || lead.visitor_id}</h1>
          <p className="text-gray-500">{lead.email || lead.phone || 'Keine Kontaktdaten'}</p>
        </div>
        <ScoreBadge score={lead.score} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-gray-900">Lead-Daten</h2>
          <dl className="space-y-2 text-sm">
            <div><dt className="text-gray-500">Status</dt><dd className="text-gray-900">{lead.status}</dd></div>
            <div><dt className="text-gray-500">Quelle</dt><dd className="text-gray-900">{lead.source_channel || 'Unbekannt'}</dd></div>
            <div><dt className="text-gray-500">Erstellt</dt><dd className="text-gray-900">{new Date(lead.created_at).toLocaleString('de-DE')}</dd></div>
          </dl>
        </section>

        <section className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-gray-900">Zusammenfassung</h2>
          <p className="whitespace-pre-wrap text-sm text-gray-700">{lead.summary || 'Noch keine Zusammenfassung vorhanden.'}</p>
        </section>

        <section className="rounded-lg border border-gray-200 bg-white p-4 lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold text-gray-900">Profil</h2>
          <pre className="overflow-auto rounded bg-gray-50 p-3 text-xs text-gray-700">
            {JSON.stringify(lead.profile || {}, null, 2)}
          </pre>
        </section>
      </div>
    </div>
  );
}
