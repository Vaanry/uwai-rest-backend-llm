from fastapi import APIRouter, status
from fastapi.responses import FileResponse
from pydantic.types import StringConstraints
from typing_extensions import Annotated

from openai_backend.prompts import chat_with_bot

from ..config import settings

FILES = settings.files


router = APIRouter(prefix="/chat", tags=["chat"])


MessageRequest = Annotated[str, StringConstraints(min_length=3, max_length=100)]


@router.post("/")
async def chat(request: MessageRequest, id: str):
    """Router for LLM chat
    id: Идентификатор пользователя, приходит с базового бэкэнда"""
    answer = chat_with_bot(id, request)
    if isinstance(answer, FileResponse):
        return answer
    response = {
        "status_code": status.HTTP_200_OK,
        "detail": answer,
    }
    return response
