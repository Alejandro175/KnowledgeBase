from app.api.question_answer import router
from fastapi import FastAPI

app = FastAPI(title="Security Assistant API", version="1.0.0")

app.include_router(router, prefix="/api/question-answering")

@app.get("/")
def live_prof():
    return {"status": "OK"}
