from fastapi import FastAPI
from fastapi.requests import Request

from app.routers import main_router

from .config import settings

app = FastAPI(title=settings.app_title)


@app.get("/")
async def welcome(request: Request) -> dict:
    return {"Hello!": "LLM backend"}


app.include_router(main_router)
