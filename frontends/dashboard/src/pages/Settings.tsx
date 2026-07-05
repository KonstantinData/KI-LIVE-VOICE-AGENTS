import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import type { Studio } from '../lib/types';

export function Settings() {
  const [studio, setStudio] = useState<Studio | null>(null);
  const [name, setName] = useState('');
  const [primaryColor, setPrimaryColor] = useState('#2563eb');
  const [agentName, setAgentName] = useState('KEA');
  const [welcomeMessage, setWelcomeMessage] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    api.get<Studio>('/studios/current')
      .then((row) => {
        setStudio(row);
        setName(row.name);
        setPrimaryColor(String(row.config?.primary_color ?? '#2563eb'));
        setAgentName(String(row.config?.agent_name ?? 'KEA'));
        setWelcomeMessage(String(row.config?.welcome_message ?? 'Hallo! Ich bin KEA. Wie kann ich Ihnen helfen?'));
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Fehler beim Laden'));
  }, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!studio) return;
    setError('');
    setMessage('');
    try {
      const updated = await api.put<Studio>('/studios/current', {
        name,
        config: {
          ...(studio.config || {}),
          primary_color: primaryColor,
          agent_name: agentName,
          welcome_message: welcomeMessage,
        },
      });
      setStudio(updated);
      setMessage('Einstellungen gespeichert.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Speichern fehlgeschlagen');
    }
  };

  if (!studio && !error) return <div className="text-sm text-gray-500">Einstellungen werden geladen...</div>;

  return (
    <div>
      <h1 className="mb-2 text-2xl font-bold text-gray-900">Einstellungen</h1>
      <p className="mb-8 text-gray-500">Studio-Konfiguration für Widget und Dashboard</p>
      {error && <div className="mb-4 text-sm text-red-600">{error}</div>}
      {message && <div className="mb-4 text-sm text-green-700">{message}</div>}

      <form onSubmit={handleSubmit} className="max-w-2xl rounded-lg border border-gray-200 bg-white p-4">
        <label className="mb-3 block text-sm">
          <span className="mb-1 block font-medium text-gray-700">Studio-Name</span>
          <input className="w-full rounded border border-gray-300 px-3 py-2" value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label className="mb-3 block text-sm">
          <span className="mb-1 block font-medium text-gray-700">Primärfarbe</span>
          <input className="h-10 w-24 rounded border border-gray-300 px-1" type="color" value={primaryColor} onChange={(e) => setPrimaryColor(e.target.value)} />
        </label>
        <label className="mb-3 block text-sm">
          <span className="mb-1 block font-medium text-gray-700">Agent-Name</span>
          <input className="w-full rounded border border-gray-300 px-3 py-2" value={agentName} onChange={(e) => setAgentName(e.target.value)} required />
        </label>
        <label className="mb-3 block text-sm">
          <span className="mb-1 block font-medium text-gray-700">Willkommensnachricht</span>
          <textarea className="w-full rounded border border-gray-300 px-3 py-2" rows={3} value={welcomeMessage} onChange={(e) => setWelcomeMessage(e.target.value)} required />
        </label>
        <button className="rounded bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700" type="submit">
          Speichern
        </button>
      </form>
    </div>
  );
}
