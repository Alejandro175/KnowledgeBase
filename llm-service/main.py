from fastapi import FastAPI, HTTPException, status
from schemas.models import Request, ContextualRequest, AnswerResponse
from services.response_generator import ResponseGenerator
from services.query_translador import QueryTranslator

generator = ResponseGenerator()
translator = QueryTranslator()

app = FastAPI(title="SOA Security Assistant API", version="1.0.0")

@app.post("/api/answer/generate")
def process_request_context(request: Request):
    """
    Generate answer using RAG approach with context.
    Context viene recuperato internamente dal sistema.
    """
    try:
        # Qui dovresti recuperare il context dal tuo sistema RAG
        # Ad esempio da un vector database o documento
        context = QueryTranslator.translate_query(request.question)  # Tua funzione
        
        contextual_req = ContextualRequest(
            question=request.question,
            context=context
        )
    
        result = generator.answer_with_context(contextual_req)
        return AnswerResponse(answer=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/answer/direct")
def process_request_llm(request: Request):
    """
    Generate answer directly from LLM without context.
    """
    try:
        result = generator.answer_without_context(request)
        return AnswerResponse(answer=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))