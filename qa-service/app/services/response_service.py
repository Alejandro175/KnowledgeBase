from langchain_openai import ChatOpenAI
from neo4j_graphrag.retrievers import Text2CypherRetriever
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.exceptions import SearchValidationError, Text2CypherRetrievalError


class LLMResponseService:
    def __init__(self, llm: OpenAILLM, retriever: Text2CypherRetriever):
        self._llm = llm
        self._rag = GraphRAG(retriever=self._retriever, llm=self._llm)

    def direct_answer(self, question: str):
        """
        Generate direct answer without context.

        Args:
            question (str): User's question.
        
        Returns:
            dict: Dictionary with the LLM-generated answer.
        """
        response = self._llm.invoke(question)
        return response.content
    
    def contextual_answer(self, question: str):
        """
        Generate context-aware answer using RAG approach.

        Args:
            question (str): User's question.
        """
        format_context = ""

        try:
            response = self._rag.search(query_text=question, return_context=True)
            print(f"Response: {response}")

            cypher_query = response.retriever_result.metadata.get("cypher_query", cypher_query)
            context = response.retriever_result.items

            if context is None:
                format_context = "No relevant context found."
            else:
                format_context = "\n".join(item.content for item in context)

        except SearchValidationError as e:
            print(f"Validation of the input arguments fail: {e}")
        except Text2CypherRetrievalError as e:
            print(f"Error during query translation: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


        return response.answer, cypher_query, format_context

"""
class LLMResponseServiceOLD:
    def __init__(self, api_key: str = None, model: str = "gpt-5o-mini"):
        self._llm = ChatOpenAI(
            temperature=0,
            api_key=api_key, 
            model=model 
        )
        self._prompt_builder = PromptBuilder()

    @staticmethod
    def _format_triples(triples, flag):

        formatted = "\nTriples:\n"
        if flag == 0:
            formatted += "\n".join(f"- {triple_group}" for triple_group in triples)
        else:
            for triple_group in triples:
                formatted += "\n".join(f"  - {triple[0]} {triple[1]} {triple[2]}" for triple in triple_group)
        return formatted

    def direct_answer(self, question: str):

        prompt = self._prompt_builder.build_direct_prompt(question)
        response = self._llm.invoke(prompt)
        return response.content

    def contextual_answer(self, question: str, database: KnowledgeGraph):

        prompt = self._prompt_builder.build_translation_prompt(question)
        response = self._llm.invoke(prompt)
        cypher_query = response.content.strip()

        print(F"QUERY CYPHER TRADOTTA: {cypher_query}")

        triples = database.execute_query(cypher_query)

        formatted_triples = self._format_triples(triples = triples, flag=0)

        print(f"[DEBUG] Formatted Triples: {formatted_triples}")

        prompt = self._prompt_builder.build_contextual_prompt(question=question, context=formatted_triples)
        response = self._llm.invoke(prompt)

        return response.content, cypher_query, formatted_triples
"""