from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Conversation, Message, User
from auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/conversations", tags=["messages"])


class MessageResponse(BaseModel):
    id: str
    senderId: str
    text: str
    createdAt: str

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: str
    participantId: str
    unread: int
    messages: list[MessageResponse]

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    text: str


class StartConversationRequest(BaseModel):
    participant_id: str


async def _message_to_response(m: Message) -> MessageResponse:
    return MessageResponse(
        id=m.id,
        senderId=m.sender_id,
        text=m.text,
        createdAt=m.created_at.isoformat() if m.created_at else "",
    )


def _conversation_id(a: str, b: str) -> str:
    return "|".join(sorted([a, b]))


@router.get("", response_model=list[ConversationResponse])
async def get_conversations(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            or_(Conversation.participant_a == user_id, Conversation.participant_b == user_id)
        ).order_by(Conversation.last_message_at.desc())
    )
    conversations = result.scalars().all()
    responses = []
    for c in conversations:
        other_id = c.participant_b if c.participant_a == user_id else c.participant_a
        msgs_result = await db.execute(
            select(Message).where(Message.conversation_id == c.id).order_by(Message.created_at.desc()).limit(50)
        )
        msgs = list(reversed(msgs_result.scalars().all()))
        unread = sum(1 for m in msgs if not m.read and m.sender_id != user_id)
        responses.append(ConversationResponse(
            id=c.id,
            participantId=other_id,
            unread=unread,
            messages=[await _message_to_response(m) for m in msgs],
        ))
    return responses


@router.post("", response_model=ConversationResponse, status_code=201)
async def start_conversation(
    body: StartConversationRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.participant_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot start conversation with yourself")

    a, b = sorted([user_id, body.participant_id])
    result = await db.execute(
        select(Conversation).where(
            Conversation.participant_a == a,
            Conversation.participant_b == b,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        msgs_result = await db.execute(
            select(Message).where(Message.conversation_id == existing.id).order_by(Message.created_at.desc()).limit(50)
        )
        msgs = list(reversed(msgs_result.scalars().all()))
        return ConversationResponse(
            id=existing.id,
            participantId=body.participant_id,
            unread=0,
            messages=[await _message_to_response(m) for m in msgs],
        )

    conversation = Conversation(participant_a=a, participant_b=b)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return ConversationResponse(
        id=conversation.id,
        participantId=body.participant_id,
        unread=0,
        messages=[],
    )


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    conversation_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if c.participant_a != user_id and c.participant_b != user_id:
        raise HTTPException(status_code=403, detail="Not a participant")

    msgs_result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc())
    )
    msgs = msgs_result.scalars().all()

    await db.execute(
        update(Message).where(
            Message.conversation_id == conversation_id,
            Message.sender_id != user_id,
            Message.read == False,
        ).values(read=True)
    )
    await db.commit()

    return [await _message_to_response(m) for m in msgs]


@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def send_message(
    conversation_id: str,
    body: SendMessageRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if c.participant_a != user_id and c.participant_b != user_id:
        raise HTTPException(status_code=403, detail="Not a participant")

    msg = Message(
        conversation_id=conversation_id,
        sender_id=user_id,
        text=body.text,
    )
    db.add(msg)
    c.last_message_at = func.now()
    await db.commit()
    await db.refresh(msg)
    return await _message_to_response(msg)
