"""Fail closed before external transfer of the existing mail/CRM projection."""
import json
import re

COMMON = {"record_id", "version", "updated_at"}
FIELDS = {
    "liquisto-business-purpose": {"company", "purpose", "website", "source_policy"},
    "crm-companies": COMMON | {"name", "industry", "lifecycle_stage"},
    "crm-deals": COMMON | {"name", "pipeline_id", "stage_id", "amount", "expected_close_date", "probability_percent"},
    "crm-open-tasks": COMMON | {"summary", "occurred_at", "status", "priority", "due_at", "related_records"},
}
SENSITIVE = re.compile(
    r"sk-[A-Za-z0-9_-]{16,}|\bBearer\s+[A-Za-z0-9_.-]{20,}|"
    r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|AIza[0-9A-Za-z_-]{30,}|"
    r"gh[pousr]_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{20,}|"
    r"\b[A-Za-z0-9_-]{48,}\b|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    r"\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]{10,}|"
    r"\b(?:password|passwort|api[_ -]?key|client[_ -]?secret)\s*[:=]\s*\S+|"
    r"\b\d{3}-\d{2}-\d{4}\b|\b(?:IBAN|Kontonummer|Sozialversicherungsnummer)\b|"
    r"\b(?:patient(?:in)?|diagnose|HIV|schwanger|sexuelle orientierung|"
    r"sexual orientation|politische meinung|political opinion|"
    r"religionszugehörigkeit|ethnische herkunft|ethnic origin|biometrisch|biometric|"
    r"gewerkschaftszugehörigkeit|trade union membership)\b",
    re.IGNORECASE,
)


def check_external_projection(messages: list[dict[str, str]]) -> None:
    """Known fields only; deny known secret/sensitive markers, never mask silently.

    This is a conservative deterministic guard, not semantic classification of
    every possible free-text personal detail. Names/business text are retained
    under the approved role scope. A denied message needs operator review.
    """
    data = json.loads(messages[1]["content"])
    if set(data) != {"prompt", "context"} or not isinstance(data["prompt"], str):
        raise ValueError
    if SENSITIVE.search(json.dumps(data, ensure_ascii=False)):
        raise ValueError
    for source in data["context"]:
        identifier = source["source_id"]
        if identifier not in FIELDS or not isinstance(source["content"], list):
            raise ValueError  # Unstructured context is not approved external data.
        if len(source["content"]) > 1:
            raise ValueError
        for record in source["content"]:
            if not isinstance(record, dict) or set(record) != FIELDS[identifier]:
                raise ValueError
            required = ({"company", "purpose", "website", "source_policy"}
                        if identifier == "liquisto-business-purpose" else
                        {"record_id", "name", "pipeline_id", "stage_id"}
                        if identifier == "crm-deals" else {"record_id", "name"}
                        if identifier == "crm-companies" else {"record_id", "summary", "occurred_at"})
            if any(not isinstance(record[key], str) or not record[key].strip() for key in required):
                raise ValueError
            for key, value in record.items():
                if key in {"amount", "related_records", "version", "probability_percent"}:
                    continue
                if value is not None and (not isinstance(value, str) or len(value) > 240):
                    raise ValueError
            if identifier == "liquisto-business-purpose":
                if (record["company"] != "Liquisto" or record["website"] != "https://liquisto.com"
                        or record["source_policy"] != "registry/tenants/liquisto/assistant-sources.json"):
                    raise ValueError
                continue
            if type(record["version"]) is not int or record["version"] < 1:
                raise ValueError
            if not record["record_id"]:
                raise ValueError
            if identifier == "crm-deals":
                amount = record["amount"]
                if amount is not None and (
                    not isinstance(amount, dict) or set(amount) != {"amount_minor", "currency"}
                    or type(amount["amount_minor"]) is not int
                    or not isinstance(amount["currency"], str)
                    or not re.fullmatch(r"[A-Z]{3}", amount["currency"])
                ):
                    raise ValueError
                probability = record["probability_percent"]
                if probability is not None and (type(probability) not in {int, float}
                                                or not 0 <= probability <= 100):
                    raise ValueError
            if identifier == "crm-open-tasks":
                if record["status"] != "open" or not isinstance(record["related_records"], list):
                    raise ValueError
                if len(record["related_records"]) > 8:
                    raise ValueError
                for reference in record["related_records"]:
                    if (not isinstance(reference, dict) or set(reference) != {"record_id", "record_type"}
                            or any(not isinstance(value, str) or len(value) > 240
                                   for value in reference.values())):
                        raise ValueError
