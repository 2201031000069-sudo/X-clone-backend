from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, Tweet, Like, Retweet, Bookmark, Follow
from schemas import CreateTweetRequest, TweetResponse, UserResponse, TodoItem
from auth import get_current_user

router = APIRouter(prefix="/tweets", tags=["tweets"])


def _user_to_response(u: User) -> UserResponse:
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
        following=u.following,
        followers=u.followers,
        verified=u.verified,
        is_following=False,
    )


async def _tweet_to_response(t: Tweet, current_user_id: str, db: AsyncSession) -> TweetResponse:
    liked = bool(
        (await db.execute(select(Like).where(Like.user_id == current_user_id, Like.tweet_id == t.id))).scalar_one_or_none()
    )
    retweeted = bool(
        (await db.execute(select(Retweet).where(Retweet.user_id == current_user_id, Retweet.tweet_id == t.id))).scalar_one_or_none()
    )
    bookmarked = bool(
        (await db.execute(select(Bookmark).where(Bookmark.user_id == current_user_id, Bookmark.tweet_id == t.id))).scalar_one_or_none()
    )

    author_result = await db.execute(select(User).where(User.id == t.author_id))
    author = author_result.scalar_one_or_none()

    return TweetResponse(
        id=t.id,
        authorId=t.author_id,
        author=_user_to_response(author) if author else UserResponse(id="", name="Unknown", username="unknown", avatar="", bio="", banner="", location="", website="", joinedAt="", following=0, followers=0, verified=False),
        content=t.content,
        createdAt=t.created_at.isoformat() if t.created_at else "",
        replies=t.reply_count,
        retweets=t.retweet_count,
        likes=t.like_count,
        bookmarks=t.bookmark_count,
        liked=liked,
        retweeted=retweeted,
        bookmarked=bookmarked,
        media=t.media if isinstance(t.media, list) else [],
        replyToId=t.reply_to_id,
        location=t.location,
        scheduledAt=t.scheduled_at.isoformat() if t.scheduled_at else None,
        todos=t.todos if isinstance(t.todos, list) else [],
    )


@router.get("", response_model=list[TweetResponse])
async def get_timeline(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Tweet)
        .where(Tweet.reply_to_id.is_(None), Tweet.archived == False)
        .order_by(Tweet.created_at.desc())
        .limit(50)
    )
    tweets = result.scalars().all()
    return [await _tweet_to_response(t, user_id, db) for t in tweets]


@router.get("/following", response_model=list[TweetResponse])
async def get_following_timeline(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Tweet).join(Follow, Follow.following_id == Tweet.author_id)
        .where(Follow.follower_id == user_id, Tweet.reply_to_id.is_(None), Tweet.archived == False)
        .order_by(Tweet.created_at.desc())
        .limit(50)
    )
    return [await _tweet_to_response(t, user_id, db) for t in result.scalars().all()]


@router.post("", response_model=TweetResponse, status_code=201)
async def create_tweet(
    body: CreateTweetRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.reply_to_id:
        parent = await db.execute(select(Tweet).where(Tweet.id == body.reply_to_id))
        parent_tweet = parent.scalar_one_or_none()
        if not parent_tweet:
            raise HTTPException(status_code=404, detail="Parent tweet not found")

    scheduled = None
    if body.scheduled_at:
        scheduled = datetime.fromisoformat(body.scheduled_at)

    tweet = Tweet(
        author_id=user_id,
        content=body.content,
        reply_to_id=body.reply_to_id,
        media=body.media,
        location=body.location,
        scheduled_at=scheduled,
        todos=[t.model_dump() for t in body.todos],
    )
    db.add(tweet)

    if body.reply_to_id:
        parent_tweet.reply_count += 1

    await db.commit()
    await db.refresh(tweet)
    return await _tweet_to_response(tweet, user_id, db)


@router.get("/bookmarks", response_model=list[TweetResponse])
async def get_bookmarks(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Tweet).join(Bookmark, Bookmark.tweet_id == Tweet.id).where(Bookmark.user_id == user_id, Tweet.archived == False).order_by(Tweet.created_at.desc())
    )
    return [await _tweet_to_response(t, user_id, db) for t in result.scalars().all()]


@router.get("/{tweet_id}", response_model=TweetResponse)
async def get_tweet(
    tweet_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tweet).where(Tweet.id == tweet_id))
    tweet = result.scalar_one_or_none()
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")
    return await _tweet_to_response(tweet, user_id, db)


@router.get("/{tweet_id}/replies", response_model=list[TweetResponse])
async def get_replies(
    tweet_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Tweet)
        .where(Tweet.reply_to_id == tweet_id, Tweet.archived == False)
        .order_by(Tweet.created_at.asc())
    )
    tweets = result.scalars().all()
    return [await _tweet_to_response(t, user_id, db) for t in tweets]


async def _toggle_interaction(
    tweet_id: str,
    user_id: str,
    db: AsyncSession,
    model: type[Like | Retweet | Bookmark],
    count_field: str,
) -> TweetResponse:
    result = await db.execute(select(Tweet).where(Tweet.id == tweet_id))
    tweet = result.scalar_one_or_none()
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")

    existing = await db.execute(
        select(model).where(model.user_id == user_id, model.tweet_id == tweet_id)
    )
    interaction = existing.scalar_one_or_none()

    if interaction:
        await db.delete(interaction)
        setattr(tweet, count_field, getattr(tweet, count_field) - 1)
        await db.commit()
    else:
        db.add(model(user_id=user_id, tweet_id=tweet_id))
        setattr(tweet, count_field, getattr(tweet, count_field) + 1)
        await db.commit()

    await db.refresh(tweet)
    return await _tweet_to_response(tweet, user_id, db)


@router.post("/{tweet_id}/archive", status_code=200)
async def archive_tweet(
    tweet_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tweet).where(Tweet.id == tweet_id))
    tweet = result.scalar_one_or_none()
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")
    if tweet.author_id != user_id:
        raise HTTPException(status_code=403, detail="Not your tweet")
    tweet.archived = True
    await db.commit()
    return {"ok": True}


@router.post("/{tweet_id}/like", response_model=TweetResponse)
async def toggle_like(
    tweet_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _toggle_interaction(tweet_id, user_id, db, Like, "like_count")


@router.post("/{tweet_id}/retweet", response_model=TweetResponse)
async def toggle_retweet(
    tweet_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _toggle_interaction(tweet_id, user_id, db, Retweet, "retweet_count")


@router.post("/{tweet_id}/bookmark", response_model=TweetResponse)
async def toggle_bookmark(
    tweet_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _toggle_interaction(tweet_id, user_id, db, Bookmark, "bookmark_count")
