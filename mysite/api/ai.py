from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from mysite.database.db import get_db
from mysite.database.schema import SearchSchema, AnswerSchema, TextSchema
from mysite.chains.ai_search import search
from mysite.chains.ai_answer import answer
from mysite.chains.ai_analyze import analyze
from mysite.chains.llm import with_optional_llm

ai_router = APIRouter(prefix='/ai', tags=['AI'])

@ai_router.post('/search/')
def search_courses(body: SearchSchema, db: Session = Depends(get_db)):
    return with_optional_llm('search', body.model_dump(), search(db, body.question))

@ai_router.post('/answer/')
def answer_message(body: AnswerSchema):
    return with_optional_llm('answer', body.model_dump(), answer(body.text, body.facts))

@ai_router.post('/analyze/')
def analyze_message(body: TextSchema, db: Session = Depends(get_db)):
    return with_optional_llm('analyze', body.model_dump(), analyze(db, body.text))
