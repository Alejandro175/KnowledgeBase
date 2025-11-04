from typing import List
from pydantic import BaseModel
from app.models.triples import Triple

class Answer(BaseModel):
    answer: str

class AnswerWithContext(Answer):
    query: str
    context: List[Triple]
