from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from models import Notification


class NotificationOut(BaseModel):
    id: str
    type: str
    actorIds: list[str]
    tweetId: str | None = None
    createdAt: str
    read: bool
    preview: str = ""


def _to_response(n: Notification) -> NotificationOut:
    return NotificationOut(
        id=n.id,
        type=n.type,
        actorIds=[n.actor_id],
        tweetId=n.tweet_id,
        createdAt=n.created_at.isoformat() if n.created_at else "",
        read=n.read,
        preview=n.preview,
    )


async def create_notification(
    db: AsyncSession,
    user_id: str,
    type: str,
    actor_id: str,
    tweet_id: str | None = None,
    preview: str = "",
) -> dict | None:
    if user_id == actor_id:
        return None
    n = Notification(
        user_id=user_id,
        type=type,
        actor_id=actor_id,
        tweet_id=tweet_id,
        preview=preview,
    )
    db.add(n)
    await db.flush()
    await db.refresh(n)
    return _to_response(n).model_dump()
