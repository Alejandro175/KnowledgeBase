from fastapi import FastAPI
from app.api import questionAnswer

app = FastAPI(title="SOA Security Assistant API", version="1.0.0")

app.include_router(questionAnswer.router, prefix="/api/answer")

@app.get("/")
def live_prof():
    return {"status": "OK"}

