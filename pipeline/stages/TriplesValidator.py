from typing import List, Tuple
from owlready2 import *
import time
from difflib import SequenceMatcher

class TriplesValidator:
    def __init__(self, ontology_path: str, output_dir: str = "output"):
        self._ontology_path = ontology_path
        self._output_dir = output_dir
        self._ontology = get_ontology(self._ontology_path).load()

    def _get_class(self, class_name: str):
        cls = self._ontology[class_name]
        if cls == None:
            cls = self._ontology.search_one(label=class_name)
        return cls
    
    def _get_property(self, prop_name: str):
        prop = self._ontology[prop_name]
        if prop == None:
            prop = self._ontology.search_one(label=prop_name)
        return prop
    
    def _save_knowledge(self, input_name: str) -> str:
        timestamp = int(time.time())
        input_name = input_name.split(".", 1)[0]
        
        file_name = f"{input_name}_{timestamp}.rdf"
        rdf_output = f"{self._output_dir}/{file_name}"
        
        self._ontology.save(file=rdf_output, format="rdfxml")
        return rdf_output
    
    @staticmethod
    def _search_hash(string ,hash_codes):
        for h in hash_codes:
            similarity = SequenceMatcher(None, h, string).ratio()
            if similarity > 0.85:
                return h
            else:
                return None

    @staticmethod
    def _matches_any_super(actual_cls, candidates) -> bool:
        """True se actual_cls è sottoclasse (o uguale) di almeno uno dei candidates."""
        for cand in candidates:
            try:
                if issubclass(actual_cls, cand):
                    return True
            except TypeError:
                pass
        return False

    def _verify_relation(self, subject_class: ThingClass, object_class: ThingClass, prop: PropertyClass) -> bool:
        """
        Verifica: subject_class ∈ domain(prop) e object_class ∈ range(prop),
        considerando le sottoclassi.
        """
        domains = list(getattr(prop, "domain", []))
        ranges  = list(getattr(prop, "range",  []))  

        domain_ok = True if not domains else self._matches_any_super(subject_class, domains)
        range_ok  = True if not ranges  else self._matches_any_super(object_class,  ranges)

        #print(f"[verify] prop={prop.name} subj={subject_class}∈{[c.name for c in domains]}? {domain_ok} | "f"obj={object_class}∈{[c.name for c in ranges]}? {range_ok}")

        return domain_ok and range_ok

    def _add_triple(self, subj_name: str, subj_class: str, relation: str, obj_name: str, obj_class: str) -> bool:
        with self._ontology:
            subject_cls = self._get_class(subj_class)
            object_cls  = self._get_class(obj_class)
            prop        = self._get_property(relation)

            #print(f"\n({subj_name}) --{prop}--> ({obj_name})")

            if subject_cls is None or object_cls is None or prop is None:
                #print("[skip] subject, object or property not found in ontology")
                return False

            if not self._verify_relation(subject_cls, object_cls, prop):
                #print("[skip] domain/range mismatch")
                return False

            try:
                #print("Creazione individui e tripla...")
                subj_ind = subject_cls(subj_name)
                obj_ind = object_cls(obj_name)
                prop[subj_ind].append(obj_ind)
                
                #print("Tripla aggiunta con successo")
                print(f"\n({subj_name}) --{prop}--> ({obj_name})")
                return True
                
            except Exception as e:
                print(f"[ERROR] {e}")
                return False

    def run(
        self,
        triples: List[List[Tuple[str, str, str]]],            
        entities_class: List[List[Tuple[str, str, float]]],
        source_name: str
    ) -> List[Tuple[str, str, str]]:

        print(entities_class)

        text2class: dict[str, str] = {}
        hash_codes = []
        malwares_on_report = []

        for cls_list in entities_class:
            for classe, text, _ in cls_list:

                if classe == "Malware":
                    malwares_on_report.append((classe, text))

                if classe == "Hash":
                    hash_codes.append(text)
                    continue

                key = text
                if key and key not in text2class:   # first-write-wins (puoi togliere il check se vuoi last-write-wins)
                    text2class[key] = classe

        #print("PRINT global text2class:\n", text2class)
        #print("------NEXT-----")

        for entity_list in triples:
            for subject, relation, obj in entity_list:
                subj_key = subject
                obj_key  = obj

                #print(f"\nProcessing triple: ({subject}, {relation}, {obj})")

                if subj_key in text2class and obj_key in text2class:
                    self._add_triple(subject, text2class[subj_key], relation, obj, text2class[obj_key])
                elif subj_key in text2class and (obj_s := self._search_hash(obj_key, hash_codes)) is not None:
                    self._add_triple(subject, text2class[subj_key], relation, obj_s, "Hash")
                else:
                    #print("[skip] subject or object not found in recognized entities")
                    continue

        # Meta dati
        print("Aggiunta metadati...")
        for a in malwares_on_report:
            self._add_triple(a[1], a[0], "mentionedIn", source_name, "Report") 
            for b in malwares_on_report:
                if a != b:
                    self._add_triple(a[1], a[0], "mentionedWith", b[1], b[0])


        print("Reasoning...")
        with self._ontology:
            sync_reasoner_pellet(
                infer_property_values=True,
                infer_data_property_values=True
            )

        print("Salvataggio...")
        return self._save_knowledge(source_name)
    
