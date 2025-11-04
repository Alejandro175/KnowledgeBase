import re
from typing import List, Tuple
from neo4j_graphrag.exceptions import SearchValidationError, Text2CypherRetrievalError
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.retrievers import Text2CypherRetriever

from app.core.templates import CustomRagTemplate
from app.models.triples import Triple, Entity


class LLMResponseService:
    def __init__(self, llm: OpenAILLM, retriever: Text2CypherRetriever):
        prompt_template = CustomRagTemplate()
        self._llm = llm
        self._rag = GraphRAG(retriever=retriever, llm=self._llm, prompt_template=prompt_template)

    @staticmethod
    def parse_context_to_triples(context) -> List[Triple]:
        triples = []
        pattern = (
            r"subject='([^']+)'\s+sub_confidence=(None|[\d.]+)\s+"
            r"predicate='([^']+)'\s+object='([^']+)'\s+obj_confidence=(None|[\d.]+)"
        )

        for item in context:
            if isinstance(item.content, str):
                match = re.search(pattern, item.content)
                if match:
                    sub_conf_raw = match.group(2)
                    sub_conf = None if sub_conf_raw == "None" else float(sub_conf_raw)
                    obj_conf_raw = match.group(5)
                    obj_conf = None if obj_conf_raw == "None" else float(obj_conf_raw)

                    triple_subject = Entity(
                        uri=match.group(1),
                        confidence=sub_conf
                    )
                    triple_object = Entity(
                        uri=match.group(4),
                        confidence=obj_conf
                    )
                    triples.append(Triple(
                        subject=triple_subject,
                        predicate=match.group(3),
                        object=triple_object
                    ))
                else:
                    print(f"No match for: {item.content}")
                    continue

        return triples

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

    def contextual_answer(self, question: str) -> Tuple[str, str, List[Triple]]:
        """
        Generate context-aware answer using RAG approach.

        Args:
            question (str): User's question.
        """
        format_context = List[Triple]
        response = ""
        cypher_query = ""
        try:
            response = self._rag.search(query_text=question, return_context=True)
            print(f"DEBUG Response: {response}")

            cypher_query = response.retriever_result.metadata.get("cypher")
            context = response.retriever_result.items

            if context is None:
                format_context = "No relevant context found."
            else:
                format_context = self.parse_context_to_triples(context)

            print("DEBUG CONTEXT")
            #print(context)
            print(format_context)

        except SearchValidationError as e:
            print(f"Validation of the input arguments fail: {e}")
        except Text2CypherRetrievalError as e:
            print(f"Error during query translation: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        return response.answer, cypher_query, format_context