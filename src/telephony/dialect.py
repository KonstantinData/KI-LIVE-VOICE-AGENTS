"""Bounded Swabian appointment semantics; never rewrite customer identity data."""

import re


def appointment_language(text: str) -> str:
    """Normalize only scheduling expressions, preserving context-sensitive fillers."""
    text = text.casefold()
    for pattern, replacement in (
        (r"\bnäch(?:s|sch)te\s+woch\b", "nächste woche"),
        (r"\b(am|morgen|morga|heute|heut)\s+(?:middag|mittag)\b", r"\1 nachmittag"),
        (r"\bobed\b", "abend"),
        (r"\bmorga\b", "morgen"),
        (r"\b(?:net|ned)\b", "nicht"),
    ):
        text = re.sub(pattern, replacement, text)
    return text


def spoken_clock(text: str, daypart: str) -> tuple[str, str] | None:
    """Return a resolved clock or a clarification; explicit 24-hour values win."""
    explicit = re.search(r"\b(?:um\s+)?(\d{1,2})(?::(\d{2}))?\s*uhr\b", text)
    if not explicit:
        explicit = re.search(r"\b(\d{1,2}):(\d{2})\b", text)
    if not explicit and re.search(r"\bum\s+(?:mittag|middag)\b", text):
        return "12:00", ""
    if explicit:
        hour, minute = int(explicit[1]), int(explicit[2] or 0)
        if hour > 23 or minute > 59:
            return "", "Welche Uhrzeit meinen Sie genau?"
        if hour >= 12 or hour == 0 or explicit[1].startswith("0"):
            return f"{hour:02}:{minute:02}", ""
    else:
        match = re.search(
            r"\b(am|gegen|um|halb|viertel|dreiviertel)\s+"
            r"(ein[se]?|zwei[e]?|drei[e]?|vier[e]?|fünf[e]?|sechs[e]?|"
            r"sieben[e]?|acht[e]?|neun[e]?|zehn[e]?|elf[e]?|zwölf[e]?)\b", text,
        )
        if not match:
            return None
        words = ["ein", "zwei", "drei", "vier", "fünf", "sechs", "sieben",
                 "acht", "neun", "zehn", "elf", "zwölf"]
        hour = next(index + 1 for index, word in enumerate(words) if match[2].startswith(word))
        minute = {"halb": 30, "viertel": 15, "dreiviertel": 45}.get(match[1], 0)
        if minute:
            hour = (hour - 1) % 12
    if daypart in {"afternoon", "early_evening", "evening"}:
        return f"{hour % 12 + 12:02}:{minute:02}", ""
    if daypart == "morning":
        return f"{hour % 12:02}:{minute:02}", ""
    return "", f"Meinen Sie {hour % 12:02}:{minute:02} oder {hour % 12 + 12:02}:{minute:02} Uhr?"
