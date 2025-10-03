from rdflib_neo4j import HANDLE_VOCAB_URI_STRATEGY, Neo4jStoreConfig, Neo4jStore
from neo4j.exceptions import ServiceUnavailable
from rdflib import Graph

class Neo4Jloader:
    def __init__(self, uri: str, user_name: str, password: str, database: str = "neo4j"):
        auth_data = {'uri': uri, 'database': database, 'user': user_name, 'pwd': password}
        print("Tentativo di conessione a Neo4J...")
        try:
            config = Neo4jStoreConfig(
                auth_data=auth_data,
                batching=True,
                handle_vocab_uri_strategy=HANDLE_VOCAB_URI_STRATEGY.IGNORE
            )
            self.neo4jGraph = Graph(store=Neo4jStore(config=config))
        except ServiceUnavailable as e:
            raise RuntimeError(f"Neo4j non è raggiungibile: {e}") from e

    def run(self, input_file_path: str):
        self.neo4jGraph.parse(input_file_path, format="application/rdf+xml")
        self.neo4jGraph.close(True)