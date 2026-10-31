from fastapi import APIRouter, HTTPException

from api.deps import check_scope
from api.schemas import StudyIn, SummaryIn
from src import config, study, summary

router = APIRouter(prefix="/api", tags=["study"])


@router.get("/config")
def get_config():
    return {"summary_styles": list(summary.STYLES), "max_items": config.MAX_ITEMS}


@router.post("/flashcards")
def flashcards(body: StudyIn):
    check_scope(body.scope)
    cards = study.make_cards(body.scope or None, body.topic, body.n)
    if not cards:
        raise HTTPException(502, "Could not generate cards. Try again or use a different topic.")
    return {"cards": cards}


@router.post("/quiz")
def quiz(body: StudyIn):
    check_scope(body.scope)
    questions = study.make_quiz(body.scope or None, body.topic, body.n)
    if not questions:
        raise HTTPException(502, "Could not generate a quiz. Try again or use a different topic.")
    return {"questions": questions}


@router.post("/summary")
def summarize(body: SummaryIn):
    check_scope(body.scope)
    if body.style not in summary.STYLES:
        raise HTTPException(422, "Unknown summary style.")
    return {"summary": summary.summarize(body.scope, body.style)}
