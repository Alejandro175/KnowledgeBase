from pydantic_settings import BaseSettings

class Config(BaseSettings):
    openai_api_key: str
    answer_llm: str
    neo4j_username: str
    neo4j_password: str
    neo4j_database: str
    neo4j_uri: str

config = Config()
