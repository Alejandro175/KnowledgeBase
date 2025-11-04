from pydantic_settings import BaseSettings

class Config(BaseSettings):
    ner_model: str
    openai_api_key: str
    relation_extraction_llm: str
    ontology_file_path: str
    neo4j_username: str
    neo4j_password: str
    neo4j_database: str
    neo4j_uri: str

builder_config = Config()
