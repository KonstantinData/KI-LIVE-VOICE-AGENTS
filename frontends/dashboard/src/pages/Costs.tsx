import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { StatsCard } from '../components/StatsCard';
import { api } from '../lib/api';
import type { CostBreakdownRow, CostReport } from '../lib/types';

const PERIOD_OPTIONS = [7, 30, 90] as const;

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('de-DE', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 4,
    maximumFractionDigits: 4,
  }).format(value);
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat('de-DE').format(value);
}

function labelForComponent(name: string): string {
  const labels: Record<string, string> = {
    voice_realtime: 'Sprachchat',
    project_upload_analysis: 'Datei-Analyse',
  };
  return labels[name] ?? name;
}

function CostBreakdownTable({
  title,
  rows,
  labelFormatter = (value) => value,
}: {
  title: string;
  rows: CostBreakdownRow[];
  labelFormatter?: (value: string) => string;
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="border-b border-gray-100 px-4 py-3">
        <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 text-right font-medium">Kosten</th>
              <th className="px-4 py-3 text-right font-medium">Tokens</th>
              <th className="px-4 py-3 text-right font-medium">Events</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map((row) => (
              <tr key={row.name}>
                <td className="px-4 py-3 text-gray-900">{labelFormatter(row.name)}</td>
                <td className="px-4 py-3 text-right font-medium text-gray-900">
                  {formatCurrency(row.estimated_cost_usd)}
                </td>
                <td className="px-4 py-3 text-right text-gray-600">
                  {formatNumber(row.total_tokens)}
                </td>
                <td className="px-4 py-3 text-right text-gray-600">
                  {formatNumber(row.event_count)}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="px-4 py-4 text-sm text-gray-500" colSpan={4}>
                  Keine Kostendaten im gewählten Zeitraum.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function Costs() {
  const [periodDays, setPeriodDays] = useState<(typeof PERIOD_OPTIONS)[number]>(30);
  const [report, setReport] = useState<CostReport | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError('');
    api.get<CostReport>(`/dashboard/costs?days=${periodDays}`)
      .then(setReport)
      .catch((err) => setError(err instanceof Error ? err.message : 'Fehler beim Laden'))
      .finally(() => setLoading(false));
  }, [periodDays]);

  const maxDailyCost = useMemo(
    () => Math.max(0, ...(report?.daily.map((row) => row.estimated_cost_usd) ?? [])),
    [report],
  );

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="mb-2 text-2xl font-bold text-gray-900">Kosten</h1>
          <p className="text-gray-500">OpenAI-Nutzung pro Chatfenster und Datei-Analyse</p>
        </div>
        <div className="inline-flex rounded-lg border border-gray-200 bg-white p-1">
          {PERIOD_OPTIONS.map((days) => (
            <button
              key={days}
              className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                periodDays === days
                  ? 'bg-primary-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
              onClick={() => setPeriodDays(days)}
              type="button"
            >
              {days} Tage
            </button>
          ))}
        </div>
      </div>

      {error && <div className="mb-4 text-sm text-red-600">{error}</div>}
      {loading && <div className="text-sm text-gray-500">Kosten werden geladen...</div>}

      {report && !loading && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatsCard
              title="Gesamtkosten"
              value={formatCurrency(report.summary.estimated_cost_usd)}
              detail={`${report.period_days} Tage`}
            />
            <StatsCard
              title="Gespräche"
              value={formatNumber(report.summary.conversation_count)}
              detail={`${formatNumber(report.summary.event_count)} Events`}
            />
            <StatsCard title="Tokens gesamt" value={formatNumber(report.summary.total_tokens)} />
            <StatsCard
              title="Audio/Bild Tokens"
              value={formatNumber(
                report.summary.input_audio_tokens +
                  report.summary.output_audio_tokens +
                  report.summary.input_image_tokens,
              )}
              detail="Input Audio, Output Audio und Bilder"
            />
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="mb-4 flex items-center justify-between gap-4">
              <h2 className="text-sm font-semibold text-gray-900">Kostenverlauf</h2>
              <span className="text-xs text-gray-500">
                Maximum {formatCurrency(maxDailyCost)}
              </span>
            </div>
            <div className="space-y-3">
              {report.daily.map((row) => {
                const width = maxDailyCost > 0 ? (row.estimated_cost_usd / maxDailyCost) * 100 : 0;
                return (
                  <div key={row.date} className="grid grid-cols-[88px_1fr_96px] items-center gap-3 text-sm">
                    <div className="text-gray-500">
                      {new Date(`${row.date}T00:00:00`).toLocaleDateString('de-DE', {
                        day: '2-digit',
                        month: '2-digit',
                      })}
                    </div>
                    <div className="h-3 rounded bg-gray-100">
                      <div
                        className="h-3 rounded bg-primary-500"
                        style={{ width: `${Math.max(width, row.estimated_cost_usd > 0 ? 2 : 0)}%` }}
                      />
                    </div>
                    <div className="text-right font-medium text-gray-900">
                      {formatCurrency(row.estimated_cost_usd)}
                    </div>
                  </div>
                );
              })}
              {report.daily.length === 0 && (
                <div className="text-sm text-gray-500">Keine Kostendaten im gewählten Zeitraum.</div>
              )}
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <CostBreakdownTable
              title="Nach Komponente"
              rows={report.by_component}
              labelFormatter={labelForComponent}
            />
            <CostBreakdownTable title="Nach Modell" rows={report.by_model} />
            <CostBreakdownTable title="Nach Kanal" rows={report.by_channel} />
          </div>

          <div className="rounded-lg border border-gray-200 bg-white">
            <div className="border-b border-gray-100 px-4 py-3">
              <h2 className="text-sm font-semibold text-gray-900">Gespräche mit Kosten</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                  <tr>
                    <th className="px-4 py-3 font-medium">Visitor</th>
                    <th className="px-4 py-3 font-medium">Kanal</th>
                    <th className="px-4 py-3 text-right font-medium">Kosten</th>
                    <th className="px-4 py-3 text-right font-medium">Tokens</th>
                    <th className="px-4 py-3 text-right font-medium">Events</th>
                    <th className="px-4 py-3 text-right font-medium">Letztes Event</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {report.top_conversations.map((row) => (
                    <tr key={row.conversation_id}>
                      <td className="px-4 py-3">
                        <Link
                          className="font-medium text-primary-600 hover:text-primary-700"
                          to={`/conversations?conversation=${row.conversation_id}`}
                        >
                          {row.visitor_id}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-gray-600">{row.channel}</td>
                      <td className="px-4 py-3 text-right font-medium text-gray-900">
                        {formatCurrency(row.estimated_cost_usd)}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-600">
                        {formatNumber(row.total_tokens)}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-600">
                        {formatNumber(row.event_count)}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-600">
                        {row.last_event_at
                          ? new Date(row.last_event_at).toLocaleString('de-DE')
                          : '-'}
                      </td>
                    </tr>
                  ))}
                  {report.top_conversations.length === 0 && (
                    <tr>
                      <td className="px-4 py-4 text-sm text-gray-500" colSpan={6}>
                        Keine Gespräche mit Kostendaten im gewählten Zeitraum.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
