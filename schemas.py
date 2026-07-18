from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, Field
import re


class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    username: str = Field(..., min_length=3, max_length=20)
    email: str
    password: str = Field(..., min_length=8)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username must contain only letters, numbers, and underscores")
        return v


class GoogleAuthRequest(BaseModel):
    id_token: str


class UserResponse(BaseModel):
    id: str
    name: str
    username: str
    avatar: str
    bio: str
    banner: str
    location: str
    website: str
    joinedAt: str
    following: int
    followers: int
    verified: bool
    is_following: bool = False

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    user: UserResponse
    token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str = Field(..., min_length=8)


class TodoItem(BaseModel):
    text: str
    done: bool = False


class CreateTweetRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=280)
    reply_to_id: Optional[str] = None
    media: list[str] = Field(default_factory=list)
    location: Optional[str] = None
    scheduled_at: Optional[str] = None
    todos: list[TodoItem] = Field(default_factory=list)


class TweetResponse(BaseModel):
    id: str
    authorId: str
    author: UserResponse
    content: str
    createdAt: str
    replies: int
    retweets: int
    likes: int
    bookmarks: int
    liked: bool
    retweeted: bool
    bookmarked: bool
    media: list[str]
    replyToId: Optional[str] = None
    location: Optional[str] = None
    scheduledAt: Optional[str] = None
    todos: list[TodoItem] = Field(default_factory=list)


class TrendResponse(BaseModel):
    category: str
    tag: str
    posts: str


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    avatar: Optional[str] = None
    banner: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str
