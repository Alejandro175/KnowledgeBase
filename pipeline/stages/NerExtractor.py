import re
from typing import Dict, List, Tuple
from gliner import GLiNER

DEFAULT_LABELS = [
    # Nomi & attori
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
        self.ner_model = GLiNER.from_pretrained(gliner_model_id)
        self.threshold = threshold

    @staticmethod
    def _normalize_text(s: str) -> str:
        text_clear = s.lower().strip()
        text_uri = re.sub(r"\s+", "-", text_clear)
        return text_uri
    
    @staticmethod
    def _merge_predictions(
        entities_chunks: List[List[Tuple[str, str, float]]]
    ) -> List[List[Tuple[str, str, float]]]:

        # Costruisci una lista piatta di indici (chunk_idx, entity_idx) nell'ordine di apparizione
        flat_indices: List[Tuple[int, int]] = []
        for ci, chunk in enumerate(entities_chunks):
            for ei in range(len(chunk)):
                flat_indices.append((ci, ei))

        n = len(flat_indices)

        for k in range(n):
            ci_k, ei_k = flat_indices[k]
            label_k, text_k, score_k = entities_chunks[ci_k][ei_k]

            for m in range(n):
                if m == k:
                    continue

                ci_m, ei_m = flat_indices[m]
                label_m, text_m, score_m = entities_chunks[ci_m][ei_m]

                if text_k == text_m and label_k != label_m:
                    if score_k > score_m:
                        entities_chunks[ci_m][ei_m] = (label_k, text_k, score_k)

        return entities_chunks

    def _remove_duplicates(
        self,
        entities_chunk: List[Tuple[str, str, float]]
    ) -> List[Tuple[str, str, float]]:
        seen = set()
        out: List[Tuple[str, str, float]] = []
        for label, text, score in entities_chunk:
            key = (label, text)
            if key in seen:
                continue
            seen.add(key)
            out.append((label, text, score))
        return out

    def _gliner_extraction(self, chunks: List[str]) -> List:
        entities_chunks = []

        for chunk in chunks:
            entities_chuck: List[Tuple[str, str]] = []  # Reset per chunk
            predictions: List[Dict] = self.ner_model.predict_entities(
                chunk,
                labels=DEFAULT_LABELS,
                threshold=self.threshold,
                multi_label=False
            )

            for p in predictions:
                text = self._normalize_text(p["text"])
                label = p["label"]

                if text and label:
                    name_class = self._mapper_classes(label)
                    # Creazione della tupla (label, text)
                    #entities_chuck.append((name_class, text, p["score"]))
                    entities_chuck.append((name_class, text, p["score"]))

            entities_chuck = self._remove_duplicates(entities_chuck)
            entities_chunks.append(entities_chuck)
        return entities_chunks
    
    def _mapper_classes(self, class_str: str) -> str:
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

        return mapping.get(class_str, class_str)
    
    def run(self, chunks: List[str]) -> List[Tuple[str, str]]:
        gliner_entities = self._gliner_extraction(chunks)   # -> [(label, text_norm?)...]
        currected = self._merge_predictions(gliner_entities)
        return currected


