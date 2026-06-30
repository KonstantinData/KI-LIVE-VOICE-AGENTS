"""WebSocket Chat-Endpoint: Empfängt Nachrichten und leitet sie an Lisa weiter."""

import json
from datetime import datetime, timezone

import structlog
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

from src.agents.lisa.agent import LisaAgent
from src.api.config import get_settings
from src.api.websocket.manager import manager
from src.db.database import AsyncSessionLocal
from src.db.models.conversation import Conversation
from src.db.models.studio import Studio

log = structlog.get_logger()
settings = get_settings()


def _origin_allowed(origin: str | None) -> bool:
    """Checks WebSocket Origin against configured CORS origins."""
    if origin is None:
        return settings.app_env != "production"
    return origin in settings.cors_origins


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
    3. LisaAgent initialisieren
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

        # ── Agent initialisieren ──────────────────────────────────────────────
        agent = LisaAgent(session=session)

        # ── Nachrichten-Loop ──────────────────────────────────────────────────
        try:
            while True:
                data = await websocket.receive_text()

                try:
                    payload = json.loads(data)
                    message_text = payload.get("message", data)
                except json.JSONDecodeError:
                    message_text = data

                if not message_text.strip():
                    continue
                if len(message_text) > settings.max_chat_message_chars:
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
                    response_text = await agent.process_message(
                        user_message=message_text,
                        conversation=conversation,
                        studio=studio,
                    )

                    # Alle DB-Änderungen dieser Nachricht committen
                    # (Nachrichten, Lead-Updates, Conversation.lead_id)
                    await session.commit()

                    # Antwort an Client senden
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
                            "Lisa ist gerade technisch nicht erreichbar. "
                            "Bitte versuchen Sie es in einem Moment erneut."
                        ),
                    })

        except WebSocketDisconnect:
            log.info("ws.disconnected", visitor=visitor_id)

            # Gesprächszusammenfassung generieren + Konversation schließen
            try:
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