if __name__ == "__main__":
    entities_class = [[('Malware', 'scanbox', 0.9930236339569092), ('AttackPattern', 'watering-hole-attacks', 0.981590211391449), ('URL', 'website', 0.8065504431724548), ('Organization', 'automotive', 0.9798633456230164), ('Organization', 'aerospace', 0.9489216804504395), ('Organization', 'manufacturing', 0.9767629504203796), ('Capability', 'loaded', 0.6699537634849548), ('File', 'malicious-javascript-file', 0.938480794429779), ('System', 'remote-server', 0.5292147994041443), ('File', 'javascript-file', 0.9384846091270447), ('Software', 'internet-explorer', 0.6799774765968323), ('Characteristic', 'remote-c&c-server', 0.9186524748802185), ('Capability', 'collects', 0.7461373805999756), ('Information', 'referer', 0.8898673057556152), ('Information', 'user-agent', 0.9701116681098938), ('Information', 'location', 0.887179434299469), ('Information', 'cookie', 0.9371137022972107), ('URL', 'domain', 0.8392328023910522), ('Information', 'title', 0.749782383441925), ('URL', 'charset', 0.8175863027572632), ('URL', 'screen-width-and-height', 0.675495982170105), ('Information', 'operating-system-version', 0.7300172448158264), ('URL', 'system-language', 0.8263967633247375)], [('Characteristic', 'c&c-server', 0.9733278751373291), ('Malware', 'scanbox', 0.9930236339569092), ('Capability', 'encodes', 0.5382857918739319), ('Capability', 'encrypts', 0.6495363712310791), ('AttackPattern', 'technique', 0.7282950282096863), ('Software', 'internet-explorer', 0.9321700930595398), ('Software', 'emet', 0.9170752167701721), ('Software', 'enhanced-mitigation-experience-toolkit', 0.6560320258140564), ('Software', 'adobe-flash', 0.905767560005188), ('Software', 'microsoft-office', 0.9340399503707886), ('Software', 'acrobat-reader', 0.9287134408950806), ('Software', 'java', 0.920791745185852), ('Software', 'javascript', 0.8119027614593506), ('Information', 'keystrokes', 0.6519771814346313), ('URL', 'website', 0.8957082629203796), ('Characteristic', 'c&c', 0.8248330950737), ('Information', 'passwords', 0.9430630207061768), ('Information', 'sensitive-data', 0.8025427460670471)], [('AttackPattern', 'attacks', 0.5646841526031494), ('Capability', 'exploits', 0.5965677499771118), ('Software', 'java', 0.8909133672714233), ('IPAddress', 'ip-IPAddress', 0.7472822666168213), ('Malware', 'scanbox', 0.8164663314819336), ('IPAddress', '122.10.9.109', 0.98480623960495), ('System', 'network', 0.9421935081481934), ('EmailAddress', 'mail.webmailgoogle.com', 0.9600834250450134), ('URL', 'js.webmailgoogle.com', 0.6851183772087097)]] 
    triples = [[('scanbox', 'execute', 'watering-hole-attacks'), ('scanbox', 'hasCharacteristic', 'remote-c&c-server'), ('scanbox', 'targetInformation', 'referer'), ('scanbox', 'targetInformation', 'user-agent'), ('scanbox', 'targetInformation', 'location'), ('scanbox', 'targetInformation', 'cookie'), ('scanbox', 'targetInformation', 'domain'), ('scanbox', 'targetInformation', 'title'), ('scanbox', 'targetInformation', 'charset'), ('scanbox', 'targetInformation', 'screen-width-and-height'), ('scanbox', 'targetInformation', 'operating-system-version'), ('scanbox', 'targetInformation', 'system-language'), ('scanbox', 'isIndicatedByFile', 'malicious-javascript-file'), ('scanbox', 'isIndicatedByFile', 'javascript-file')], [('scanbox', 'hasCharacteristic', 'c&c-server'), ('scanbox', 'hasCharacteristic', 'c&c'), ('scanbox', 'hasCharacteristic', 'encodes'), ('scanbox', 'hasCharacteristic', 'encrypts'), ('scanbox', 'hasCharacteristic', 'javascript'), ('scanbox', 'targetSoftware', 'internet-explorer'), ('scanbox', 'targetSoftware', 'emet'), ('scanbox', 'targetSoftware', 'enhanced-mitigation-experience-toolkit'), ('scanbox', 'targetSoftware', 'adobe-flash'), ('scanbox', 'targetSoftware', 'microsoft-office'), ('scanbox', 'targetSoftware', 'acrobat-reader'), ('scanbox', 'targetInformation', 'keystrokes'), ('scanbox', 'targetInformation', 'passwords'), ('scanbox', 'targetInformation', 'sensitive-data'), ('scanbox', 'execute', 'technique')], [('scanbox', 'execute', 'attacks'), ('scanbox', 'hasCharacteristic', 'exploits'), ('scanbox', 'targetSoftware', 'java'), ('scanbox', 'isIndicatedByAddress', '122.10.9.109'), ('scanbox', 'isIndicatedByUrl', 'js.webmailgoogle.com'), ('scanbox', 'isIndicatedByEmail', 'mail.webmailgoogle.com')]]
    source_name = "test"
    
    ValidationStage = TriplesValidator(ontology_path="ontology/malwareOntologyV2.rdf", output_dir="output")

    ValidationStage.run(triples=triples, entities_class=entities_class, source_name=source_name)