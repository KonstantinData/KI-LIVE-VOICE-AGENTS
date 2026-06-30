import { Link } from 'react-router-dom';
import type { Lead } from '../lib/types';
import { ScoreBadge } from './ScoreBadge';

interface LeadTableProps {
  leads: Lead[];
}

export function LeadTable({ leads }: LeadTableProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
          <tr>
            <th className="px-4 py-3">Lead</th>
            <th className="px-4 py-3">Kontakt</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Score</th>
            <th className="px-4 py-3">Erstellt</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {leads.map((lead) => (
            <tr key={lead.id} className="hover:bg-gray-50">
              <td className="px-4 py-3">
                <Link className="font-medium text-primary-700 hover:underline" to={`/leads/${lead.id}`}>
                  {lead.name || lead.visitor_id}
                </Link>
              </td>
              <td className="px-4 py-3 text-gray-600">
                {lead.email || lead.phone || 'Keine Kontaktdaten'}
              </td>
              <td className="px-4 py-3 text-gray-700">{lead.status}</td>
              <td className="px-4 py-3"><ScoreBadge score={lead.score} /></td>
              <td className="px-4 py-3 text-gray-500">{new Date(lead.created_at).toLocaleString('de-DE')}</td>
            </tr>
          ))}
          {leads.length === 0 && (
            <tr>
              <td className="px-4 py-8 text-center text-gray-500" colSpan={5}>
                Noch keine Leads vorhanden.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
