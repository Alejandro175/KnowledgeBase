from fastapi import FastAPI
from app.api.router import router

app = FastAPI(title="Knowledge graph builder", version="1.0")
app.include_router(prefix="/graph-builder/api", router=router)

@app.get("/")
def health_check():
    return {"status": "OK", "service": "Graph Builder API"}

