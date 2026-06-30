import { useEffect, useState } from 'react';
import { StatsCard } from '../components/StatsCard';
import { api } from '../lib/api';
import type { DashboardStats } from '../lib/types';

export function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get<DashboardStats>('/dashboard/stats')
      .then(setStats)
      .catch((err) => setError(err instanceof Error ? err.message : 'Fehler beim Laden'));
  }, []);

  if (error) return <div className="text-sm text-red-600">{error}</div>;
  if (!stats) return <div className="text-sm text-gray-500">Dashboard wird geladen...</div>;

  return (
    <div>
      <h1 className="mb-2 text-2xl font-bold text-gray-900">Dashboard</h1>
      <p className="mb-8 text-gray-500">{stats.studio.name}</p>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatsCard title="Leads gesamt" value={stats.leads_total} detail={`${stats.leads_qualified} qualifiziert`} />
        <StatsCard title="Aktive Gespräche" value={stats.active_conversations} />
        <StatsCard title="Termine" value={stats.appointments_total} />
        <StatsCard title="Offene Follow-ups" value={stats.pending_followups} />
        <StatsCard title="Ø Lead-Score" value={stats.average_lead_score} />
        <StatsCard title="Feedback" value={stats.feedback_total} />
      </div>
    </div>
  );
}
