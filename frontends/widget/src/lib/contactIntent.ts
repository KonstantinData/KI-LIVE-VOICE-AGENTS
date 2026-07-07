interface ContactChoice {
  id: string;
  label: string;
}

const CONTACT_TERMS = [
  'kontaktdaten',
  'kontaktaufnahme',
  'kontakt',
  'rückruf',
  'rueckruf',
  'zurückrufen',
  'zurueckrufen',
  'anrufen',
  'telefon',
  'telefonnummer',
  'email',
  'e-mail',
  'mail',
  'erreichbarkeit',
  'erreichen',
  'melden',
];

const CONTACT_PHRASES = [
  'termin vereinbaren',
  'termin buchen',
  'termin ausmachen',
  'beratungstermin',
];

export function hasContactIntent(text: string): boolean {
  const normalized = text.toLowerCase();
  return (
    CONTACT_TERMS.some((term) => normalized.includes(term)) ||
    CONTACT_PHRASES.some((phrase) => normalized.includes(phrase))
  );
}

export function isContactChoice(choice: ContactChoice): boolean {
  return (
    choice.id === 'next_contact' ||
    choice.id === 'global_contact' ||
    hasContactIntent(choice.label)
  );
}
