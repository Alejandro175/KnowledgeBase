import time
from pathlib import Path
from rdflib_neo4j import HANDLE_VOCAB_URI_STRATEGY, Neo4jStoreConfig, Neo4jStore
from rdflib import Graph
from neo4j.exceptions import ServiceUnavailable, SessionExpired

class Neo4jWriter:
    def __init__(self, uri: str, user_name: str, password: str, database: str = "neo4j"):
        self.auth_data = {'uri': uri, 'user': user_name, 'pwd': password, 'database': database}
        self.neo4jGraph = None

    def _connect(self):
        while True:
            try:
                print("Attempting to connect to Neo4j...")
                config = Neo4jStoreConfig(
                    auth_data=self.auth_data,
                    batching=True,
                    handle_vocab_uri_strategy=HANDLE_VOCAB_URI_STRATEGY.IGNORE
                )
                self.neo4jGraph = Graph(store=Neo4jStore(config=config))
                print("Connection established.")
                break
            except Exception as e:
                print(f"Connection failed: {e}. Retrying in 10 seconds...")
                time.sleep(10)

    def is_connected(self) -> bool:
        if self.neo4jGraph is None:
            return False

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

    def run(self, input_file_path: str, delete_after: bool = True):
        if not self.is_connected():
            print("Connection not active. Attempting to (re)connect...")
            try:
                self._connect()
            except Exception as e:
                raise RuntimeError(f"Unable to establish connection to Neo4j: {e}")

        try:
            self.neo4jGraph.parse(input_file_path, format="application/rdf+xml")
            self.neo4jGraph.close(True)
            print(f"Successfully loaded {input_file_path} into Neo4j")
        except Exception as e:
            raise RuntimeError(f"Error loading data into Neo4j: {e}")
        finally:
            if delete_after:
                Path(input_file_path).unlink(missing_ok=True)
