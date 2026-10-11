"""Request-local technical references for receipt-verified regular mail only."""
from __future__ import annotations

import json
import re
import secrets

from src.api.services.liquisto_mail_data import FIELDS, check_external_projection
from src.api.services.liquisto_mail_openai import parse_json

REFERENCE_CONTRACT = "olivia-mail-opaque-refs-v1"
SOURCE_RECORD_TYPES = {
    "crm-companies": "company", "crm-deals": "deal", "crm-open-tasks": "activity",
}
REFERENCE_TYPES = frozenset({"company", "contact", "deal", "activity", "relationship"})
REFERENCE_RULES = (
    "\nrecord_id bezeichnet ausschliesslich eine kurzlebige technische Referenz "
    "dieser Anfrage, keine echte CRM-ID. Gleiche Referenzen desselben record_type "
    "bezeichnen denselben Datensatz; verknuepfte Datensaetze ohne gelieferten Inhalt "
    "bleiben unbekannt. Gib Referenztokens nicht in der Antwort aus. Belege Fakten "
    "weiter mit dem Quellenlabel. Referenzen ermoeglichen keine Aktionen oder Abrufe."
)


def _identifier(value: object) -> str:
    if (not isinstance(value, str) or not value.strip() or len(value) > 240
            or any(ord(character) < 32 or ord(character) == 127 for character in value)):
        raise ValueError
    return value  # Exact equality, never normalize or extract a credential suffix.


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)


def prepare_external_reference_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Called after signed source/role/payload validation, before external preflight.

    Only exact typed CRM ID slots are non-exportable. Everything else is retained
    and checked by the unchanged guard. No ID-derived hashes, maps, or reverse
    substitution leave this function; bindings exist in memory for this call.
    """
    if (len(messages) != 2 or [item.get("role") for item in messages] != ["system", "user"]
            or any(set(item) != {"role", "content"} or not isinstance(item["content"], str)
                   for item in messages)):
        raise ValueError
    data = parse_json(messages[1]["content"])
    if (not isinstance(data, dict) or set(data) != {"prompt", "context"}
            or not isinstance(data["prompt"], str) or not isinstance(data["context"], list)
            or len(data["context"]) > 4):
        raise ValueError
    slots = []
    source_ids = set()
    for source in data["context"]:
        if (not isinstance(source, dict)
                or set(source) != {"source_id", "label", "observed_at", "content", "model_projection"}
                or not isinstance(source["source_id"], str)
                or source["source_id"] not in FIELDS or source["source_id"] in source_ids
                or not isinstance(source["content"], list) or len(source["content"]) > 1):
            raise ValueError
        source_ids.add(source["source_id"])
        projection = source["model_projection"]
        if (not isinstance(projection, dict)
                or set(projection) != {"provided_records", "shown_records", "truncated"}
                or type(projection["provided_records"]) is not int
                or type(projection["shown_records"]) is not int
                or type(projection["truncated"]) is not bool
                or projection["provided_records"] < len(source["content"])
                or projection["shown_records"] != len(source["content"])
                or projection["truncated"] != (projection["provided_records"] > len(source["content"]))):
            raise ValueError
        for record in source["content"]:
            if not isinstance(record, dict) or set(record) != FIELDS[source["source_id"]]:
                raise ValueError
            if source["source_id"] == "liquisto-business-purpose":
                continue
            slots.append((record, SOURCE_RECORD_TYPES[source["source_id"]], _identifier(record["record_id"])))
            if source["source_id"] == "crm-open-tasks":
                if not isinstance(record["related_records"], list) or len(record["related_records"]) > 8:
                    raise ValueError
                for reference in record["related_records"]:
                    if (not isinstance(reference, dict) or set(reference) != {"record_id", "record_type"}
                            or not isinstance(reference["record_type"], str)
                            or reference["record_type"] not in REFERENCE_TYPES):
                        raise ValueError
                    slots.append((reference, reference["record_type"], _identifier(reference["record_id"])))

    original_ids = {original for _, _, original in slots}
    for container, _, _ in slots:
        container["record_id"] = None
    # IDs repeated in user-visible text are not silently rewritten or exported.
    if any(original in text for text in _strings(data) for original in original_ids):
        raise ValueError
    for container, _, _ in slots:
        container["record_id"] = "ref-pending"
    prepared = [dict(messages[0]), {"role": "user", "content": json.dumps(data, ensure_ascii=False)}]
    check_external_projection(prepared)  # Full unchanged guard over every retained value.

    bindings: dict[tuple[str, str], str] = {}
    used = set()
    for container, record_type, original in slots:
        binding = (record_type, original)
        if binding not in bindings:
            for _ in range(8):
                token = secrets.token_hex(12)
                if not re.fullmatch(r"[0-9a-f]{24}", token):
                    raise ValueError
                reference = "ref-" + token
                if reference not in used and reference not in original_ids:
                    break
            else:
                raise ValueError
            used.add(reference)
            bindings[binding] = reference
        container["record_id"] = bindings[binding]
    for source in data["context"]:
        source["model_projection"]["reference_contract"] = REFERENCE_CONTRACT
    prepared[0]["content"] += REFERENCE_RULES
    prepared[1]["content"] = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    check_external_projection(prepared)
    return prepared
