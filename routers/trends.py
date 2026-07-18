from fastapi import APIRouter

from schemas import TrendResponse

router = APIRouter(prefix="/trends", tags=["trends"])

TRENDS: list[TrendResponse] = [
    TrendResponse(category="Technology · Trending", tag="#WebDev", posts="128K posts"),
    TrendResponse(category="Trending in India", tag="#Bengaluru", posts="42.1K posts"),
    TrendResponse(category="Sports · Trending", tag="#WorldCup", posts="890K posts"),
    TrendResponse(category="Music · Trending", tag="Taylor Swift", posts="312K posts"),
    TrendResponse(category="Trending", tag="#OpenSource", posts="18.4K posts"),
    TrendResponse(category="News · LIVE", tag="Elections 2026", posts="1.2M posts"),
]


@router.get("", response_model=list[TrendResponse])
async def get_trends():
    return TRENDS
