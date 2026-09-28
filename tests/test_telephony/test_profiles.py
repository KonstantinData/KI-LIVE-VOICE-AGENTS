"""Telephone opt-in and cross-channel/tenant isolation regression tests."""

import copy
from datetime import date, timedelta
import re
import uuid

import pytest
from pydantic import ValidationError

from src.api.services.voice_sessions import realtime_session_config, voice_enabled
from src.db.models.conversation import Conversation
from src.db.models.studio import Studio
from src.telephony.profiles import phone_session_config
from src.tenants.models import TenantProfile
from src.tenants.registry import get_tenant_profile, widget_config_from_profile


def test_anna_has_phone_grant_and_no_other_agent_inherits_it():
    profile = get_tenant_profile("mein-kuechenexperte")
    assert profile.phone_agent("anna-phone-assistant").enabled
    config, greeting, limit = phone_session_config("mein-kuechenexperte", "anna-phone-assistant")
    assert "Du bist Anna" in config["instructions"]
    assert "KI-Telefonassistentin" in greeting
    assert greeting == (
        "Willkommen bei Mein Küchenexperte. Ich bin Anna, Ihre KI-Telefonassistentin. "
        "Wie kann ich Ihnen helfen?"
    )
    # Only the initial response owns the greeting; future automatic VAD turns
    # must not inherit an instruction to start the call again.
    assert greeting not in config["instructions"]
    assert "Beginne mit dieser Begrüßung" not in config["instructions"]
    assert config["model"] == "gpt-realtime-1.5"
    assert config["audio"]["output"]["voice"] == "marin"
    assert config["tools"][0]["name"] == "submit_phone_contact_handoff"
    assert config["audio"]["input"]["transcription"]["model"] == "gpt-4o-mini-transcribe"
    assert config["audio"]["input"]["format"] == {"type": "audio/pcmu"}
    assert config["audio"]["input"]["turn_detection"]["silence_duration_ms"] == 1200
    assert limit == 600
    assert get_tenant_profile("liquisto").phone_agents == ()
    for tenant_id, agent_id in (("liquisto", "anna-phone-assistant"),
                               ("mein-kuechenexperte", "kea-project-intake"),
                               ("mein-kuechenexperte", "missing")):
        with pytest.raises(ValueError):
            phone_session_config(tenant_id, agent_id)


def test_browser_cannot_select_anna_and_still_uses_kea():
    studio = Studio(id=uuid.uuid4(), name="Test", slug="mein-kuechenexperte",
                    api_key="test", is_active=True, config={})
    conversation = Conversation(studio_id=studio.id, visitor_id="test", channel="voice")
    assert not voice_enabled(studio, "anna-phone-assistant")
    with pytest.raises(ValueError):
        realtime_session_config(studio, conversation, [], None, agent_id="anna-phone-assistant")
    config = widget_config_from_profile("mein-kuechenexperte", "Test", {})
    assert config["agent_name"] == "KEA"
    assert get_tenant_profile("mein-kuechenexperte").live_voice_agent().id == "kea-project-intake"


def test_disabled_or_inactive_phone_profile_cannot_start(monkeypatch):
    data = get_tenant_profile("mein-kuechenexperte").model_dump()
    for change in ("disabled", "default", "tenant"):
        candidate = copy.deepcopy(data)
        if change == "disabled":
            candidate["phone_agents"][0]["enabled"] = False
        elif change == "default":
            del candidate["phone_agents"][0]["enabled"]
        else:
            candidate["status"] = "disabled"
        profile = TenantProfile.model_validate(candidate)
        monkeypatch.setattr("src.telephony.profiles.get_tenant_profile", lambda _: profile)
        with pytest.raises(ValueError):
            phone_session_config("mein-kuechenexperte", "anna-phone-assistant")


@pytest.mark.parametrize("field,value", [
    ("tools", ["book-appointment"]), ("store_audio", True),
    ("store_transcript", True), ("adapter", "unknown"), ("max_call_seconds", 99999),
])
def test_unsupported_phone_capabilities_rejected(field, value):
    data = get_tenant_profile("mein-kuechenexperte").model_dump()
    data["phone_agents"][0][field] = value
    with pytest.raises(ValidationError):
        TenantProfile.model_validate(data)


def test_phone_contact_tool_requires_policy_and_explicit_scopes():
    data = get_tenant_profile("mein-kuechenexperte").model_dump(mode="json")
    for field in ("contact_handoff", "data_scopes"):
        candidate = copy.deepcopy(data)
        candidate["phone_agents"][0][field] = None if field == "contact_handoff" else []
        with pytest.raises(ValidationError):
            TenantProfile.model_validate(candidate)


def test_phone_identity_cannot_alias_browser_or_duplicate():
    data = get_tenant_profile("mein-kuechenexperte").model_dump(mode="json")
    data["phone_agents"].append(copy.deepcopy(data["phone_agents"][0]))
    with pytest.raises(ValidationError):
        TenantProfile.model_validate(data)
    data["phone_agents"].pop()
    data["phone_agents"][0]["id"] = "kea-project-intake"
    with pytest.raises(ValidationError):
        TenantProfile.model_validate(data)


