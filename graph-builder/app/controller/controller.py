from datetime import datetime
import uuid
from pathlib import Path
from fastapi import UploadFile

from app.pipeline.stages.FileReader import FileReader
from app.pipeline.stages.NamedEntityRecognition import GlinerExtractor
from app.pipeline.stages.RelationExtractor import RelationExtractorLLM
from app.pipeline.stages.OntologyValidator import RDFsTriplesValidator
from app.pipeline.stages.Neo4jWriter import Neo4jWriter
from ..core.config import builder_config as config

# Pipeline Configuration
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
NER_THRESHOLD = 0.52

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

class PipelineController:
    def __init__(self):
        self.LoadStage = Neo4jWriter(
            user_name=config.neo4j_username,
            password=config.neo4j_password,
            uri=config.neo4j_uri,
            database=config.neo4j_database
        )
        self.ExtractionStage = FileReader(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        self.NERStage = GlinerExtractor(
            threshold=NER_THRESHOLD,
            gliner_model_id=config.ner_model
        )
        self.RelationExtractionStage = RelationExtractorLLM(
            api_key=config.openai_api_key,
            model=config.relation_extraction_llm
        )
        self.ValidationStage = RDFsTriplesValidator(
            ontology_path=config.ontology_file_path
        )
        print("Pipeline created!!")

    def process_file(self, input_file_path: Path, file_name: str) -> bool:
        """Processa il file attraverso la pipeline"""
        if not input_file_path.exists():
            raise FileNotFoundError(f"File non trovato: {input_file_path}")

        # Read input file
        print(f"Read input file {input_file_path}")
        output_chunks = self.ExtractionStage.run(str(input_file_path))

        # Named Entity Extraction
        print("Named Entity Extraction")
        output_entities = self.NERStage.run(output_chunks)

        # Relation Extraction
        print("RelationExtraction")
        triples_raw = self.RelationExtractionStage.run(output_chunks, output_entities)

        # Validation
        print("Validation")
        rdf_tmp_file = self.ValidationStage.run(triples_raw, output_entities, file_name)

        # Load on Neo4j
        print("Neo4jWriter")
        self.LoadStage.run(rdf_tmp_file)
        return True

    def file_handler(self, file: UploadFile) -> dict:
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename

        print(f"File: {file_path}")

        try:
            with open(file_path, "wb") as file_object:
                file_object.write(file.file.read())

            print("Fila saved and start processing")
            self.process_file(file_path, file.filename)

            result = {
                "file_name": file.filename,
                "timestamp": datetime.now()

            }

            return result
        except Exception as e:
            if file_path.exists():
                file_path.unlink()
            raise