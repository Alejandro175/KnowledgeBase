import csv
import os
from dotenv import load_dotenv

from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.retrievers import Text2CypherRetriever
from neo4j import GraphDatabase

from ragas.llms import llm_factory
from ragas import EvaluationDataset
from ragas import evaluate
from ragas.metrics import LLMContextRecall, Faithfulness, FactualCorrectness, AnswerRelevancy, ResponseRelevancy, NonLLMContextRecall, NonLLMContextPrecisionWithReference, LLMContextPrecisionWithoutReference, ContextEntityRecall, NonLLMStringSimilarity, ResponseGroundedness, SemanticSimilarity, BleuScore

from app.controller.response_service import LLMResponseService
from app.core.templates import neo4j_schema, examples

load_dotenv(dotenv_path=".env.test")

API_KEY = os.getenv("OPENAI_API_KEY")
ANSWER_LLM = os.getenv("ANSWER_LLM")
EVALUATION_LLM = os.getenv("EVALUATION_LLM")

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE")

RAG_RESULTS_PATH = "evaluation_rag.csv"
LLM_RESULTS_PATH = "evaluation_llm.csv"

sample_queries = [
    "What files are indicators of the malware scanbox?",
    "What are the software targets by the malware scanbox?",
    "What are the information targets by the malware scanbox?",
    "What files are indicators of the malware Cloud Atlas?",
    "What is the attack pattern executes by the malware Cloud Atlas?",
    "What are the countries related to the origin of the malware Cloud Atlas?",
    "What are the characteristics of the malware Cloud Atlas?",
    "What are the similarities between RedOctober and Cloud Atlas?",
    "Which organizations are attacking by the Scanbox malware?",
]

expected_responses = [
    "The Scanbox malware is indicated by a malicious JavaScript file that can be used to perform malicious activities.",
    "The Scanbox malware targets software applications like Microsoft Office, Internet Explorer, Adobe Flash, Adobe Acrobat, and Java by exploiting their vulnerabilities. To protect against it, keep these applications updated with the latest security patches and disable unnecessary plugins or features.",
    "The malware Scanbox targets the following information: referer, user-agent, location, cookie, domain, content title to identify specific content the victim is visiting, charset, screen width and height, operating system version, and system language.",
    "The Malware Cloud Atlas is indicated by the presence of the following files: Ukraine Russia's new art of war.doc, Катастрофа малайзийского лайнера.doc, Diplomatic Car for Sale.doc, МВКСИ.doc, Organigrama Gobierno Rusia.doc, Фото.doc, Информационное письмо.doc, Форма заявки (25-26.09.14).doc, Письмо_Руководителям.doc, Прилож.doc, Car for sale.doc and Af-Pak and Central Asia's security issues.doc.",
    "The Cloud Atlas malware conducts highly targeted attacks through spear-phishing documents. Its behavior demonstrates a strategic approach focused on specific individuals or organizations. Strengthening protection measures against phishing-based threats is essential.",
    "Cloud Atlas is connected to both Sweden and Russia, indicating that the threat actors or supporting infrastructure may be based in or active within these regions.",
    "Cloud Atlas shows command-and-control (C&C) behaviors, indicating communication with remote servers to coordinate its activities. Its use of cloud services suggests potential abuse of legitimate platforms for malicious purposes.",
    "RedOctober and Cloud Atlas exhibit notable parallels in their operations. Both employ spear-phishing documents to initiate attacks, demonstrating a shared dependence on email-based social engineering. They focus on targeted campaigns supported by Command-and-Control (C&C) infrastructure to sustain access. Furthermore, both groups aim at similar software ecosystems such as Microsoft Visual Studio and Office reflecting an emphasis on commonly used enterprise tools. Indicators also connect both operations to Russia and Kazakhstan, hinting at overlapping regional origins or targets.",
    "The malware Scanbox attacks industries including automotive, aerospace, and manufacturing",
]


def setup_rag() -> LLMResponseService:
    # RAG service setup
    llm_client = OpenAILLM(api_key=API_KEY, model_name=ANSWER_LLM)
    driver = GraphDatabase.driver(uri=NEO4J_URI, database=NEO4J_DATABASE,
                                  auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    retriever = Text2CypherRetriever(driver, llm_client, neo4j_schema, examples)
    return LLMResponseService(llm_client, retriever)

def triples_to_string(context_retrieved):
    text_context = []
    for triple in context_retrieved:
        text_context.append(triple.to_text())
    return text_context

def evaluation(response_service: LLMResponseService):
    dataset_rag = []
    dataset_llm = []
    rag_metrics = [SemanticSimilarity(), FactualCorrectness(mode="precision",atomicity="low"), AnswerRelevancy(), Faithfulness(), ResponseGroundedness()]
    llm_metrics = [SemanticSimilarity(), FactualCorrectness(mode="precision",atomicity="low"), AnswerRelevancy(), Faithfulness(), ResponseGroundedness()]

    evaluator_llm = llm_factory(EVALUATION_LLM)

    for query, reference in zip(sample_queries, expected_responses):
        rag_response, _, raw_context = response_service.contextual_answer(query)
        context = triples_to_string(raw_context)

        llm_response = response_service.direct_answer(query)

        print(f"Response RAG: {rag_response}")
        print(f"context: {context}")
        print(f"Response LLM: {llm_response}")

        dataset_rag.append(
            {
                "user_input": query,
                "retrieved_contexts": context,
                "reference_contexts": context,
                "response": rag_response,
                "reference": reference,
            }
        )


        dataset_llm.append(
            {
                "user_input": query,
                "response": llm_response,
                "retrieved_contexts": context,
                "reference": reference
            }
        )

    evaluation_dataset_rag = EvaluationDataset.from_list(dataset_rag)
    rag_result = evaluate(dataset=evaluation_dataset_rag,metrics=rag_metrics,llm=evaluator_llm)

    evaluation_dataset_llm = EvaluationDataset.from_list(dataset_llm)
    llm_result = evaluate(dataset=evaluation_dataset_llm,metrics=llm_metrics,llm=evaluator_llm)

    rag_metrics = rag_result.to_pandas()
    rag_metrics.to_csv(path_or_buf=RAG_RESULTS_PATH, mode="a", header=not os.path.exists(RAG_RESULTS_PATH), index=False)

    llm_metrics = llm_result.to_pandas()
    llm_metrics.to_csv(path_or_buf=LLM_RESULTS_PATH, mode="a", header=not os.path.exists(LLM_RESULTS_PATH), index=False)

if __name__ == "__main__":
    response_service = setup_rag()
    evaluation(response_service = response_service)







