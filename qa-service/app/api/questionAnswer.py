from fastapi import APIRouter, Depends, HTTPException
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.retrievers import Text2CypherRetriever

from app.services.response_service import LLMResponseService
from app.models.requests import LLMRequest
from app.models.answers import Answer, AnswerWithContext
from app.core.config import config
from app.db.schema import neo4j_schema, examples, driver

router = APIRouter()

def get_llm(api_key: str = config.openai_api_token, model: str = config.openai_model) -> OpenAILLM:
    return OpenAILLM(api_key=api_key, model_name=model, model_params={"temperature": 0})

def get_query_translator(llm=Depends(get_llm)) -> Text2CypherRetriever:
    return Text2CypherRetriever(driver, llm, neo4j_schema, examples)

def get_qa_service(llm=Depends(get_llm), retriever=Depends(get_query_translator)) -> LLMResponseService:
    return LLMResponseService(llm, retriever)

@router.post("/generate")
def process_request_context(request: LLMRequest, service: LLMResponseService = Depends(get_qa_service)):
    """
    Generate answer using RAG approach with context.
    Context viene recuperato internamente dal sistema.
    """
    try:
        result, cypher_query, context = service.contextual_answer(question=request.question)
        return AnswerWithContext(answer=result, query=cypher_query, context=context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/direct")
def process_request_context(request: LLMRequest, service: LLMResponseService = Depends(get_qa_service)):
    """
    Generate answer directly from LLM without context.
    """
    try:
        result = service.direct_answer(request.question)
        return Answer(answer=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))