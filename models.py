import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, Text, Integer, JSON, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    avatar: Mapped[str] = mapped_column(String(500), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    banner: Mapped[str] = mapped_column(String(500), default="")
    location: Mapped[str] = mapped_column(String(100), default="")
    website: Mapped[str] = mapped_column(String(500), default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    following: Mapped[int] = mapped_column(default=0)
    followers: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Tweet(Base):
    __tablename__ = "tweets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    author_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    media: Mapped[dict] = mapped_column(JSON, default=list)
    reply_to_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    reply_count: Mapped[int] = mapped_column(Integer, default=0)
    retweet_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    bookmark_count: Mapped[int] = mapped_column(Integer, default=0)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    todos: Mapped[dict] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Like(Base):
    __tablename__ = "likes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    tweet_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    __table_args__ = (UniqueConstraint("user_id", "tweet_id", name="uq_like"),)


class Retweet(Base):
    __tablename__ = "retweets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    tweet_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    __table_args__ = (UniqueConstraint("user_id", "tweet_id", name="uq_retweet"),)


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    tweet_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    __table_args__ = (UniqueConstraint("user_id", "tweet_id", name="uq_bookmark"),)


class Follow(Base):
    __tablename__ = "follows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    follower_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    following_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    __table_args__ = (UniqueConstraint("follower_id", "following_id", name="uq_follow"),)
