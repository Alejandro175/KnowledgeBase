import os
from pathlib import Path
from time import sleep

from stages.FileReader import FileReader
from stages.NerExtractor import GlinerExtractor
from stages.RelationExtractor import RelationExtractorLLM
from stages.TriplesValidator import TriplesValidator
from stages.Neo4jWriter import Neo4jWriter

# NEO4J Configuration
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DBNAME = os.getenv("NEO4J_DBNAME")

# NER and LLM Configuration
NER_MODEL_ID = os.getenv("NER_MODEL")
LLM_MODEL_ID = os.getenv("OPENAI_MODEL")
OPENAI_KEY = os.getenv("OPENAI_API_TOKEN")

# ONTOLOGY Configuration
ONTOLOGY_PATH = os.getenv("ONTOLOGY_FILE")

# Pipeline Configuration
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
NER_THRESHOLD = 0.52
CHECK_INTERVAL = 5 # Secondi

class Pipeline():
    def __init__(self):
        print("Inizializzazione pipeline...")
        self.LoadStage = Neo4jWriter(user_name=NEO4J_USERNAME, password=NEO4J_PASSWORD, uri=NEO4J_URI, database=NEO4J_DBNAME)
        self.ExtractionStage = FileReader(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        self.NERStage = GlinerExtractor(threshold=NER_THRESHOLD, gliner_model_id=NER_MODEL_ID)
        self.RelationExtractionStage = RelationExtractorLLM(api_key=OPENAI_KEY, model=LLM_MODEL_ID)
        self.ValidationStage = TriplesValidator(ontology_path=ONTOLOGY_PATH)
        
    def process_file(self, input_file: str):

        in_path = Path(input_file)
        if not in_path.exists():
            raise FileNotFoundError(f"File non trovato: {in_path}")
    
        # Read input file
        print(f"Read file {in_path}.")
        output_chunks = self.ExtractionStage.run(input_file)

        # Named Entity Extraction
        print("Named Entity Extraction process.")
        output_entities = self.NERStage.run(output_chunks)
        print(output_entities)

        # Creazione di relazioni
        print("Relation Extraction process.")
        triples_raw = self.RelationExtractionStage.run(output_chunks, output_entities)

        # Validazione triple
        print("Triples validation process.")
        rdf_tmp_file = self.ValidationStage.run(triples_raw, output_entities, in_path.stem)

        # Load on neo4J
        #print("Triples load process.")
        self.LoadStage.run(rdf_tmp_file, delete_after=True)
        self.LoadStage.close()

        print("Fine esecuzione\n")

def main():
    pipeline = Pipeline()
    Path("temp").mkdir(exist_ok=True)

    # Crea le directory necessarie
    input_dir = Path("input").mkdir(exist_ok=True)

    print(f"Monitoraggio della directory input ogni 5 secondi...")
    print("Premi Ctrl+C per interrompere.\n")

    try:
        while True:
            input_files = list(input_dir.glob("*.txt"))
            
            if input_files:
                input_file = input_files[0]
                
                try:
                    print(f"Processando file: {input_file.name}")
                    pipeline.process_file(str(input_file))
                    print(f"File {input_file.name} processato con successo.")
                    
                except Exception as e:
                    print(f"Errore durante il processamento del file: {e}")
                    
                finally:
                    input_file.unlink(missing_ok=True)

            sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\n\nMonitoraggio interrotto dall'utente.")
    
if __name__ == "__main__":
    main()