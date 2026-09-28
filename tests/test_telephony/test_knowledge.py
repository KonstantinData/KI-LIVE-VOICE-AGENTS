"""Knowledge freshness, provenance and agent isolation regression tests."""

from datetime import date
import json

import pytest

from src.agents.anna import knowledge
from src.tenants.knowledge import TenantKnowledgeChunk


def fact(**metadata):
    return TenantKnowledgeChunk(
        id="example", category="services", title="Example", content="Business fact",
        metadata={
            "sensitivity": "public", "status": "approved",
            "reviewed_on": "2026-09-21", "valid_until": "2026-10-21",
            "source_repo": "www/preise.php",
            "source_url": "https://mein-kuechenexperte.de/preise",
            **metadata,
        },
    )


@pytest.mark.parametrize("metadata", [
    {"sensitivity": "restricted"}, {"status": "draft"}, {"status": "conflicting"},
    {"reviewed_on": "2026-09-22"}, {"valid_until": "2026-09-20"},
    {"reviewed_on": "invalid"}, {"valid_until": ""}, {"source_repo": ""},
    {"source_url": "https://another-tenant.example/preise"},
    {"source_url": "https://mein-kuechenexperte.de.attacker.example/preise"},
])
def test_unapproved_or_stale_facts_are_withheld(metadata):
    assert not knowledge.usable_public_fact(fact(**metadata), today=date(2026, 9, 21))


def test_review_window_is_inclusive():
    assert knowledge.usable_public_fact(fact(), today=date(2026, 9, 21))
    assert knowledge.usable_public_fact(fact(), today=date(2026, 10, 21))
    assert not knowledge.usable_public_fact(fact(), today=date(2026, 10, 22))


def test_registry_snapshot_has_traceable_public_facts():
    source = knowledge.load_anna_knowledge()
    assert source.chunks
    assert all(knowledge.usable_public_fact(chunk, today=date(2026, 9, 25))
               for chunk in source.chunks)
    assert len({chunk.id for chunk in source.chunks}) == len(source.chunks)


def test_loader_rejects_foreign_scope_and_duplicate_identifiers(tmp_path, monkeypatch):
    path = tmp_path / "anna.json"
    monkeypatch.setattr(knowledge, "KNOWLEDGE_PATH", path)
    data = {
        "contract_version": "1.0.0", "tenant_id": knowledge.TENANT_ID,
        "scope_id": knowledge.SCOPE_ID, "chunks": [fact().model_dump()],
    }
    for changed in (
        {"tenant_id": "liquisto"}, {"scope_id": "mein-kuechenexperte-studio-knowledge"},
        {"chunks": [fact().model_dump(), fact().model_dump()]},
    ):
        path.write_text(json.dumps({**data, **changed}), encoding="utf-8")
        with pytest.raises(ValueError):
            knowledge.load_anna_knowledge()


def test_edits_are_loaded_for_next_call(tmp_path, monkeypatch):
    path = tmp_path / "anna.json"
    monkeypatch.setattr(knowledge, "KNOWLEDGE_PATH", path)
    data = {
        "contract_version": "1.0.0", "tenant_id": knowledge.TENANT_ID,
        "scope_id": knowledge.SCOPE_ID, "chunks": [fact().model_dump()],
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    assert knowledge.load_anna_knowledge().chunks[0].content == "Business fact"
    data["chunks"][0]["content"] = "Updated fact"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert knowledge.load_anna_knowledge().chunks[0].content == "Updated fact"
