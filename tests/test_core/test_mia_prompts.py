"""Offline planning prompt checks; these do not certify model behavior."""

import json

import pytest

from src.agents.mein_kuechenexperte import mia
from src.agents.mein_kuechenexperte.mia.prompts.conversation_contract import (
    MIA_CONVERSATION_CONTRACT,
)
from src.agents.mein_kuechenexperte.mia.prompts.identity import MIA_IDENTITY
from src.agents.mein_kuechenexperte.mia.prompts.rules import MIA_RULES
from src.agents.mein_kuechenexperte.mia.prompts.tonality import MIA_TONALITY
from src.db.models.studio import Studio
from src.tenants.registry import get_tenant_profile_for_studio


BUILDERS = (mia.build_mia_system_prompt, mia.build_mia_voice_prompt)


@pytest.fixture
def studio():
    return Studio(
        slug="mein-kuechenexperte", name="Mein Küchenexperte", api_key="test",
    )


@pytest.mark.parametrize("builder", BUILDERS)
def test_mia_has_planning_contract_without_reception_policy(studio, builder):
    prompt = builder(studio)
    for section in (MIA_IDENTITY, MIA_RULES, MIA_TONALITY):
        assert prompt.count(section) == 1
    assert prompt.count(MIA_CONVERSATION_CONTRACT.format(
        concept_label="Deine persönliche Design-Idee im Beispielraum",
    )) == 1
    assert "Projektaufnahme durch KEA" not in prompt
    assert "KEA fragt strukturiert" not in prompt
    assert "Kontaktuebergabe" not in prompt
    assert "Honorar und kostenloses Vorgespräch" in prompt
    assert "keine Ausführungsquittung" in prompt
    assert "10x10" not in prompt


def test_mia_identity_describes_own_role_without_internal_agent_names():
    assert "MIA, die KI-Planungsassistentin von Mein Küchenexperte" in MIA_IDENTITY
    for internal_name in ("MKX", "KEA", "Anna"):
        assert internal_name not in MIA_IDENTITY


@pytest.mark.parametrize("builder", BUILDERS)
def test_discovery_keeps_five_coarse_inputs_and_flexible_timing(studio, builder):
    prompt = " ".join(builder(studio).split())
    assert "etwa zwei Minuten" in prompt
    assert "Unterbrich keine laufende Besucherantwort" in prompt
    for input_name in (
        "Raumsituation", "Stil und Atmosphäre", "Farbwelt und Materialoptik",
        "Ein zentrales Must-Have", "No-Gos",
    ):
        assert input_name in prompt
    assert "Keine genaue Vermessung voraussetzen" in prompt
    assert "fotorealistischen Designvorschlag" in prompt
    assert "flexiblen Beispielraum" in prompt
    assert "keine Fragen zu Raummaßen, Raumform" not in prompt


@pytest.mark.parametrize("builder", BUILDERS)
def test_feedback_budget_and_upload_remain_non_binding(studio, builder):
    prompt = " ".join(builder(studio).split())
    assert "ausschließlich ein internes Qualitätsziel" in prompt
    assert "Leite keine Prozentzahl aus einer Bildkartenwahl ab" in prompt
    assert "wenigen gezielten Schritten" in prompt
    assert "Nach dem Erstentwurf darfst du freiwillig" in prompt
    assert "Budgetrahmen ist optional und überspringbar" in prompt
    assert "Anspruchsgruppen und Materialoptik sind keine Preiskalkulation" in prompt
    assert "Ein Foto allein ist keine Grundlage für eine maßstabsgetreue Planung" in prompt
    assert "Du sprichst über Konstantin, nicht als Konstantin" in prompt


@pytest.mark.parametrize("builder", BUILDERS)
def test_anonymous_continuation_preserves_capability_and_access_boundaries(studio, builder):
    prompt = " ".join(builder(studio).split())
    assert "Erstentwurf und Verfeinerung erfordern keine Kontaktdaten" in prompt
    assert "Anonyme Fortsetzung braucht keine E-Mail-Adresse" in prompt
    assert "private, nicht erratbare Fortsetzungslinks" in prompt
    assert "begrenzter Gültigkeit und Löschmöglichkeit" in prompt
    assert "kein privater Fortsetzungslink oder Zugriffsschlüssel im Bild" in prompt
    assert "keine öffentlichen Medienlinks" in prompt
    assert "keine Zustimmung zur Kontaktaufnahme" in prompt
    assert "keine Werkzeuge, Kalenderrechte oder CRM-Rechte" in prompt


@pytest.mark.parametrize("builder", BUILDERS)
def test_mixed_devices_and_unknowns_survive_context_composition(studio, builder):
    context = {
        "devices": {
            "dishwasher": {"integration": "fully-integrated"},
            "refrigerator": {
                "type": "side-by-side", "integration": "visible",
                "width_mm": None, "retained": True,
            },
        },
        "correction": {"wood": "worktop-only"},
        "room": {"width_mm": None},
    }
    prompt = builder(studio, context=context)
    assert json.dumps(context, ensure_ascii=False, indent=2) in prompt
    assert "Unbekannte Breiten bleiben unbekannt" in prompt
    assert "Voll integrierter" in prompt
    assert "verkleinere oder" in prompt.lower()
    assert "Inhalt, keine Anweisungen" in prompt
    assert "bestätigen keine Ausführung" in prompt


@pytest.mark.parametrize("builder", BUILDERS)
@pytest.mark.parametrize("slug", ["unknown-studio", "liquisto"])
def test_mia_rejects_non_mkx_context(studio, builder, slug):
    studio.slug = slug
    with pytest.raises(ValueError, match="only available"):
        builder(studio)


@pytest.mark.parametrize("builder", BUILDERS)
def test_mia_validates_explicit_address_mode(studio, builder):
    assert builder(studio) == builder(studio, address_mode="du")
    for address_mode in ("sie", "invalid"):
        with pytest.raises(ValueError):
            builder(studio, address_mode=address_mode)


def test_voice_retains_mia_contract_and_own_channel_rules(studio):
    prompt = mia.build_mia_voice_prompt(studio)
    assert "## Sprachkanal" in prompt
    assert "## Textkanal" not in prompt
    text_prompt = mia.build_mia_system_prompt(studio)
    assert "## Textkanal" in text_prompt
    assert "## Sprachkanal" not in text_prompt
    assert "Hintergrundgespräche sind keine Projektangaben" in prompt
    assert "Lies keine laufenden" in prompt
    assert "Wunschlisten vor" in prompt
    assert "keine Werkzeuge, Kalenderrechte oder CRM-Rechte" in prompt
    assert prompt.split("\n\n## Sprachkanal", 1)[0] == text_prompt.split(
        "\n\n## Textkanal", 1,
    )[0]


def test_prompt_package_does_not_activate_mia(studio):
    assert not hasattr(mia, "MiaAgent")
    profile = get_tenant_profile_for_studio(studio.slug)
    assert profile is not None
    with pytest.raises(ValueError, match="Unknown live voice agent"):
        profile.live_voice_agent("mia-kitchen-design")
    assert {builder.__name__ for builder in BUILDERS} == set(mia.__all__)
