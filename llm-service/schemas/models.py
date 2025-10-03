from pydantic import BaseModel

class Request(BaseModel):
    """Request containing only a user question."""
    question: str

class ContextualRequest(Request):
    """Request containing a question with retrieved context information."""
    context: str