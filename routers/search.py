from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, Tweet
from schemas import UserResponse, TweetResponse
from auth import get_current_user
from routers.users import _user_to_response
from routers.tweets import _tweet_to_response

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def search(
    q: str = Query(..., min_length=1),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pattern = f"%{q}%"

    users_result = await db.execute(
        select(User).where(
            or_(User.name.ilike(pattern), User.username.ilike(pattern))
        ).limit(20)
    )
    users = users_result.scalars().all()
    users_resp = [await _user_to_response(u, user_id, db) for u in users]

    tweets_result = await db.execute(
        select(Tweet).where(Tweet.content.ilike(pattern)).order_by(Tweet.created_at.desc()).limit(20)
    )
    tweets = tweets_result.scalars().all()
    tweets_resp = [await _tweet_to_response(t, user_id, db) for t in tweets]

    return {"users": users_resp, "tweets": tweets_resp}
