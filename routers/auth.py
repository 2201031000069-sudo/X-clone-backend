from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from database import get_db
from models import User, PasswordResetToken
from schemas import LoginRequest, SignupRequest, GoogleAuthRequest, ForgotPasswordRequest, ResetPasswordRequest, TokenResponse, UserResponse
from auth import hash_password, verify_password, create_access_token, generate_reset_token

import os
import hashlib
from datetime import datetime, timezone

from ratelimit import limiter

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_CLIENT_ID = os.getenv("VITE_GOOGLE_CLIENT_ID", "")


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
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id)
    return TokenResponse(user=_user_to_response(user), token=token)


@router.post("/signup", response_model=TokenResponse, status_code=201)
@limiter.limit("5/minute")
async def signup(request: Request, body: SignupRequest, db: AsyncSession = Depends(get_db)):
    existing_email = await db.execute(select(User).where(User.email == body.email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    existing_username = await db.execute(select(User).where(User.username == body.username))
    if existing_username.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already taken")

    user = User(
        name=body.name,
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        avatar=f"https://api.dicebear.com/9.x/avataaars/svg?seed={body.username}",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(user=_user_to_response(user), token=token)


@router.post("/google", response_model=TokenResponse)
async def google_auth(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    try:
        info = id_token.verify_oauth2_token(body.id_token, google_requests.Request(), GOOGLE_CLIENT_ID)
        google_id = info["sub"]
        email = info.get("email", "")
        name = info.get("name", "User")
        picture = info.get("picture", "")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    result = await db.execute(select(User).where(User.google_id == google_id))
    user = result.scalar_one_or_none()

    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.google_id = google_id
            await db.commit()
            await db.refresh(user)
        else:
            username_base = email.split("@")[0] if email else f"user_{google_id[:8]}"
            username = username_base
            counter = 1
            while True:
                exists = await db.execute(select(User).where(User.username == username))
                if not exists.scalar_one_or_none():
                    break
                username = f"{username_base}{counter}"
                counter += 1

            user = User(
                name=name,
                username=username,
                email=email,
                google_id=google_id,
                avatar=picture,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(user=_user_to_response(user), token=token)


@router.post("/forgot-password", status_code=200)
@limiter.limit("3/minute")
async def forgot_password(request: Request, body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        return {"message": "If that email exists, we sent a reset link."}

    token, token_hash, expires_at = generate_reset_token()
    reset = PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
    db.add(reset)
    await db.commit()

    from mailer import send_reset_email
    await send_reset_email(user.email, token)

    return {"message": "If that email exists, we sent a reset link."}


@router.post("/reset-password", status_code=200)
@limiter.limit("5/minute")
async def reset_password(request: Request, body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()

    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used == False,
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
        )
    )
    reset = result.scalar_one_or_none()

    if not reset:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    result = await db.execute(select(User).where(User.id == reset.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.hashed_password = hash_password(body.password)
    reset.used = True
    await db.commit()

    return {"message": "Password updated successfully"}