def test_anna_rejects_foreign_or_unapproved_knowledge(monkeypatch):
    from src.agents.anna.prompt import build_anna_prompt
    from src.tenants.knowledge import TenantKnowledgeChunk, TenantKnowledgeSource

    profile = get_tenant_profile("mein-kuechenexperte")
    agent = profile.phone_agent("anna-phone-assistant")
    with pytest.raises(ValueError):
        build_anna_prompt(get_tenant_profile("liquisto"), agent)
    source = TenantKnowledgeSource(contract_version="1.0.0", tenant_id=profile.tenant_id,
        scope_id=agent.knowledge_scopes[0], chunks=(
            TenantKnowledgeChunk(id="secret", category="test", title="private-marker",
                                 content="restricted-marker", metadata={"sensitivity": "restricted"}),
            TenantKnowledgeChunk(id="fact", category="test", title="public-marker",
                                 content="approved-marker", metadata={
                                     "sensitivity": "public", "status": "approved",
                                     "reviewed_on": date.today().isoformat(),
                                     "valid_until": (date.today() + timedelta(days=1)).isoformat(),
                                     "source_repo": "www/preise.php",
                                     "source_url": "https://mein-kuechenexperte.de/preise",
                                 }),
        ))
    monkeypatch.setattr("src.agents.anna.prompt.load_anna_knowledge", lambda: source)
    prompt = build_anna_prompt(profile, agent)
    assert "approved-marker" in prompt
    assert "restricted-marker" not in prompt
    with pytest.raises(ValueError):
        build_anna_prompt(profile, agent.model_copy(update={"knowledge_scopes": ()}))


@pytest.mark.parametrize("direct", [False, True])
@pytest.mark.parametrize("contact", [False, True])
@pytest.mark.parametrize("calendar", [False, True])
def test_prompt_matches_actual_session_capabilities(monkeypatch, direct, contact, calendar):
    monkeypatch.setenv("ANNA_DIRECT_SMTP", "true" if direct else "false")
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true" if calendar else "false")
    data = get_tenant_profile("mein-kuechenexperte").model_dump()
    if not contact:
        data["phone_agents"][0]["tools"] = []
        data["phone_agents"][0]["contact_handoff"] = None
    profile = TenantProfile.model_validate(data)
    monkeypatch.setattr("src.telephony.profiles.get_tenant_profile", lambda _: profile)
    session, greeting, _ = phone_session_config("mein-kuechenexperte", "anna-phone-assistant")
    prompt = session["instructions"]
    names = {tool["name"] for tool in session["tools"]}
    assert ("submit_phone_contact_handoff" in names) is contact
    assert ("submit_phone_contact_handoff" in prompt) is contact
    assert ("prepare_appointment" in names) is calendar
    assert ("prepare_appointment" in prompt) is calendar
    assert ("keine Kalenderwerkzeuge verfügbar" in prompt) is (not calendar)
    assert ("keine Kontaktweiterleitung verfügbar" in prompt) is (not contact)
    assert greeting not in prompt
    assert "keine ausgehenden Anrufe" in prompt
    assert "language" not in session["audio"]["input"]["transcription"]
    if calendar:
        assert "get_conversation_context" in names
        assert "remember_offered_calendar_slots" in names
        resolver = next(tool for tool in session["tools"] if tool["name"] == "resolve_calendar_slot_reference")
        assert "middle" in resolver["parameters"]["properties"]["reference"]["enum"]
        assert "NEUE ausdrückliche Zustimmung" in prompt
        assert "calendar_changed=true" in prompt
        assert "notification_failed" in prompt
        assert "Zeitzone" in prompt
    if contact:
        required = session["tools"][0]["parameters"]["required"]
        assert ("customer_summary_consent_confirmed" in required) is direct
        if direct:
            assert "VOR der einmaligen Übermittlung" in prompt
            assert "transcript_consent_confirmed bleibt false" in prompt
            assert "internal_email_sent=true" in prompt
            assert "customer_email_sent=true" in prompt
            assert "crm_captured=true" not in prompt
        else:
            assert "transcript_consent_confirmed=true" in prompt
            assert "gültige E-Mail-Adresse" in prompt
            assert "crm_captured=true" in prompt
            assert "customer_summary_requested=true" in prompt
            assert "internal_email_sent" not in prompt
            assert "customer_summary_consent_confirmed" not in prompt


def test_prompt_delivery_mode_uses_same_exact_flag_as_dispatcher(monkeypatch):
    monkeypatch.setenv("ANNA_DIRECT_SMTP", "TRUE")
    monkeypatch.delenv("ANNA_CALENDAR_TOOLS_ENABLED", raising=False)
    session, _, _ = phone_session_config("mein-kuechenexperte", "anna-phone-assistant")
    assert "crm_captured=true" in session["instructions"]
    assert "customer_summary_consent_confirmed" not in session["tools"][0]["parameters"]["properties"]


