from pydantic import BaseModel

class LLMRequest(BaseModel):
    """Request containing only a user question."""
    question: str