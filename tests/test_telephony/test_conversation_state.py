from src.telephony.conversation_state import PhoneConversationState


def test_booking_email_purpose_is_revision_bound_and_does_not_authorize_phone():
    state = PhoneConversationState()
    details = {"name": "Test Person", "email": "test@example.com"}
    state.confirm("email", details["email"])
    assert not state.contact_ready(details)
    state.confirm_booking_email(details["email"])
    assert state.contact_ready(details)
    state.confirm("phone", "0123456789")
    assert not state.contact_ready({**details, "phone": "0123456789"})
    state.confirm("email", "corrected@example.com")
    corrected = {**details, "email": "corrected@example.com"}
    assert not state.contact_ready(corrected)
    state.confirm_booking_email(corrected["email"])
    assert state.contact_ready(corrected)


def test_state_keeps_preferences_and_identity_for_the_whole_call():
    state = PhoneConversationState()
    state.ingest_transcript(
        "Anrufer: Mein Name ist Konstantin Milonas und ich brauche ein Erstgespräch.\n"
        "Anrufer: Nächste Woche Donnerstag am frühen Abend, am 5. Oktober.\n"
        "Anrufer: Für die Rückmeldung bitte per E-Mail."
    )
    state.remember("request_topic", "Beratungstermin vereinbaren")

    snapshot = state.snapshot()
    assert snapshot["customer_name"] == "Konstantin Milonas"
    assert snapshot["first_name"] == "Konstantin"
    assert snapshot["last_name"] == "Milonas"
    assert snapshot["appointment_type"] == "Kostenloses Erstgespräch"
    assert snapshot["preferred_week"] == "next_week"
    assert snapshot["preferred_day"] == "donnerstag"
    assert snapshot["preferred_date"] == "5. oktober"
    assert snapshot["preferred_time_of_day"] == "early_evening"
    assert snapshot["preferred_contact_method"] == "email"
    assert snapshot["request_topic"] == "Beratungstermin vereinbaren"
    assert snapshot["name_confirmed"] is True


def test_correction_replaces_only_changed_value_and_stale_tool_data_cannot_restore_it():
    state = PhoneConversationState()
    state.remember("customer_name", "Konstantin Milonas", confirmed=True)
    assert state.confirm("email", "info@condata.de")
    assert state.confirm("phone", "0176 23785746")
    assert state.confirm("booking_consent")

    assert state.confirm("email", "info@condata.io")
    assert state.email == "info@condata.io"
    assert state.is_confirmed("email")
    assert state.is_confirmed("phone")
    assert not state.is_confirmed("booking_consent")

    enriched = state.enrich_handoff({
        "first_name": "", "last_name": "", "email": "info@condata.de",
        "phone": "0176 23785746", "preferred_channel": "email",
    }, "")
    assert enriched["email"] == "info@condata.io"
    assert "info@condata.de" not in enriched.values()
    assert enriched["phone"] == "0176 23785746"
    assert enriched["email_confirmed"] is True


def test_tool_error_does_not_clear_state_and_close_does():
    state = PhoneConversationState()
    state.remember("customer_name", "Konstantin Milonas", confirmed=True)
    state.confirm("email", "info@condata.io")
    state.remember("preferred_time_of_day", "early_evening")
    before = state.snapshot()

    # A tool error has no state mutation path; later handoff still sees the same facts.
    enriched = state.enrich_handoff({
        "first_name": "", "last_name": "", "email": "", "phone": "",
    }, "")
    assert state.snapshot() == before
    assert enriched["email"] == "info@condata.io"
    assert enriched["first_name"] == "Konstantin"

    state.clear()
    assert state.snapshot() == PhoneConversationState().snapshot()