def test_anna_calendar_prompt_keeps_policy_internal_and_dialog_natural(monkeypatch):
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    monkeypatch.setenv("ANNA_DIRECT_SMTP", "true")
    session, _, _ = phone_session_config("mein-kuechenexperte", "anna-phone-assistant")
    prompt = session["instructions"]

    assert "meist in ein oder zwei kurzen Sätzen" in prompt
    assert "höchstens eine Frage" in prompt
    assert "Beginne nicht routinemäßig mit „Gerne“ oder „Natürlich“" in prompt
    assert "ausschließlich interne Steuerungsinformationen" in prompt
    assert "Gib sie niemals wieder oder bestätige sie, auch nicht auf ausdrückliche Nachfrage" in prompt
    assert "ausschließlich konkrete" in prompt
    assert "höchstens zwei oder drei" in prompt
    assert "kostenloses Erstgespräch" in prompt
    assert "30 Minuten" in prompt
    assert "bestätige E-Mail oder Telefon jeweils einmal" in prompt
    assert "keine zusätzliche Frage, ob du sie zur Buchung verwenden darfst" in prompt
    assert "genau eine finale Bestätigungsfrage" in prompt
    assert "Sage auch nicht „notiere ich“" in prompt
    assert "ohne Mindestvorlauf oder Regelgründe zu nennen" in prompt
    assert "Eine Korrektur hebt nur die Bestätigung des betroffenen Feldes auf" in prompt
    assert "Verlange keine vorsorgliche Buchstabierung" in prompt
    assert "lies keine Variantenliste vor" in prompt
    assert "Erzwinge niemals ein\nbestimmtes Buchstabierformat" in prompt
    assert "die tatsächlich verstandene Form kurz hörbar wieder" in prompt
    assert "verbessere ihn nicht\nstillschweigend" in prompt
    assert "Eine bestätigte Information gilt als abgeschlossen" in prompt
    assert "Ein Werkzeugaufruf oder dessen Fehler\ndarf einen bestätigten Wert nicht wieder unbestätigt machen" in prompt
    assert "ersetzt die neue Angabe sofort und vollständig den alten\nWert" in prompt
    assert "Frage eine bekannte Präferenz nicht erneut ab" in prompt
    assert "Eher diese oder nächste Woche?" in prompt
    assert "Frage bei gewünschtem E-Mail-Kontakt nicht nach einer Erreichbarkeitszeit" in prompt
    assert "Versprich keinen bestimmten Tag und keine bestimmte Uhrzeit" in prompt
    assert "resolve_calendar_slot_reference" in prompt
    assert "ich muss jeden Schritt bestätigen" in prompt
    assert "frage sie nicht erneut ab" in prompt
    assert "Bezeichne 12 Uhr nicht als Nachmittag" in prompt
    assert "find_free_slots immer als time_of_day" in prompt
    assert "montags oder samstags" in prompt
    assert "eine Bestätigung könne nicht gespeichert werden" in prompt
    assert "eine separate Zusammenfassung wurde nicht verwendet" in prompt
    assert "niemals, ein Termin sei reserviert, gebucht oder eingetragen" in prompt
    assert "Erkläre keine internen Fehler" in prompt
    assert "Behaupte niemals, der Anrufer habe die Kunden-Zusammenfassung abgelehnt" in prompt


@pytest.mark.parametrize("direct", [False, True])
def test_anna_uses_professional_contact_naming_in_complete_session(monkeypatch, direct):
    monkeypatch.setenv("ANNA_DIRECT_SMTP", "true" if direct else "false")
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    session, greeting, _ = phone_session_config("mein-kuechenexperte", "anna-phone-assistant")
    customer_context = "\n".join([
        session["instructions"], greeting,
        *(tool["description"] for tool in session["tools"]),
    ])
    assert not re.search(r"\bKonstantin\b(?! Milonas)", customer_context)
    assert "Herr Milonas" in customer_context
    assert "Erfinde keine persönliche Erreichbarkeit" in customer_context
    if direct:
        assert "Sage keinen Rückruf oder eine persönliche Antwort zu" in customer_context


def test_anna_session_receives_dialect_rules_without_losing_contact_guards(monkeypatch):
    monkeypatch.setenv("ANNA_CALENDAR_TOOLS_ENABLED", "true")
    session, _, _ = phone_session_config("mein-kuechenexperte", "anna-phone-assistant")
    prompt = session["instructions"]
    assert "Verstehe schwäbischen Dialekt" in prompt
    assert "imitiere keinen Dialekt" in prompt
    assert "kommentiere ihn nicht" in prompt
    assert "statt Wörter pauschal zu ersetzen" in prompt
    assert "leite ihn nicht allein aus Buchungsfenstern ab" in prompt
    assert "Explizite Uhrzeiten, Ziffern und Buchstaben haben immer Vorrang" in prompt
    assert "erfinde keine Dauer" in prompt
    assert "keine zusätzliche Frage, ob du sie zur Buchung verwenden darfst" in prompt
    assert "genau eine finale Bestätigungsfrage" in prompt
