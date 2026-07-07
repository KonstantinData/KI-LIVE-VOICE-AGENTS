"""
KEA Text Flow
=============
What:    Deterministic text-chat runtime for the Mein Küchenexperte tenant.
Does:    Persists controlled KEA orientation turns and returns choice payloads.
Why:     KEA needs a guided website flow without drifting into consulting.
Who:     The public widget WebSocket handler.
Depends: sqlalchemy, src.api.services.kea_text_flow_nodes, db models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.api.services.kea_text_flow_nodes import NODES, START_NODE, SUMMARY_NODE
from src.api.services.kea_text_flow_nodes import FlowChoice, FlowNode, FlowResponse, choice
from src.db.models.conversation import Conversation
from src.db.models.message import Message


class KeaTextFlow:
    """Tenant-bound deterministic KEA text flow."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def start(self, conversation: Conversation) -> FlowResponse:
        """Starts or resumes the deterministic text flow."""
        state = self._state(conversation)
        if not state.get("node"):
            state["node"] = START_NODE
            state["slots"] = {}
            self._set_state(conversation, state)
        node = NODES.get(str(state["node"]), NODES[START_NODE])
        return await self._assistant(conversation, node.text, node.choices)

    async def handle(
        self,
        conversation: Conversation,
        *,
        message_text: str,
        action_id: str | None = None,
        action_label: str | None = None,
    ) -> FlowResponse:
        """Handles one text or choice turn."""
        user_content = (action_label or message_text).strip()
        if user_content:
            await self._save(conversation, "user", user_content)

        state = self._state(conversation)
        state.setdefault("slots", {})
        current = str(state.get("node") or START_NODE)
        global_response = self._global_intent(message_text) if not action_id else None
        if global_response is not None:
            state["node"] = global_response.id
            self._set_state(conversation, state)
            return await self._assistant(
                conversation,
                global_response.text,
                global_response.choices,
            )

        if action_id:
            next_node = self._advance_by_choice(current, action_id, state)
            return await self._respond_for_node(conversation, state, next_node)

        if current in {"free_note", "capture_note"} and message_text.strip():
            self._slots(state)["note"] = message_text.strip()
            return await self._summary(conversation, state)

        routed = self._route_free_text(message_text)
        return await self._respond_for_node(conversation, state, routed)

    def _global_intent(self, text: str) -> FlowNode | None:
        lower = text.lower()
        if any(word in lower for word in ("upload", "hochladen", "unterlagen", "pdf", "foto")):
            return FlowNode(
                id="global_upload",
                text=(
                    "Für eine konkrete Einordnung helfen Angebot, Planung, Grundriss "
                    "oder Fotos. Nutzen Sie dafür bitte den Upload-Bereich im Chatfenster. "
                    "Die Dateien werden erst hochgeladen, wenn Sie den Upload bestätigen."
                ),
                choices=(choice("back_start", "Zurück zur Einordnung", START_NODE),),
            )
        if any(word in lower for word in ("kontakt", "rückruf", "anrufen", "email", "e-mail", "mensch")):
            return FlowNode(
                id="global_contact",
                text=(
                    "Gern. Bitte nutzen Sie das Kontaktformular hier im Chatfenster. "
                    "So vermeiden wir Hör- oder "
                    "Übertragungsfehler und können Ihre Anfrage sauber zuordnen."
                ),
                choices=(choice("back_start", "Zurück zur Einordnung", START_NODE),),
            )
        if "strategie-check" in lower or "strategie check" in lower:
            return self._strategy_check_node()
        if any(word in lower for word in ("preis", "kosten", "kostet", "paket", "angebot")):
            return FlowNode(
                id="global_price",
                text=(
                    "Das hängt davon ab, ob Sie noch Orientierung suchen, schon ein "
                    "Angebot vorliegen haben oder im Bau-/Sanierungsprozess stecken. "
                    "Ich ordne Sie kurz ein und nenne dann den passenden nächsten Schritt."
                ),
                choices=(
                    NODES[START_NODE].choices[1],
                    NODES[START_NODE].choices[2],
                    NODES[START_NODE].choices[0],
                ),
            )
        return None

    def _strategy_check_node(self) -> FlowNode:
        return FlowNode(
            id="global_strategy_price",
            text=(
                "Der Strategie-Check ist sinnvoll, wenn Sie vor dem Küchenkauf "
                "Struktur, Prioritäten oder einen neutralen Blick auf die nächsten "
                "Schritte brauchen. Auf der Website ist er mit 42,80 EUR inkl. "
                "MwSt. ausgewiesen. Für die genaue Passung frage ich zuerst kurz: "
                "Geht es eher um Budget, Planung oder ein konkretes Angebot?"
            ),
            choices=(
                choice("buy_budget", "Budget und Prioritäten", "buy_deadline", {"path": "vor_kuechenkauf", "focus": "budget_prioritaeten"}),
                choice("buy_studio", "Planung vorbereiten", "buy_deadline", {"path": "vor_kuechenkauf", "focus": "studio_vorbereitung"}),
                choice("offer_price", "Konkretes Angebot", "offer_stage", {"path": "angebot_pruefen", "focus": "preis_vergleichbarkeit"}),
            ),
        )

    def _route_free_text(self, text: str) -> str:
        lower = text.lower()
        if any(word in lower for word in ("angebot", "vertrag", "preis", "vergleich", "unterschrift")):
            return "offer_focus"
        if any(word in lower for word in ("sanierung", "renovierung", "hausbau", "anschluss", "grundriss")):
            return "build_stage"
        if any(word in lower for word in ("start", "orientierung", "küchenkauf", "kuechenkauf", "studio")):
            return "buy_focus"
        return "free_note"

    async def _respond_for_node(
        self,
        conversation: Conversation,
        state: dict[str, Any],
        next_node: str,
    ) -> FlowResponse:
        if next_node == SUMMARY_NODE:
            return await self._summary(conversation, state)
        if next_node == "global_upload":
            node = self._global_intent("upload")
            state["node"] = next_node
            self._set_state(conversation, state)
            return await self._assistant(conversation, node.text, node.choices) if node else await self.start(conversation)
        if next_node == "global_contact":
            node = self._global_intent("kontakt")
            state["node"] = next_node
            self._set_state(conversation, state)
            return await self._assistant(conversation, node.text, node.choices) if node else await self.start(conversation)
        state["node"] = next_node
        self._set_state(conversation, state)
        node = NODES.get(next_node, NODES[START_NODE])
        return await self._assistant(conversation, node.text, node.choices)

    def _advance_by_choice(self, current: str, action_id: str, state: dict[str, Any]) -> str:
        node = NODES.get(current, NODES[START_NODE])
        for item in node.choices:
            if item.id == action_id:
                if item.set_slots:
                    self._slots(state).update(item.set_slots)
                return item.next_node
        for item in NODES[START_NODE].choices:
            if item.id == action_id:
                if item.set_slots:
                    self._slots(state).update(item.set_slots)
                return item.next_node
        strategy_actions = {
            "buy_budget": ("buy_deadline", {"path": "vor_kuechenkauf", "focus": "budget_prioritaeten"}),
            "buy_studio": ("buy_deadline", {"path": "vor_kuechenkauf", "focus": "studio_vorbereitung"}),
            "offer_price": ("offer_stage", {"path": "angebot_pruefen", "focus": "preis_vergleichbarkeit"}),
        }
        if action_id in strategy_actions:
            next_node, slots = strategy_actions[action_id]
            self._slots(state).update(slots)
            return next_node
        if action_id == "next_upload":
            return "global_upload"
        if action_id == "next_contact":
            return "global_contact"
        if action_id == "back_start":
            return START_NODE
        return START_NODE

    async def _summary(self, conversation: Conversation, state: dict[str, Any]) -> FlowResponse:
        slots = self._slots(state)
        state["node"] = "next_step"
        self._set_state(conversation, state)
        content = (
            "Zwischenstand:\n"
            f"- Bereich: {self._label(slots.get('path'))}\n"
            f"- Fokus: {self._label(slots.get('focus') or slots.get('stage'))}\n"
            f"- Zeitdruck: {self._label(slots.get('deadline'))}\n"
        )
        if slots.get("note"):
            content += f"- Ihre Ergänzung: {slots['note']}\n"
        content += "\nWas möchten Sie als nächsten Schritt tun?"
        return await self._assistant(
            conversation,
            content,
            (
                choice("next_upload", "Unterlagen im Chatfenster hochladen", "global_upload"),
                choice("next_contact", "Kontaktformular öffnen", "global_contact"),
                choice("back_start", "Weitere Situation einordnen", START_NODE),
            ),
        )

    async def _assistant(
        self,
        conversation: Conversation,
        content: str,
        choices: tuple[FlowChoice, ...] = (),
    ) -> FlowResponse:
        await self._save(
            conversation,
            "assistant",
            content,
            tool_calls=[{"type": "kea_text_flow", "choices": [item.__dict__ for item in choices]}],
        )
        return FlowResponse(content=content, choices=choices)

    async def _save(
        self,
        conversation: Conversation,
        role: str,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> None:
        self._session.add(Message(conversation_id=conversation.id, role=role, content=content, tool_calls=tool_calls))

    def _state(self, conversation: Conversation) -> dict[str, Any]:
        metadata = dict(conversation.metadata_ or {})
        return dict(metadata.get("kea_text_flow") or {})

    def _set_state(self, conversation: Conversation, state: dict[str, Any]) -> None:
        metadata = dict(conversation.metadata_ or {})
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        metadata["kea_text_flow"] = state
        conversation.metadata_ = metadata

    @staticmethod
    def _slots(state: dict[str, Any]) -> dict[str, str]:
        slots = state.setdefault("slots", {})
        return slots
    @staticmethod
    def _label(value: str | None) -> str:
        if not value:
            return "noch offen"
        labels = {
            "bau_sanierung": "Bau / Sanierung / Renovierung",
            "vor_kuechenkauf": "Vor dem Küchenkauf Klarheit gewinnen",
            "angebot_pruefen": "Angebot / Planung einschätzen",
            "sehr_hoch": "sehr kurzfristig",
            "hoch": "hoch",
            "mittel": "mittel",
            "offen": "offen",
        }
        return labels.get(value, value.replace("_", " "))
