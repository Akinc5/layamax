"""
WebSocket connection manager for real‑time dashboard updates.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Set

from fastapi import WebSocket


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts messages."""

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(ws)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Send a JSON message to every connected client."""
        payload = json.dumps(message, default=str)
        dead: List[WebSocket] = []
        async with self._lock:
            targets = list(self._connections)
        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.discard(ws)

    async def send_personal(self, ws: WebSocket, message: Dict[str, Any]) -> None:
        payload = json.dumps(message, default=str)
        try:
            await ws.send_text(payload)
        except Exception:
            await self.disconnect(ws)

    @property
    def active_count(self) -> int:
        return len(self._connections)


# Singleton
ws_manager = ConnectionManager()
