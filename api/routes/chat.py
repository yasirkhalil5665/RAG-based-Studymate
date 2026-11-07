from fastapi import APIRouter

from api.deps import check_scope
from api.schemas import ChatIn
from api.state import sessions
from src.chat import ask

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
def chat(body: ChatIn):
    check_scope(body.scope)
    history = sessions.setdefault(body.session_id, [])
    question = body.question.strip()
    result = ask(question, body.scope or None, history)
    history.append((question, result["answer"]))
    return result


@router.delete("/{session_id}")
def clear(session_id: str):
    sessions.pop(session_id, None)
    return {"cleared": True}
