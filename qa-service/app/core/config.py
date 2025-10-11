from pydantic_settings import BaseSettings

class Config(BaseSettings):
    openai_api_token: str
    openai_model: str
    neo4j_username: str
    neo4j_password: str
    neo4j_dbname: str
    neo4j_uri: str

config = Config()