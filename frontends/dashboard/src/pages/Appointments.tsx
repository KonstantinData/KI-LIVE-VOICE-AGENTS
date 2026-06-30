import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import type { Appointment } from '../lib/types';

export function Appointments() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get<Appointment[]>('/appointments/')
      .then(setAppointments)
      .catch((err) => setError(err instanceof Error ? err.message : 'Fehler beim Laden'));
  }, []);

  return (
    <div>
      <h1 className="mb-2 text-2xl font-bold text-gray-900">Termine</h1>
      <p className="mb-8 text-gray-500">Beratungstermine und Terminwünsche</p>
      {error && <div className="mb-4 text-sm text-red-600">{error}</div>}
      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50 text-left text-xs font-semibold uppercase text-gray-500">
            <tr><th className="px-4 py-3">Zeitpunkt</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Dauer</th><th className="px-4 py-3">Notizen</th></tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {appointments.map((appointment) => (
              <tr key={appointment.id}>
                <td className="px-4 py-3">{new Date(appointment.datetime_).toLocaleString('de-DE')}</td>
                <td className="px-4 py-3">{appointment.status}</td>
                <td className="px-4 py-3">{appointment.duration_minutes} Min.</td>
                <td className="px-4 py-3 text-gray-600">{appointment.notes || '-'}</td>
              </tr>
            ))}
            {appointments.length === 0 && <tr><td className="px-4 py-8 text-center text-gray-500" colSpan={4}>Keine Termine vorhanden.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
