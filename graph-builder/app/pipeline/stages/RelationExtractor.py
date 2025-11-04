from typing import List, Dict
import json
from openai import OpenAI
from app.pipeline.datatypes.data_models import Triple, ChuckEntities

context = """
You extract factual triples from cybersecurity reports about malware.

OUTPUT FORMAT (STRICT)
<subject>,<relation>,<object>
- One triple per line
- No duplicates, no extra text
- Multi-word entities: use hyphens (e.g., "c&c-server")

ALLOWED RELATIONS
Malware,executes,AttackPattern
Malware,targetsSystem,System
Malware,targetsInformation,Information
Malware,targetsSoftware,Software
Malware,hasOriginCountry,Country
Malware,hasTargetCountry,Country
Malware,attackOrg,Organization
Malware,isIndicatedByEmail,EmailAddress
Malware,isIndicatedByFile,File
Malware,isIndicatedByHash,Hash
Malware,isIndicatedByUrl,URL
Malware,isIndicatedByAddress,IPAddress
Malware,isMember,Category
Malware,hasCharacteristic,Capability
Malware,hasCharacteristic,Protocols

RULES
1. Use concrete values from chunk/mentioned_entities, never generic class names like "malware"
2. Subject MUST be the malware name mentioned on malware_list
3. ALWAYS extract isIndicatedBy for URLs, IPs, emails, files, hashes

INPUT
{"chunk": "...", "mentioned_entities": [{"LABEL":"...","TEXT":"..."}], "malware_list": ["...", "..."]}

EXAMPLES
onionduke,hasLocation,russia
onionduke,hasCharacteristic,c&c-server
onionduke,targetOrg,government-agencies
onionduke,isIndicatedByUrl,https://abc.example/onion
cloud-atlas,execute,cyber-espionage
cloud-atlas,isIndicatedByFile,car-for-sale.doc
"""

class RelationExtractorLLM:
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini", temperature = 0): 
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._temperature = temperature

    @staticmethod
    def _clear_entity_name(string: str):
        return string.replace("\"", "").strip().replace(" ", "-").lower()

    def run(self, doc_text_chunks: List[str], ner_output: List[ChuckEntities]) -> List[Triple]:
        seen = set()
        malware_list = []
        mentioned_entities = []
        results = []

        for entities_list in ner_output:
            chuck_entities = []

            for entity_item in entities_list.entities:
                chuck_entities.append({"LABEL": entity_item.label, "TEXT": entity_item.text})

                if entity_item.label == "Malware" and entity_item.text not in seen:
                    seen.add(entity_item.text)
                    malware_list.append(entity_item.text)

            mentioned_entities.append(chuck_entities)

        for (chunk, mentioned_entities) in zip(doc_text_chunks, mentioned_entities):
            relations = self._llm_extract_relations(chunk, mentioned_entities, malware_list)
            results.extend(relations)

        return results
                
    def _llm_extract_relations(self, text_chunk: str, mentioned_entities: List[Dict[str, str]], malware_list: List[str]) -> List[Triple]:

        user_payload = {
            "Malware_in_report": malware_list,
            "chunk": text_chunk,
            "mentioned_entities": mentioned_entities
        }

        user_content = json.dumps(user_payload, ensure_ascii=False)

        # noinspection PyTypeChecker
        response = self._client.responses.create(
            model=self._model,
            input= [
                {"role": "system", "content": context},
                {"role": "user", "content": user_content}
            ]
        )

        content = response.output_text

        print("------------------")
        print(text_chunk)
        print("------------------")
        print(content)
        print("------------------")

        triples = []
        for line in content.splitlines():
            parts = line.split(",")
            if len(parts) == 3:
                triples.append(
                    Triple(
                        self._clear_entity_name(parts[0]),
                        parts[1],
                        self._clear_entity_name(parts[2])
                    )
                )

        return triples