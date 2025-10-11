from pydantic import BaseModel

class Answer(BaseModel):
    answer: str

class AnswerWithContext(Answer):
    query: str
    context: str