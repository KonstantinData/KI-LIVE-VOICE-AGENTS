import { useEffect, useState } from 'react';
import { LeadTable } from '../components/LeadTable';
import { api } from '../lib/api';
import type { Lead } from '../lib/types';

export function Leads() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get<Lead[]>('/leads/')
      .then(setLeads)
      .catch((err) => setError(err instanceof Error ? err.message : 'Fehler beim Laden'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 className="mb-2 text-2xl font-bold text-gray-900">Leads</h1>
      <p className="mb-8 text-gray-500">Interessenten aus dem Widget</p>
      {error && <div className="mb-4 text-sm text-red-600">{error}</div>}
      {loading ? <div className="text-sm text-gray-500">Leads werden geladen...</div> : <LeadTable leads={leads} />}
    </div>
  );
}
