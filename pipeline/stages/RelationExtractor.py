from typing import Tuple, List
import json
from openai import OpenAI

context = """
You extract factual triples from cybersecurity reports about malware.

OUTPUT FORMAT (STRICT)
<subject>,<relation>,<object>
- One triple per line
- Lowercase (except hashes: preserve exact format)
- No duplicates, no extra text

ALLOWED RELATIONS
Malware,executes,AttackPattern
Malware,targetSystem,System
Malware,targetInformation,Information
Malware,targetSoftware,Software
Malware,hasLocation,Country/Region
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
1. Use concrete values from chunk/mentioned_entities, never generic class names
2. Subject MUST be the malware name (if missing, output nothing)
3. ALWAYS extract isIndicatedBy for URLs, IPs, emails, files, hashes
4. Multi-word entities: use hyphens (e.g., "c&c-server")

INPUT
{"chunk": "...", "mentioned_entities": [{"LABEL":"...","TEXT":"..."}]}

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
    def _clear_triple(triple: List[str, str, str]):
        triple[0] = triple[0].replace("\"", "").strip().replace(" ", "-").lower()
        triple[2] = triple[2].replace("\"", "").strip().replace(" ", "-").lower()
        return triple

    def run(self, text_chunks: List[str], entities_list: List[List]):
        seen = set()
        malwares_on_report = []
        results = []

        for chunk in entities_list:
            for label, text, _ in chunk:
                if label == "Malware" and text not in seen:
                    seen.add(text)
                    malwares_on_report.append((label, text))

        for (chunk_text, chunk_entities) in zip(text_chunks, entities_list):
            rels = self._llm_extract_relations(chunk_text, chunk_entities, malwares_on_report)
            results.append(rels)

        return results

                
    def _llm_extract_relations(self, text_chunk: str, mentioned_entities_raw: List[Tuple[str, str]], malwares_on_report):
        mentioned_entities = [{"LABEL": t, "TEXT": v} for (t, v, s) in mentioned_entities_raw]
        
        user_content = json.dumps(
            {
                "Malwares on report": malwares_on_report,
                "chunk": text_chunk,
                "mentioned_entities": mentioned_entities
            }, ensure_ascii=False
        )

        # Chiamata diretta all'API OpenAI
        response = self._client.responses.create(
            model=self._model,
            input=[
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
                parts = self._clear_triple(parts)
                triples.append(tuple(parts))

        return triples