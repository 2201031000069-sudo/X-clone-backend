"""
Seed the database with mock users and tweets so you can test the frontend.

Usage:
  python seed.py

This creates the accounts from frontend mock-data.ts with a default password "password123".
Login with email: you@example.com / password: password123
"""
import asyncio
from datetime import datetime, timezone, timedelta

from database import init_db, async_session, engine, Base
from models import User, Tweet
from auth import hash_password


MOCK_USERS = [
    {"id": "u1", "name": "You", "username": "you", "email": "you@example.com", "bio": "Building things on the internet.", "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=you", "banner": "https://images.unsplash.com/photo-1519681393784-d120267933ba?w=1200", "location": "Everywhere", "website": "https://example.com", "verified": False, "following": 128, "followers": 342},
    {"id": "2293588e-05fa-450d-b297-7a4e856fe6df", "name": "Yash", "username": "yash", "email": "yash@example.com", "bio": "", "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=yash", "verified": False, "following": 0, "followers": 0},
    {"id": "u2", "name": "Ada Lovelace", "username": "ada", "email": "ada@example.com", "bio": "First programmer. Poet of science.", "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=ada", "verified": True, "following": 89, "followers": 12400},
    {"id": "u3", "name": "Grace Hopper", "username": "grace", "email": "grace@example.com", "bio": "Compiler pioneer. It's easier to ask forgiveness than permission.", "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=grace", "verified": True, "following": 210, "followers": 9800},
    {"id": "u4", "name": "Linus T.", "username": "linus", "email": "linus@example.com", "bio": "Talk is cheap. Show me the code.", "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=linus", "verified": True, "following": 42, "followers": 88},
    {"id": "u5", "name": "Sara Dev", "username": "saradev", "email": "sara@example.com", "bio": "Frontend @ Chirp. Design systems nerd.", "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=sara", "verified": False, "following": 512, "followers": 1830},
    {"id": "u6", "name": "Marcus", "username": "marcusai", "email": "marcus@example.com", "bio": "AI research & bad jokes.", "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=marcus", "verified": False, "following": 300, "followers": 5200},
    {"id": "u7", "name": "Priya S.", "username": "priya", "email": "priya@example.com", "bio": "Product designer. Coffee snob.", "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=priya", "verified": False, "following": 190, "followers": 2400},
    {"id": "u8", "name": "Chirp News", "username": "chirpnews", "email": "news@example.com", "bio": "Breaking. Curated by humans.", "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=news", "verified": True, "following": 12, "followers": 240000},
]

now = datetime.now(timezone.utc)

MOCK_TWEETS = [
    {"id": "t1", "author_id": "u4", "content": "The best code is no code at all. Every new line of code you willingly bring into the world is code that has to be debugged.", "created_at": now - timedelta(minutes=12), "likes": 2100, "retweets": 340, "replies": 82, "bookmarks": 190},
    {"id": "t2", "author_id": "u2", "content": "That brain of mine is something more than merely mortal, as time will show. ✨", "created_at": now - timedelta(minutes=45), "likes": 512, "retweets": 88, "replies": 12, "bookmarks": 40},
    {"id": "t3", "author_id": "u8", "content": "BREAKING: Chirp opens sign-ups globally today. Millions expected in the first 24 hours.", "created_at": now - timedelta(hours=2), "likes": 8900, "retweets": 1400, "replies": 210, "bookmarks": 320, "media": ["https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=900"]},
    {"id": "t4", "author_id": "u5", "content": "Rewriting our design tokens today. Semantic > literal, every single time. Your future self will thank you.", "created_at": now - timedelta(hours=3), "likes": 410, "retweets": 55, "replies": 22, "bookmarks": 80},
    {"id": "t5", "author_id": "u3", "content": "A ship in port is safe, but that's not what ships are built for. Sail out. Do new things.", "created_at": now - timedelta(hours=5), "likes": 1900, "retweets": 260, "replies": 40, "bookmarks": 210},
    {"id": "t6", "author_id": "u6", "content": "hot take: most 'AI agents' are just a for-loop with a chat api and a hope.", "created_at": now - timedelta(hours=8), "likes": 5400, "retweets": 900, "replies": 320, "bookmarks": 190},
    {"id": "t7", "author_id": "u7", "content": "Spent the morning at a small kaapi shop redesigning our onboarding on paper. Nothing beats pen + coffee.", "created_at": now - timedelta(hours=11), "likes": 190, "retweets": 12, "replies": 8, "bookmarks": 15, "media": ["https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=900"]},
    {"id": "t8", "author_id": "u2", "content": "The engine can do whatever we know how to order it to perform.", "created_at": now - timedelta(hours=22), "likes": 220, "retweets": 30, "replies": 5, "bookmarks": 12},
    {"id": "t9", "author_id": "u4", "content": "git commit -m 'i am inevitable'", "created_at": now - timedelta(days=1), "likes": 3200, "retweets": 400, "replies": 60, "bookmarks": 40},
    {"id": "t10", "author_id": "u5", "content": "the trick to shipping is: keep going.", "created_at": now - timedelta(days=2), "likes": 180, "retweets": 22, "replies": 4, "bookmarks": 8},
    {"id": "t11", "author_id": "u8", "content": "New rocket launch scheduled for tonight. Live coverage begins at 21:00 UTC.", "created_at": now - timedelta(days=3), "likes": 4200, "retweets": 500, "replies": 90, "bookmarks": 60},
    {"id": "t12", "author_id": "u6", "content": "reading old papers is a cheat code.", "created_at": now - timedelta(days=4), "likes": 160, "retweets": 18, "replies": 2, "bookmarks": 5},
]

DEFAULT_PASSWORD = "password1235"


async def seed():
    await init_db()

    async with async_session() as session:
        # Users
        for u in MOCK_USERS:
            user = User(
                id=u["id"],
                name=u["name"],
                username=u["username"],
                email=u["email"],
                hashed_password=hash_password(DEFAULT_PASSWORD),
                bio=u.get("bio", ""),
                avatar=u.get("avatar", ""),
                banner=u.get("banner", ""),
                location=u.get("location", ""),
                website=u.get("website", ""),
                verified=u.get("verified", False),
                following=u.get("following", 0),
                followers=u.get("followers", 0),
            )
            session.add(user)

        await session.flush()

        # Tweets
        for t in MOCK_TWEETS:
            tweet = Tweet(
                id=t["id"],
                author_id=t["author_id"],
                content=t["content"],
                media=t.get("media", []),
                reply_to_id=t.get("reply_to_id"),
                like_count=t["likes"],
                retweet_count=t["retweets"],
                reply_count=t["replies"],
                bookmark_count=t["bookmarks"],
                created_at=t["created_at"],
            )
            session.add(tweet)

        await session.commit()

    print("Done! DB seeded with 8 users and 12 tweets.")
    print(f'Login: you@example.com / {DEFAULT_PASSWORD}')


if __name__ == "__main__":
    asyncio.run(seed())
