import re
from typing import Dict, List, Tuple
from gliner import GLiNER
from app.pipeline.datatypes.data_models import Entity, ChuckEntities

DEFAULT_LABELS = [
    "Malware Name",
    "Malware Family",
    "Malware Types",
    "Attack Pattern",
    "Strategy",

    "Economic Sector",
    "Industrial Sector",
    "Politic organization",

    # indicatori
    "Infrastructure",
    "Network",
    "Application Software",
    "Protocol",
    "Endpoint",
    "IP Address",
    "Email Address",
    "URL",
    "File",
    "Hash Value",

    # USER DATA
    "User Information",
    "System Information",

    # LOCATIONS INFORMATION
    "Country",
    "Region",
    "Year",

    # CAPABILITIES
    "C&C", 
    "Encryption",
    "Collection",
    "Execution"
]

class GlinerExtractor:
    def __init__(self, gliner_model_id: str = "gliner-community/gliner_large-v2.5", threshold: float = 0.70):
        self.ner_model = GLiNER.from_pretrained(pretrained_model_name_or_path=gliner_model_id)
        self.threshold = threshold

    @staticmethod
    def _normalize_text(s: str) -> str:
        text_clear = s.lower().strip()
        text_uri = re.sub(r"\s+", "-", text_clear)
        return text_uri
    
    @staticmethod
    def _merge_predictions(entities_chunks: List[ChuckEntities]) -> List[ChuckEntities]:
        """
        For each unique entity.text, find the entity with the highest score.
        Then set every occurrence of that text to have that best label and best score.
        Returns the mutated entities_chunks (same structure).
        """
        # 1) Find best (label, score) for each text
        best_by_text: Dict[str, Tuple[str, float]] = {}

        for chunk in entities_chunks:
            for ent in chunk.entities:
                cur = best_by_text.get(ent.text)
                if cur is None or ent.score > cur[1]:
                    best_by_text[ent.text] = (ent.label, ent.score)

        # 2) Overwrite all occurrences of the same text with the best (label, score)
        for chunk in entities_chunks:
            for i, ent in enumerate(chunk.entities):
                best_label, best_score = best_by_text[ent.text]
                if ent.label != best_label or ent.score != best_score:
                    # replace with a new Entity in the internal list
                    chunk.entities[i] = Entity(best_label, ent.text, best_score)

        return entities_chunks

    @staticmethod
    def _remove_duplicates(entities_chunk: List[Entity]) -> List[Entity]:
        seen = set()
        out = []
        for entity in entities_chunk:
            key = (entity.label, entity.text)
            if key in seen:
                continue
            seen.add(key)
            out.append(entity)
        return out

    def _gliner_extraction(self, chunks: List[str]) -> List[ChuckEntities]:
        chunks_entities: List[ChuckEntities] = []

        for chunk in chunks:
            entities_list : List[Entity] = []  # Reset per chunk
            predictions: List[Dict] = self.ner_model.predict_entities(
                chunk,
                labels=DEFAULT_LABELS,
                threshold=self.threshold,
                multi_label=False
            )

            for p in predictions:
                text = self._normalize_text(p["text"])
                label = p["label"]
                score = p["score"]

                if text and label:
                    name_class = self._mapper_classes(label)
                    entities_list.append(Entity(name_class, text, score))

            entities_list = self._remove_duplicates(entities_list)

            chunks_entities.append(ChuckEntities(entities_list))
        return chunks_entities

    @staticmethod
    def _mapper_classes(label: str) -> str:
        mapping = {
            "Malware Name": "Malware",
            "Malware Family": "Category",
            "Malware Types": "Category",

            "Attack Pattern": "AttackPattern",
            "Strategy": "AttackPattern",

            "Economic Sector": "Organization",
            "Industrial Sector": "Organization",
            "Politic organization": "Organization",

            "User Information": "Information",
            "System Information": "Information",

            "Infrastructure": "System",
            "Web System": "System",
            "Network": "System",
            "Application Software": "Software",

            "IP Address": "IPAddress",
            "Email Address": "EmailAddress",
            "URL": "URL",
            "Endpoint": "URL",
            "Hash Value": "Hash",

            "Application Protocol": "Protocols",
            "C&C": "Characteristic",
            "Encryption" : "Capability",
            "Collection" : "Capability",
            "Execution" : "Capability"
        }
        return mapping.get(label, label)
    
    def run(self, chunks: List[str]) -> List[ChuckEntities]:
        gliner_entities = self._gliner_extraction(chunks)   # -> [(label, text_norm?)...]
        clear_entities = self._merge_predictions(gliner_entities)
        return clear_entities