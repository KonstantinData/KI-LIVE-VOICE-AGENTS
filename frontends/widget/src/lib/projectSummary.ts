interface SummaryMessage {
  role: 'user' | 'assistant';
  content: string;
}

const DEFAULT_SUMMARY = 'Der Kunde wünscht eine Kontaktaufnahme zur Küchenberatung.';
const MAX_SUMMARY_CHARS = 1200;

const VALUE_LABELS: Record<string, string> = {
  anschluesse_offen: 'Anschlüsse, Elektro oder Wasser sind noch abzustimmen',
  angebot_pruefen: 'ein vorhandenes Angebot oder eine Planung besser einschätzen',
  bau_sanierung: 'Bau, Sanierung oder Renovierung',
  budget_prioritaeten: 'Budgetrahmen und Prioritäten',
  fruehe_planung: 'frühe Planungsphase',
  grundriss_fest: 'Grundriss oder Raumaufteilung stehen bereits fest',
  grundriss_layout: 'Grundriss, Küchenform oder Laufwege',
  hoch: 'zeitnah',
  leistungen_verstehen: 'Leistungsumfang und Angebotsinhalte verstehen',
  mittel: 'mit etwas zeitlichem Spielraum',
  offen: 'ohne festen Zeitdruck',
  preis_vergleichbarkeit: 'Preis und Vergleichbarkeit',
  sehr_hoch: 'sehr kurzfristig',
  technik_anschluesse: 'Anschlüsse, Elektro, Wasser oder Abluft',
  vor_kuechenkauf: 'vor dem Küchenkauf Klarheit gewinnen',
  vollstaendigkeit: 'Vollständigkeit vor dem nächsten Schritt',
};

function cleanSummaryText(text: string): string {
  return text
    .replace(/\s+/g, ' ')
    .replace(/\s+([.,:;!?])/g, '$1')
    .trim();
}

function limitSummary(text: string): string {
  const cleaned = cleanSummaryText(text);
  if (cleaned.length <= MAX_SUMMARY_CHARS) return cleaned;
  return `${cleaned.slice(0, MAX_SUMMARY_CHARS - 3).trim()}...`;
}

function normalizeValue(value: string): string {
  const cleaned = cleanSummaryText(value);
  const key = cleaned.toLowerCase().replace(/\s*\/\s*/g, '_').replace(/\s+/g, '_');
  return VALUE_LABELS[key] ?? cleaned;
}

function extractSummaryField(text: string, label: string): string {
  const match = text.match(new RegExp(`-\\s*${label}:\\s*([^\\n]+)`, 'i'));
  return match ? normalizeValue(match[1]) : '';
}

function buildValueSummary(text: string): string {
  const area = extractSummaryField(text, 'Bereich');
  const focus = extractSummaryField(text, 'Fokus');
  const urgency = extractSummaryField(text, 'Zeitdruck');
  const note = extractSummaryField(text, 'Ihre Ergänzung');

  const parts = [
    area ? `Ihr Anliegen wurde dem Bereich "${area}" zugeordnet.` : '',
    focus ? `Der wichtigste Punkt ist: ${focus}.` : '',
    urgency ? `Der nächste Schritt wirkt ${urgency}.` : '',
    note ? `Ihre Ergänzung: ${note}.` : '',
  ].filter(Boolean);

  if (parts.length === 0) {
    return DEFAULT_SUMMARY;
  }

  return limitSummary(
    `${parts.join(' ')} Mein Küchenexperte kann dadurch gezielter einschätzen, welche Unterlagen, Fragen oder nächsten Schritte für Sie sinnvoll sind.`,
  );
}

export function buildProjectSummary(messages: SummaryMessage[]): string {
  const summaryMessage = [...messages]
    .reverse()
    .find((message) => message.role === 'assistant' && message.content.includes('Zwischenstand:'));

  if (summaryMessage) {
    return buildValueSummary(summaryMessage.content);
  }

  const customerMessages = messages
    .filter((message) => message.role === 'user')
    .map((message) => cleanSummaryText(message.content))
    .filter(Boolean)
    .slice(-5);

  if (customerMessages.length === 0) {
    return DEFAULT_SUMMARY;
  }

  return limitSummary(
    `Aus dem bisherigen Gespräch ergeben sich diese Angaben: ${customerMessages.join(' | ')}. Mein Küchenexperte kann darauf aufbauen und die nächsten passenden Schritte gezielter vorbereiten.`,
  );
}
