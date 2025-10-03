import os
from pathlib import Path
from typing import Tuple, List
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch, json

MODELS_DIR = Path(os.getenv("HF_HUB_CACHE"))

# --- 1) CONTEXT (una sola volta, nel role=system) ---
context = """
You are an LLM that extracts factual triples from English cybersecurity reports about an specific malware.

TASK
- Map entities mentioned in the input "chunk" or provided in "mentioned_entities" to the allowed relations and output factual triples.

STRICT OUTPUT
- Output triples strictly in this format (one per line): <subject text>,<relation>,<object text>
- No extra text, no commentary, no JSON, no bullet points.
- No duplicate lines. No leading/trailing spaces around commas.

ALLOWED RELATIONS (subject class, relation, object class)
- Malware,hasTargetSoftware,Software
- Malware,execute,AttackPattern
- Malware,ComunicateWith,System
- Malware,compromise,System
- Malware,hasLocation,Country
- Malware,hasLocation,Region
- Malware,hasTargetInformation,Information
- Malware,hasTargetSector,Sector
- Malware,isIndicatedBy,Email
- Malware,isIndicatedBy,File
- Malware,isIndicatedBy,Hash
- Malware,isIndicatedBy,URL
- Malware,isIndicatedBy,Address
- Malware,isRelateTo,Category
- Malware,hasCharacteristic,Capability

MAPPING RULES (CRITICAL)
1) Subjects and objects MUST be concrete strings from the chunk or from mentioned_entities. NEVER output generic class names (e.g., "Information", "Software", "Sector", "Country", "Region", "AttackPattern", "URL", "File", "Hash", "Address", "Infrastructure").
2) Subject MUST be the concrete malware name from the chunk or mentioned_entities (type == "Malware"). If none is present, output nothing.
4) ALWAYS emit isIndicatedBy triples for each URL, Email, IP Address present in the chunk or in mentioned_entities.
5) For File and Hash, only emit if an explicit concrete string is present (e.g., a filename, hash value); do not generalize.
6) Write the hash codes exactly as they are.

VALIDATION CHECKLIST (apply before output)
- Each line matches: <subject text>,<relation>,<object text>
- Subject/object are concrete strings (not class names).
- Relation is one of the allowed ones.
- Remove duplicates (exact string equality across the whole line).

INPUT FORMAT
You will receive a JSON with:
{
  "chunk": "<string>",
  "mentioned_entities": [
    {"type": "<ClassName>", "text": "<verbatim string>"}
    ...
  ]
}

OUTPUT FORMAT
One triple per line:
<subject text>,<relation>,<object text>

MINI-EXAMPLES
Given:
chunk: "OnionDuke communicates via the Tor network and was seen in Russia. Indicators include https://abc.example/onion and 185.21.15.3."
mentioned_entities: [
  {"type":"Malware","text":"OnionDuke"},
  {"type":"Infrastructure","text":"tor-network"},
  {"type":"Country","text":"Russia"}
]

Valid output:
onionduke,communicateWith,c&c-server
cloud-atlas,isIndicatedBy,bicorporate.dll
cloud-atlas,isIndicatedBy,Car-for-sale.doc
onionduke,hasLocation,Russia
onionduke,isIndicatedBy,https://abc.example/onion
onionduke,isIndicatedBy,185.21.15.3
"""

class RelationExtractorLLM:
    def __init__(self, model_id: str = "Qwen/Qwen3-4B-Instruct-2507-FP8"): 
        cache_folder_name = "models--" + model_id.replace("/", "--")
        model_cache_path = MODELS_DIR / cache_folder_name
        use_cache = model_cache_path.exists()

        print(f"LLM model Load from cache: {use_cache}")

        self._tokenizer = AutoTokenizer.from_pretrained(model_id, local_files_only=use_cache)
        self._model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype="auto",
            device_map="auto",
            local_files_only = use_cache
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
        
        print("------------------")
        print(text_chunk)
        print("------------------")
        print(content)
        print("------------------")

        triples = []
        for line in content.splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 3:
                parts = self._clear_result(parts)
                triples.append(tuple(parts))

        for a in malwares_on_report:
            for b in malwares_on_report:
                if a != b:
                    triples.append(tuple((a[1], "mentionedWith", b[1])))

        return triples

