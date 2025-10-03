import os
from pathlib import Path
from time import sleep

import torch
from stages.FileReader import FileReader
from stages.NerExtractor import GlinerExtractor
from stages.ReLLM import RelationExtractorLLM
from stages.TriplesValidator import TriplesValidator
from stages.LoaderNeo4J import Neo4Jloader

NEO4J_URI=os.getenv("NEO4J_URI")
NEO4J_USERNAME=os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD=os.getenv("NEO4J_PASSWORD")
NEO4J_DBNAME=os.getenv("NEO4J_DBNAME")

NER_MODEL_ID = "gliner-community/gliner_large-v2.5"
LLM_MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507-FP8"

ONTOLOGY_PATH = "ontology/malwareOntology.rdf"
OUTPUT_PATH = "output"

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
NER_THRESHOLD = 0.52
CHECK_INTERVAL = 5 #Secondi

class Pipeline():
    def __init__(self):
        print("Inizializzazione pipeline...")
        self.LoadStage = Neo4Jloader(user_name=NEO4J_USERNAME, password=NEO4J_PASSWORD, uri=NEO4J_URI, database=NEO4J_DBNAME)
        self.ExtractionStage = FileReader(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        self.NERStage = GlinerExtractor(threshold=NER_THRESHOLD, gliner_model_id=NER_MODEL_ID)
        self.RelationExtractionStage = RelationExtractorLLM(model_id=LLM_MODEL_ID)
        self.ValidationStage = TriplesValidator(ontology_path=ONTOLOGY_PATH, output_dir=OUTPUT_PATH)
        
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
        print(triples_raw)
        # Validazione triple

        print("Triples validation process.")
        rdf_output = self.ValidationStage.run(triples_raw, output_entities, in_path.stem)

        # Load on neo4J
        print("Triples load process.")
        self.LoadStage.run(rdf_output)


        print("Fine esecuzione\n")

def main():
    pipeline = Pipeline()
    
    # Crea le directory necessarie
    input_dir = Path("input")
    input_dir.mkdir(exist_ok=True)

    print(f"Monitoraggio della directory input ogni 5 secondi...")
    print("Premi Ctrl+C per interrompere.\n")
    
    try:
        while True:
            # Cerca file .txt nella directory input
            input_files = list(input_dir.glob("*.txt"))
            print("Ciclo")
            if input_files:
                for input_file in input_files:
                    try:
                        print(f"processando file: {input_file.name}")
                        pipeline.process_file(str(input_file))

                        print(f"File {input_file.name} processato con successo.")
                        input_file.unlink()
                        
                    except Exception as e:
                        print(f"Errore durante l'elaborazione di {input_file.name}: {e}")
                        # In caso di errore, cancella comunque il file per evitare loop infiniti
                        try:
                            input_file.unlink()
                            print(f"File {input_file.name} cancellato dopo errore.")
                        except Exception as del_err:
                            print(f"Impossibile cancellare {input_file.name}: {del_err}")
            
            # Attendi prima del prossimo controllo
            sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\nMonitoraggio interrotto dall'utente.")

if __name__ == "__main__":
    main()