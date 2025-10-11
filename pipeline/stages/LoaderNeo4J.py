from rdflib_neo4j import HANDLE_VOCAB_URI_STRATEGY, Neo4jStoreConfig, Neo4jStore
from neo4j.exceptions import ServiceUnavailable, SessionExpired
from rdflib import Graph

class Neo4Jloader:
    def __init__(self, uri: str, user_name: str, password: str, database: str = "neo4j"):
        self.auth_data = {'uri': uri, 'database': database, 'user': user_name, 'pwd': password}
        self.neo4jGraph = None
        self._connect()

    def _connect(self):
        print("Tentativo di connessione a Neo4J...")
        config = Neo4jStoreConfig(
            auth_data=self.auth_data,
            batching=True,
            handle_vocab_uri_strategy=HANDLE_VOCAB_URI_STRATEGY.IGNORE
        )
        self.neo4jGraph = Graph(store=Neo4jStore(config=config))
        print("Connessione stabilita.")

    def is_connected(self) -> bool:
        try:
            store = self.neo4jGraph.store
            driver = getattr(store, "_driver", None)
            if driver is None:
                return False
            with driver.session() as session:
                session.run("RETURN 1")
            return True
        except (ServiceUnavailable, SessionExpired, AttributeError):
            return False

    def run(self, input_file_path: str):
        if not self.is_connected():
            print("Connessione non attiva. Riprovo a connettermi...")
            try:
                self._connect()
            except Exception as e:
                raise RuntimeError(f"Impossibile ristabilire la connessione a Neo4j: {e}")
        self.neo4jGraph.parse(input_file_path, format="application/rdf+xml")
        self.neo4jGraph.close(True)

    def close(self):
        if self.neo4jGraph:
            try:
                self.neo4jGraph.close(True)
                print("Connessione chiusa.")
            except Exception as e:
                print(f"Errore durante la chiusura: {e}")
            finally:
                self.neo4jGraph = None