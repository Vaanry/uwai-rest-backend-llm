from fastapi import APIRouter

from .chat import router as chat_router

main_router = APIRouter()

main_router.include_router(chat_router)
