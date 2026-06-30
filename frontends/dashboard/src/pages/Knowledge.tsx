import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import type { KnowledgeChunk } from '../lib/types';

export function Knowledge() {
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([]);
  const [category, setCategory] = useState('faq');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [error, setError] = useState('');

  const load = () => {
    api.get<KnowledgeChunk[]>('/knowledge/')
      .then(setChunks)
      .catch((err) => setError(err instanceof Error ? err.message : 'Fehler beim Laden'));
  };

  useEffect(load, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    try {
      const created = await api.post<KnowledgeChunk>('/knowledge/', { category, title, content });
      setChunks((prev) => [created, ...prev]);
      setTitle('');
      setContent('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Speichern fehlgeschlagen');
    }
  };

  return (
    <div>
      <h1 className="mb-2 text-2xl font-bold text-gray-900">Wissensbasis</h1>
      <p className="mb-8 text-gray-500">Studio-Wissen für Lisa verwalten</p>
      {error && <div className="mb-4 text-sm text-red-600">{error}</div>}

      <form onSubmit={handleSubmit} className="mb-6 rounded-lg border border-gray-200 bg-white p-4">
        <div className="grid gap-3 md:grid-cols-[160px_1fr]">
          <select value={category} onChange={(e) => setCategory(e.target.value)} className="rounded border border-gray-300 px-3 py-2 text-sm">
            <option value="faq">FAQ</option>
            <option value="sortiment">Sortiment</option>
            <option value="referenzen">Referenzen</option>
            <option value="aktionen">Aktionen</option>
            <option value="studio">Studio</option>
          </select>
          <input value={title} onChange={(e) => setTitle(e.target.value)} className="rounded border border-gray-300 px-3 py-2 text-sm" placeholder="Titel" required />
          <textarea value={content} onChange={(e) => setContent(e.target.value)} className="md:col-span-2 rounded border border-gray-300 px-3 py-2 text-sm" placeholder="Inhalt" rows={4} required />
        </div>
        <button className="mt-3 rounded bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700" type="submit">
          Wissen speichern
        </button>
      </form>

      <div className="grid gap-3">
        {chunks.map((chunk) => (
          <article key={chunk.id} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="mb-1 text-xs font-semibold uppercase text-primary-700">{chunk.category}</div>
            <h2 className="font-semibold text-gray-900">{chunk.title}</h2>
            <p className="mt-2 whitespace-pre-wrap text-sm text-gray-700">{chunk.content}</p>
          </article>
        ))}
        {chunks.length === 0 && <div className="rounded-lg border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">Noch kein Wissen hinterlegt.</div>}
      </div>
    </div>
  );
}
