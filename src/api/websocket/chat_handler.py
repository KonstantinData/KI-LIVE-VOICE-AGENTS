"""WebSocket chat endpoint for tenant-scoped widget conversations."""

import json
from datetime import datetime, timezone

import structlog
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

from src.agents.lisa.agent import LisaAgent
from src.api.config import get_settings
from src.api.services.kea_text_flow import KeaTextFlow
from src.api.services.kea_text_flow_nodes import FlowChoice, FlowResponse
from src.api.websocket.manager import manager
from src.db.database import AsyncSessionLocal
from src.db.models.conversation import Conversation
from src.db.models.studio import Studio
from src.tenants.registry import agent_display_name, get_tenant_profile_for_studio

log = structlog.get_logger()
settings = get_settings()


def _origin_allowed(origin: str | None) -> bool:
    """Checks WebSocket Origin against configured CORS origins."""
    if origin is None:
        return settings.app_env != "production"
    return origin in settings.cors_origins


def _choice_payload(choice: FlowChoice) -> dict[str, str]:
    """Serializes one KEA text-flow choice for the widget."""
    return {"id": choice.id, "label": choice.label}


async def _send_flow_response(websocket: WebSocket, response: FlowResponse) -> None:
    """Sends one KEA text-flow response to the widget."""
    await websocket.send_json({
        "type": "message",
        "role": "assistant",
        "content": response.content,
        "choices": [_choice_payload(choice) for choice in response.choices],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def _public_agent_name(studio_slug: str) -> str:
    """Returns the public assistant name used in user-facing error messages."""
    return agent_display_name(studio_slug)


async def handle_chat(
    websocket: WebSocket,
    studio_slug: str,
    visitor_id: str,
    consent_given: bool = False,
) -> None:
    """
    WebSocket-Handler für den Chat-Endpoint.

    /ws/chat?studio={slug}&visitor={visitor_id}

    1. Studio anhand slug laden → Verbindung schließen wenn nicht gefunden
    2. Konversation finden oder erstellen (via visitor_id)
    3. Agent initialisieren
    4. Bei jeder Nachricht: agent.process_message() → DB commit → Antwort senden
    5. Bei Disconnect: finalize_conversation() → DB commit → Verbindung trennen
    """
    origin = websocket.headers.get("origin")
    if not _origin_allowed(origin):
        await websocket.close(code=4403)
        return
    if not consent_given:
        await websocket.close(code=4401)
        return
    if len(visitor_id) > 255 or len(studio_slug) > 100:
        await websocket.close(code=4400)
        return

    connection_key = f"{studio_slug}:{visitor_id}"
    await manager.connect(websocket, connection_key)

    async with AsyncSessionLocal() as session:
        # ── Studio laden ──────────────────────────────────────────────────────
        result = await session.execute(
            select(Studio).where(Studio.slug == studio_slug)
        )
        studio = result.scalar_one_or_none()

        if studio is None:
            await websocket.send_json({
                "type": "error",
                "message": f"Studio '{studio_slug}' nicht gefunden",
            })
            await websocket.close(code=4004)
            manager.disconnect(connection_key)
            return

        if not studio.is_active:
            await websocket.send_json({
                "type": "error",
                "message": "Dieses Studio ist derzeit nicht aktiv.",
            })
            await websocket.close(code=4003)
            manager.disconnect(connection_key)
            return

        profile = get_tenant_profile_for_studio(studio.slug)
        if profile is not None and studio.slug != "mein-kuechenexperte":
            await websocket.send_json({
                "type": "error",
                "message": "Der Textchat ist für diesen Tenant noch nicht konfiguriert.",
            })
            await websocket.close(code=4003)
            manager.disconnect(connection_key)
            return

        # ── Konversation finden oder erstellen ────────────────────────────────
        conv_result = await session.execute(
            select(Conversation)
            .where(Conversation.studio_id == studio.id)
            .where(Conversation.visitor_id == visitor_id)
            .where(Conversation.status == "active")
        )
        conversation = conv_result.scalar_one_or_none()

        if conversation is None:
            conversation = Conversation(
                studio_id=studio.id,
                visitor_id=visitor_id,
                channel="widget",
                status="active",
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)

        log.info(
            "ws.chat_started",
            studio=studio_slug,
            visitor=visitor_id,
            conversation_id=str(conversation.id),
        )
        await websocket.send_json({
            "type": "session",
            "conversation_id": str(conversation.id),
            "visitor_id": visitor_id,
        })

        # ── Agent initialisieren ──────────────────────────────────────────────
        agent = LisaAgent(session=session)
        public_agent_name = _public_agent_name(studio.slug)
        kea_flow = KeaTextFlow(session=session) if studio.slug == "mein-kuechenexperte" else None

        if kea_flow is not None:
            flow_response = await kea_flow.start(conversation)
            await session.commit()
            await _send_flow_response(websocket, flow_response)

        # ── Nachrichten-Loop ──────────────────────────────────────────────────
        try:
            while True:
                data = await websocket.receive_text()

                try:
                    payload = json.loads(data)
                    message_text = str(payload.get("message") or "")
                    action_id = payload.get("action_id")
                    action_label = payload.get("label")
                except json.JSONDecodeError:
                    message_text = data
                    action_id = None
                    action_label = None

                if not message_text.strip() and not action_id:
                    continue
                action_label_text = str(action_label or "")
                if (
                    len(message_text) > settings.max_chat_message_chars
                    or len(action_label_text) > settings.max_chat_message_chars
                ):
                    await websocket.send_json({
                        "type": "error",
                        "message": "Die Nachricht ist zu lang.",
                    })
                    continue

                log.info(
                    "ws.message_received",
                    visitor=visitor_id,
                    text_len=len(message_text),
                )

                # Typing-Indicator senden
                await websocket.send_json({"type": "typing", "role": "assistant"})

                try:
                    # Agent verarbeitet Nachricht (7-Schritte-Loop)
                    if kea_flow is not None:
                        flow_response = await kea_flow.handle(
                            conversation,
                            message_text=message_text,
                            action_id=str(action_id) if action_id else None,
                            action_label=action_label_text if action_label else None,
                        )
                    else:
                        response_text = await agent.process_message(
                            user_message=message_text,
                            conversation=conversation,
                            studio=studio,
                        )

                    # Alle DB-Änderungen dieser Nachricht committen
                    # (Nachrichten, Lead-Updates, Conversation.lead_id)
                    await session.commit()

                    # Antwort an Client senden
                    if kea_flow is not None:
                        await _send_flow_response(websocket, flow_response)
                    else:
                        await websocket.send_json({
                            "type": "message",
                            "role": "assistant",
                            "content": response_text,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                except Exception as e:
                    await session.rollback()
                    log.error("ws.message_error", visitor=visitor_id, error=str(e))
                    await websocket.send_json({
                        "type": "error",
                        "message": (
                            f"{public_agent_name} ist gerade technisch nicht erreichbar. "
                            "Bitte versuchen Sie es in einem Moment erneut."
                        ),
                    })

        except WebSocketDisconnect:
            log.info("ws.disconnected", visitor=visitor_id)

            # Gesprächszusammenfassung generieren + Konversation schließen
            try:
                if kea_flow is not None:
                    conversation.status = "closed"
                    conversation.summary = (
                        conversation.summary
                        or "KEA Textchat: geführte Projekteinordnung im Widget."
                    )
                    log.info(
                        "kea.finalized",
                        visitor=visitor_id,
                        conversation_id=str(conversation.id),
                    )
                else:
                    await agent.finalize_conversation(conversation, studio)
                await session.commit()
                log.info(
                    "ws.finalized",
                    visitor=visitor_id,
                    conversation_id=str(conversation.id),
                )
            except Exception as e:
                log.error("ws.finalize_error", visitor=visitor_id, error=str(e))

        except Exception as e:
            log.error("ws.error", visitor=visitor_id, error=str(e))

        finally:
            manager.disconnect(connection_key)
