from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, Tweet, Follow
from schemas import UserResponse, TweetResponse, UpdateProfileRequest
from auth import get_current_user
from routers.tweets import _tweet_to_response

router = APIRouter(prefix="/users", tags=["users"])


async def _user_to_response(u: User, current_user_id: str | None = None, db: AsyncSession | None = None) -> UserResponse:
    following = u.following
    followers = u.followers
    is_following = False
    if current_user_id and db:
        result = await db.execute(
            select(Follow).where(
                Follow.follower_id == current_user_id,
                Follow.following_id == u.id,
            )
        )
        is_following = result.scalar_one_or_none() is not None
    return UserResponse(
        id=u.id,
        name=u.name,
        username=u.username,
        avatar=u.avatar,
        bio=u.bio,
        banner=u.banner,
        location=u.location,
        website=u.website,
        joinedAt=u.created_at.isoformat() if u.created_at else "",
        following=following,
        followers=followers,
        verified=u.verified,
        is_following=is_following,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await _user_to_response(user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    body: UpdateProfileRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return await _user_to_response(user)


@router.get("/suggestions", response_model=list[UserResponse])
async def get_suggestions(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.id != user_id).order_by(func.random()).limit(3)
    )
    users = result.scalars().all()
    return [await _user_to_response(u, user_id, db) for u in users]


@router.get("/{username}", response_model=UserResponse)
async def get_user(
    username: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await _user_to_response(user, user_id, db)


@router.get("/{username}/tweets", response_model=list[TweetResponse])
async def get_user_tweets(
    username: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tweets_result = await db.execute(
        select(Tweet)
        .where(Tweet.author_id == user.id, Tweet.reply_to_id.is_(None))
        .order_by(Tweet.created_at.desc())
    )
    tweets = tweets_result.scalars().all()
    return [await _tweet_to_response(t, user_id, db) for t in tweets]


@router.post("/{username}/follow", response_model=UserResponse)
async def follow_user(
    username: str,
    current_user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == username))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == current_user_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    existing = await db.execute(
        select(Follow).where(
            Follow.follower_id == current_user_id,
            Follow.following_id == target.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already following this user")

    follow = Follow(follower_id=current_user_id, following_id=target.id)
    db.add(follow)
    target.followers += 1

    source_result = await db.execute(select(User).where(User.id == current_user_id))
    source = source_result.scalar_one_or_none()
    if source:
        source.following += 1

    await db.commit()
    await db.refresh(target)
    return await _user_to_response(target, current_user_id, db)


@router.post("/{username}/unfollow", response_model=UserResponse)
async def unfollow_user(
    username: str,
    current_user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == username))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    existing = await db.execute(
        select(Follow).where(
            Follow.follower_id == current_user_id,
            Follow.following_id == target.id,
        )
    )
    follow = existing.scalar_one_or_none()
    if not follow:
        raise HTTPException(status_code=409, detail="Not following this user")

    await db.delete(follow)
    target.followers -= 1

    source_result = await db.execute(select(User).where(User.id == current_user_id))
    source = source_result.scalar_one_or_none()
    if source:
        source.following -= 1

    await db.commit()
    await db.refresh(target)
    return await _user_to_response(target, current_user_id, db)
