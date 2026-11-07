from pydantic import BaseModel, Field

from src.config import MAX_ITEMS


class ChatIn(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=2000)
    scope: str | None = None


class StudyIn(BaseModel):
    scope: str | None = None
    topic: str = Field(default="", max_length=200)
    n: int = Field(default=10, ge=1, le=MAX_ITEMS)


class SummaryIn(BaseModel):
    scope: str
    style: str = "Short overview"
