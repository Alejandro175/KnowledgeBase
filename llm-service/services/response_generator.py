import os
from schemas.requests import Request, ContextualRequest
from langchain_openai import ChatOpenAI

class ResponseGenerator:
    def __init__(self):
        self._llm = ChatOpenAI(
            temperature=0,  # Deterministic output for reproducible results
            api_key=os.getenv("OPENAI_API_TOKEN"),  # Load API key from environment
            model="gpt-4o-mini"  # Use a lightweight GPT-4 variant
        )

    def answer_without_context(self, request: Request):
        """
        Generate answer directly from LLM without context.

        Args:
            request (Request): Request object containing only the question.
        
        Returns:
            dict: Dictionary with the LLM-generated answer.
        """
        response = self._llm.invoke(request.question)
        return {"answer": response.content.strip()}

    def answer_with_context(self, request: ContextualRequest):
        """
        Generate context-aware answer using RAG approach.

        Args:
            request (ContextualRequest): Request object with question and context.
        
        Returns:
            dict: Dictionary with the context-aware answer.
        """
        prompt = [
            {"role": "system", "content": """
            Your role as an AI assistant is to support a security analyst in monitoring a system with a SOA architecture, helping the analyst 
            understand the dependencies between the different services that make up the architecture and which resources they depend on for their operation.
            
            Your primary goal is to enhance the analyst's cyber situation awareness by providing concise, context-aware insights.  

            # Instructions  
            - Answer exclusively based on the information provided in the context; do not use your own pre-existing knowledge or external sources. 
            - Prioritize clear and concise answers that directly assist the analyst.  
            - Focus on practical insights that improve the analyst's decision-making. 
            """},
            {"role": "user", "content": f"Context: {request.context}\n\nQuestion: {request.question}"}
        ]
        # Invoke the language model with the crafted prompt
        response = self._llm.invoke(prompt)

        # Return the cleaned answer
        return {"answer": response.content.strip()}