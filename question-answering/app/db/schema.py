from app.core.config import config
from neo4j import GraphDatabase

driver = GraphDatabase.driver(uri=config.neo4j_uri, database=config.neo4j_database,
                              auth=(config.neo4j_username, config.neo4j_password))
