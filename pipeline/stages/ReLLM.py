from typing import Tuple, List
from transformers import AutoModelForCausalLM, AutoTokenizer
import json

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
{"chunk": "...", "mentioned_entities": [{"type":"...","text":"..."}]}

EXAMPLES
onionduke,hasLocation,russia
onionduke,hasCharacteristic,c&c-server
onionduke,targetOrg,government-agencies
onionduke,isIndicatedByUrl,https://abc.example/onion
cloud-atlas,execute,cyber-espionage
cloud-atlas,isIndicatedByFile,car-for-sale.doc
"""
class RelationExtractorLLM:
    def __init__(self, model_id: str = "Qwen/Qwen3-4B-Instruct-2507-FP8"): 
        self._tokenizer = AutoTokenizer.from_pretrained(model_id)
        self._model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype="auto",
            device_map="auto",
        )

    @staticmethod
    def _clear_result(parts: str):
        parts[0] = parts[0].replace("\"", "").strip().replace(" ", "-").lower()
        parts[2] = parts[2].replace("\"", "").strip().replace(" ", "-").lower()
        return parts

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
            #print(chunk_entities)
            rels = self._llm_extract_relations(chunk_text, chunk_entities, malwares_on_report)
            results.append(rels)
            #print(rels)   # -> righe "subject, relation, object"
            #print("------ NEXT CHUNK -----")

        return results

                
    def _llm_extract_relations(self, text_chunk: str, mentioned_entities_raw: List[Tuple[str, str]], malwares_on_report):
        mentioned_entities = [{"class entity": t, "text": v} for (t, v, s) in mentioned_entities_raw]
        messages = [
            {"role": "system", "content": context},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "Malwares on report": malwares_on_report,
                        "chunk": text_chunk,
                        "mentioned_entities": mentioned_entities
                    },
                    ensure_ascii=False
                ),
            },
        ]

        # --- 4) PREP & GENERATION ---
        chat_text = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = self._tokenizer([chat_text], return_tensors="pt").to(self._model.device)

        generated_ids = self._model.generate(
            **inputs,
            max_new_tokens=360,
            do_sample=True,
            no_repeat_ngram_size=16,
            eos_token_id=self._tokenizer.eos_token_id,
        )
        output_ids = generated_ids[0][len(inputs.input_ids[0]):]
        content = self._tokenizer.decode(output_ids, skip_special_tokens=True).strip()
        
        #print("------------------")
        #print(text_chunk)
        #print("------------------")
        #print(content)
        #print("------------------")

        triples = []
        for line in content.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 3:
                parts = self._clear_result(parts)
                triples.append(tuple(parts))

        return triples

