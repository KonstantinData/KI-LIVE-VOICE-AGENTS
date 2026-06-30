"""WebSocket Connection Manager: Verwaltet alle aktiven Verbindungen."""


import structlog
from fastapi import WebSocket

log = structlog.get_logger()


class ConnectionManager:
    """
    Verwaltet alle aktiven WebSocket-Verbindungen.

    Ermöglicht es, Nachrichten an einzelne oder alle Verbindungen zu senden.
    """

    def __init__(self) -> None:
        # visitor_id → WebSocket
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, visitor_id: str) -> None:
        """Akzeptiert eine neue WebSocket-Verbindung."""
        await websocket.accept()
        self._connections[visitor_id] = websocket
        log.info("ws.connected", visitor_id=visitor_id, total=len(self._connections))

    def disconnect(self, visitor_id: str) -> None:
        """Entfernt eine Verbindung aus dem Manager."""
        self._connections.pop(visitor_id, None)
        log.info("ws.disconnected", visitor_id=visitor_id, total=len(self._connections))

    async def send_text(self, visitor_id: str, message: str) -> None:
        """Sendet eine Text-Nachricht an einen spezifischen Visitor."""
        websocket = self._connections.get(visitor_id)
        if websocket:
            await websocket.send_text(message)

    async def send_json(self, visitor_id: str, data: dict) -> None:
        """Sendet JSON-Daten an einen spezifischen Visitor."""
        websocket = self._connections.get(visitor_id)
        if websocket:
            await websocket.send_json(data)

    async def broadcast(self, message: str) -> None:
        """Sendet eine Nachricht an alle verbundenen Clients."""
        for websocket in self._connections.values():
            await websocket.send_text(message)

    @property
    def active_connections(self) -> int:
        """Gibt die Anzahl aktiver Verbindungen zurück."""
        return len(self._connections)


# Globale Instanz (Singleton)
manager = ConnectionManager()
