"""
KEA Text Flow Nodes
===================
What:    Static node definitions for the Mein Küchenexperte KEA text flow.
Does:    Defines choices and prompts for the three website-oriented entry paths.
Why:     Keeping static flow data separate keeps the runtime service small.
Who:     src.api.services.kea_text_flow
Depends: dataclasses
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FlowChoice:
    """One selectable user-facing flow choice."""

    id: str
    label: str
    next_node: str
    set_slots: dict[str, str] | None = None


@dataclass(frozen=True)
class FlowNode:
    """One deterministic KEA text-chat node."""

    id: str
    text: str
    choices: tuple[FlowChoice, ...] = ()


@dataclass(frozen=True)
class FlowResponse:
    """Response sent to the widget."""

    content: str
    choices: tuple[FlowChoice, ...] = ()


def choice(
    choice_id: str,
    label: str,
    next_node: str,
    slots: dict[str, str] | None = None,
) -> FlowChoice:
    """Creates one reusable flow choice."""
    return FlowChoice(choice_id, label, next_node, slots)


START_NODE = "start"
SUMMARY_NODE = "summary"


NODES: dict[str, FlowNode] = {
    START_NODE: FlowNode(
        id=START_NODE,
        text=(
            "Willkommen! Ich bin KEA. Ich helfe Ihnen, Ihre Küchensituation "
            "besser einzuordnen, damit Sie den nächsten Schritt sicherer "
            "entscheiden können. Worum geht es bei Ihnen gerade?"
        ),
        choices=(
            choice(
                "start_build",
                "Ich baue, saniere oder renoviere und möchte früh wissen, worauf ich achten muss",
                "build_stage",
                {"path": "bau_sanierung"},
            ),
            choice(
                "start_buy",
                "Ich möchte vor dem Küchenkauf Klarheit gewinnen",
                "buy_focus",
                {"path": "vor_kuechenkauf"},
            ),
            choice(
                "start_offer",
                "Ich habe ein Angebot und möchte es besser einschätzen können",
                "offer_focus",
                {"path": "angebot_pruefen", "has_offer": "true"},
            ),
            choice(
                "start_free",
                "Ich möchte mein Anliegen kurz selbst beschreiben",
                "free_note",
                {"path": "freitext"},
            ),
        ),
    ),
    "build_stage": FlowNode(
        id="build_stage",
        text=(
            "Gut, dass Sie sich früh damit beschäftigen. Gerade bei Bau, "
            "Sanierung oder Renovierung können Küchenentscheidungen Auswirkungen "
            "auf Anschlüsse, Maße, Zeitplan und andere Beteiligte haben. "
            "Wo stehen Sie aktuell?"
        ),
        choices=(
            choice("build_early", "Ich bin noch in der frühen Planungsphase", "build_detail", {"stage": "fruehe_planung"}),
            choice("build_floorplan", "Grundriss oder Raumaufteilung stehen bereits fest", "build_detail", {"stage": "grundriss_fest"}),
            choice("build_connections", "Anschlüsse, Elektro oder Wasser müssen noch abgestimmt werden", "build_detail", {"stage": "anschluesse_offen"}),
            choice("build_next", "Die nächsten Schritte stehen bald an und ich möchte nichts übersehen", "build_detail", {"stage": "naechste_schritte"}),
        ),
    ),
    "build_detail": FlowNode(
        id="build_detail",
        text=(
            "Wobei möchten Sie zuerst Sicherheit gewinnen? Es geht hier um eine "
            "erste Einordnung, nicht um eine verbindliche Fachplanung."
        ),
        choices=(
            choice("build_layout", "Grundriss, Küchenform oder Laufwege", "deadline", {"focus": "grundriss_layout"}),
            choice("build_tech", "Anschlüsse, Elektro, Wasser oder Abluft", "deadline", {"focus": "technik_anschluesse"}),
            choice("build_budget", "Budgetrahmen und Prioritäten", "deadline", {"focus": "budget_prioritaeten"}),
            choice("build_complete", "Vollständigkeit vor dem nächsten Schritt", "deadline", {"focus": "vollstaendigkeit"}),
        ),
    ),
    "buy_focus": FlowNode(
        id="buy_focus",
        text=(
            "Dann sortieren wir zuerst, was Ihnen vor dem Küchenkauf am meisten "
            "Klarheit geben würde. Wobei wünschen Sie sich Orientierung?"
        ),
        choices=(
            choice("buy_start", "Wie ich sinnvoll starte", "buy_deadline", {"focus": "sinnvoll_starten"}),
            choice("buy_studio", "Was ich vor dem ersten Küchenstudio-Termin klären sollte", "buy_deadline", {"focus": "studio_vorbereitung"}),
            choice("buy_budget", "Wie ich Budget und Prioritäten sortiere", "buy_deadline", {"focus": "budget_prioritaeten"}),
            choice("buy_unsure", "Ich bin noch bei mehreren Punkten unsicher", "buy_deadline", {"focus": "mehrere_unsicherheiten"}),
        ),
    ),
    "buy_deadline": FlowNode(
        id="buy_deadline",
        text="Wann möchten Sie voraussichtlich den nächsten Schritt machen?",
        choices=(
            choice("buy_soon", "In den nächsten 1-2 Wochen", "optional_note", {"deadline": "hoch"}),
            choice("buy_month", "Im nächsten Monat", "optional_note", {"deadline": "mittel"}),
            choice("buy_quarter", "In den nächsten 2-3 Monaten", "optional_note", {"deadline": "offen"}),
            choice("buy_open", "Noch offen", "optional_note", {"deadline": "offen"}),
        ),
    ),
    "offer_focus": FlowNode(
        id="offer_focus",
        text="Wobei möchten Sie bei Ihrem Angebot als Erstes Klarheit gewinnen?",
        choices=(
            choice("offer_plan", "Planung / Grundriss einordnen", "offer_stage", {"focus": "planung_grundriss"}),
            choice("offer_scope", "Inhalte / Leistungen verstehen", "offer_stage", {"focus": "leistungen_verstehen"}),
            choice("offer_price", "Preis / Vergleichbarkeit einordnen", "offer_stage", {"focus": "preis_vergleichbarkeit"}),
            choice("offer_multi", "Ich bin bei mehreren Punkten unsicher", "offer_stage", {"focus": "mehrere_punkte"}),
        ),
    ),
    "offer_stage": FlowNode(
        id="offer_stage",
        text="Wie weit sind Sie mit der Entscheidung?",
        choices=(
            choice("offer_orient", "Ich orientiere mich noch", "offer_deadline", {"decision_stage": "orientierung"}),
            choice("offer_compare", "Ich vergleiche mehrere Angebote", "offer_deadline", {"decision_stage": "vergleich"}),
            choice("offer_soon", "Ich will bald entscheiden", "offer_deadline", {"decision_stage": "bald_entscheiden"}),
            choice("offer_sign", "Ich bin kurz vor Unterschrift", "offer_deadline", {"decision_stage": "kurz_vor_unterschrift"}),
        ),
    ),
    "offer_deadline": FlowNode(
        id="offer_deadline",
        text="Bis wann brauchen Sie eine sichere Einordnung?",
        choices=(
            choice("offer_urgent", "Sehr kurzfristig (1-3 Tage)", "offer_note", {"deadline": "sehr_hoch"}),
            choice("offer_week", "In 1 Woche", "offer_note", {"deadline": "hoch"}),
            choice("offer_month", "In 2-4 Wochen", "offer_note", {"deadline": "mittel"}),
            choice("offer_open", "Noch offen", "offer_note", {"deadline": "offen"}),
        ),
    ),
    "offer_note": FlowNode(
        id="offer_note",
        text="Was ist bei Ihrem Angebot aus Ihrer Sicht noch unklar oder offen?",
        choices=(
            choice("offer_write", "Wichtigste Frage kurz notieren", "capture_note"),
            choice("offer_skip", "Ohne Zusatz weiter", SUMMARY_NODE),
        ),
    ),
    "optional_note": FlowNode(
        id="optional_note",
        text="Möchten Sie noch kurz ergänzen, was in Ihrer Situation besonders wichtig ist?",
        choices=(
            choice("note_write", "Ja, kurz beschreiben", "capture_note"),
            choice("note_skip", "Ohne Zusatz weiter", SUMMARY_NODE),
        ),
    ),
    "deadline": FlowNode(
        id="deadline",
        text="Wann steht bei Ihnen der nächste wichtige Schritt an?",
        choices=(
            choice("deadline_soon", "Sehr bald - in den nächsten 1 bis 4 Wochen", "optional_note", {"deadline": "sehr_hoch"}),
            choice("deadline_months", "In den nächsten 1 bis 3 Monaten", "optional_note", {"deadline": "hoch"}),
            choice("deadline_later", "Etwas später - in etwa 4 bis 8 Monaten", "optional_note", {"deadline": "mittel"}),
            choice("deadline_open", "Noch offen - ich möchte mich frühzeitig orientieren", "optional_note", {"deadline": "offen"}),
        ),
    ),
    "free_note": FlowNode(
        id="free_note",
        text="Schreiben Sie Ihr Anliegen kurz auf. Ich ordne es danach in den passenden nächsten Schritt ein.",
    ),
    "capture_note": FlowNode(
        id="capture_note",
        text="Schreiben Sie den Punkt gern kurz in das Eingabefeld.",
    ),
}
