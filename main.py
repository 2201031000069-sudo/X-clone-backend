import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from slowapi import _rate_limit_exceeded_handler

from database import init_db
from ratelimit import limiter
from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.tweets import router as tweets_router
from routers.trends import router as trends_router
from routers.upload import router as upload_router
from routers.search import router as search_router
from routers.messages import router as messages_router
from routers.ws import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Nextweet API", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8080").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(tweets_router)
app.include_router(trends_router)
app.include_router(upload_router)
app.include_router(search_router)
app.include_router(messages_router)
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
