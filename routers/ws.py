import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select, update, func

from database import async_session
from models import Notification
from auth import verify_token
from routers.notifications import _to_response

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(user_id, set()).add(ws)

    def disconnect(self, user_id: str, ws: WebSocket):
        conns = self._connections.get(user_id)
        if conns:
            conns.discard(ws)
            if not conns:
                del self._connections[user_id]

    async def send_to_user(self, user_id: str, message: dict):
        conns = self._connections.get(user_id)
        if not conns:
            return
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)


manager = ConnectionManager()


async def _send_unread_count(user_id: str):
    async with async_session() as db:
        result = await db.execute(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id,
                Notification.read == False,
            )
        )
        count = result.scalar() or 0
    await manager.send_to_user(user_id, {"type": "unread_count", "data": count})


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, token: str):
    user_id = verify_token(token)
    if not user_id:
        await ws.close(code=4001)
        return

    await manager.connect(user_id, ws)
    await _send_unread_count(user_id)

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type")

            if msg_type == "get_notifications":
                async with async_session() as db:
                    result = await db.execute(
                        select(Notification)
                        .where(Notification.user_id == user_id)
                        .order_by(Notification.created_at.desc())
                        .limit(50)
                    )
                    items = [_to_response(n).model_dump() for n in result.scalars().all()]
                await ws.send_json({"type": "notifications", "data": items})

            elif msg_type == "mark_read":
                nid = data.get("id")
                if not nid:
                    continue
                async with async_session() as db:
                    n = await db.get(Notification, nid)
                    if n and n.user_id == user_id:
                        n.read = True
                        await db.commit()
                await _send_unread_count(user_id)

            elif msg_type == "mark_all_read":
                async with async_session() as db:
                    await db.execute(
                        update(Notification)
                        .where(Notification.user_id == user_id, Notification.read == False)
                        .values(read=True)
                    )
                    await db.commit()
                await _send_unread_count(user_id)

    except WebSocketDisconnect:
        manager.disconnect(user_id, ws)
    except Exception:
        manager.disconnect(user_id, ws)
