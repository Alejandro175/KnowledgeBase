from typing import List, Tuple
from owlready2 import *
import time
from difflib import SequenceMatcher

class TriplesValidator:
    def __init__(self, ontology_path: str, output_dir: str = "output"):
        self._ontology_path = ontology_path
        self._output_dir = output_dir
        self._ontology = self._load_ontology()

    def _load_ontology(self):
        print("Aggiornamento ontology")
        self._ontology = get_ontology(self._ontology_path).load()

    def _get_class(self, name: str):
        return self._ontology[name]

    def _get_property(self, name: str):
        return self._ontology[name]

    def _save_knowledge(self, input_name: str) -> str:
        # Genera un timestamp corrente e un numero casuale
        timestamp = int(time.time())  # otteniamo il timestamp come intero
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
                # Se ci fossero Union/Restriction servirebbe gestione ad hoc
                pass
        return False

    def _verify_relation(self, subject_class: str, object_class: str, prop) -> bool:
        """
        Verifica: subject_class ∈ domain(prop) e object_class ∈ range(prop),
        considerando le sottoclassi.
        """
        if prop is None:
            print(f"[prop-missing] {prop}")
            return False

        subj_cls = self._get_class(subject_class)
        obj_cls  = self._get_class(object_class)
        if subj_cls is None or obj_cls is None:
            print(f"[class-missing] subj={subject_class} obj={object_class}")
            return False

        # Usa direttamente le CLASSI, non i nomi
        domains = list(getattr(prop, "domain", []))  # List[ThingClass]
        ranges  = list(getattr(prop, "range",  []))  # List[ThingClass]

        # Se domain/range sono vuoti li trattiamo come wildcard (OK)
        domain_ok = True if not domains else self._matches_any_super(subj_cls, domains)
        range_ok  = True if not ranges  else self._matches_any_super(obj_cls,  ranges)

        print(f"[verify] prop={prop.name} subj={subject_class}∈{[c.name for c in domains]}? {domain_ok} | "f"obj={object_class}∈{[c.name for c in ranges]}? {range_ok}")

        return domain_ok and range_ok

    def _add_triple(self, subj_name: str, subj_class: str, relation: str, obj_name: str, obj_class: str) -> bool:
        with self._ontology:
            subject_cls = self._get_class(subj_class)
            object_cls  = self._get_class(obj_class)
            prop        = self._get_property(relation)

            print(f"\n({subj_name}, {subject_cls}) --{relation}--> ({obj_name}, {object_cls})")

            if not (subject_cls and object_cls and prop):
                print("[skip] missing subject/object class or property")
                return False

            if not self._verify_relation(subj_class, obj_class, prop):
                print("[skip] domain/range mismatch")
                return False

            # Crea / riusa individui (qui semplice: crea nuovi con quegli IRI)
            subj_ind = subject_cls(subj_name)
            if isinstance(prop, ObjectPropertyClass):
                obj_ind = object_cls(obj_name)
                getattr(subj_ind, prop.name).append(obj_ind)
            elif isinstance(prop, DataPropertyClass):
                getattr(subj_ind, prop.name).append(obj_name)  # literal
            else:
                #print(f"[skip] unsupported property type: {type(prop)}")
                return False

            #print("Relazione creata.")
            return True

    def run(
        self,
        triples: List[List[Tuple[str, str, str]]],            # [(subject, relation, object)]
        entities_class: List[List[Tuple[str, str, float]]],   # [(classe, text, score)]
        source_name: str
    ) -> List[Tuple[str, str, str]]:
        
        self._load_ontology()

        text2class: dict[str, str] = {}
        hash_codes = []
        for cls_list in entities_class:
            for classe, text, _ in cls_list:

                if classe == "Hash":
                    hash_codes.append(text)
                    continue

                key = text
                if key and key not in text2class:   # first-write-wins (puoi togliere il check se vuoi last-write-wins)
                    text2class[key] = classe

        #print("PRINT global text2class:\n", text2class)
        #print("------NEXT-----")

        # 2) Usa la mappa globale per processare tutte le triple (su tutti i chunk)
        for entity_list in triples:
            for subject, relation, obj in entity_list:
                subj_key = subject
                obj_key  = obj

                if subj_key in text2class and obj_key in text2class:
                    self._add_triple(subject, text2class[subj_key], relation, obj, text2class[obj_key])
                elif subj_key in text2class and (obj_s := self._search_hash(obj_key, hash_codes)) is not None:
                    self._add_triple(subject, text2class[subj_key], relation, obj_s, "Hash")
                else:
                    # log minimale per capire cosa manca
                    if subj_key not in text2class:
                        print(f"[MISS] subject non trovato in text2class: '{subject}'")
                    if obj_key not in text2class:
                        print(f"[MISS] object non trovato in text2class: '{obj}'")

        return self._save_knowledge(source_name)
    
if __name__ == "__main__":
    triples = [[('onionduke', 'hasTargetSoftware', 'tor-network'), ('onionduke', 'hasTargetSoftware', 'windows-executables'), ('onionduke', 'hasLocation', 'russia'), ('onionduke', 'hasTargetSector', 'european'), ('onionduke', 'isIndicatedBy', 'tor-exit-node'), ('onionduke', 'isMember', 'miniduke')], [('onionduke', 'hasTargetSoftware', 'executable'), ('onionduke', 'hasTargetSoftware', 'binary'), ('onionduke', 'hasTargetSoftware', 'wrapper'), ('onionduke', 'hasTargetSoftware', 'pe-resource'), ('onionduke', 'hasTargetSoftware', 'gif-image-file'), ('onionduke', 'hasTargetSoftware', 'dll'), ('onionduke', 'execute', 'execute'), ('onionduke', 'execute', 'decrypt'), ('onionduke', 'hasAbility', 'execution'), ('onionduke', 'hasAbility', 'encrypted'), ('onionduke', 'isIndicatedBy', 'a75995f94854dea87980b71199d2'), ('onionduke', 'isMember', 'trojan-dropper:w32/onionduke.a'), ('onionduke', 'isMember', 'dropper'), ('onionduke', 'hasLocation', 'tor-exit-node')], [('onionduke', 'hasTargetSoftware', 'dll-file'), ('onionduke', 'hasTargetSoftware', 'file'), ('onionduke', 'hasAbility', 'decrypt'), ('onionduke', 'hasAbility', 'download'), ('onionduke', 'hasAbility', 'execute'), ('onionduke', 'execute', 'attackpattern'), ('onionduke', 'isIndicatedBy', 'b491c14d8cfb48636-f6095b7b16555e9a-575d57f'), ('onionduke', 'hasTargetInformation', 'configuration'), ('onionduke', 'hasTargetInformation', 'configuration-data'), ('onionduke', 'compromise', 'system'), ('onionduke', 'isMember', 'backdoor:w32/onionduke.b')], [('onionduke', 'hasTargetInformation', 'login-credentials'), ('onionduke', 'hasTargetInformation', 'victim-machine'), ('onionduke', 'hasTargetInformation', 'compromised-system'), ('onionduke', 'hasTargetSoftware', 'antivirus-software'), ('onionduke', 'hasAbility', 'gathering'), ('onionduke', 'hasAbility', 'downloaded'), ('onionduke', 'hasAbility', 'executed'), ('onionduke', 'controledBy', 'backdoor-process'), ('onionduke', 'execute', 'backdoor-process'), ('onionduke', 'hasTargetInformation', 'firewall'), ('onionduke', 'hasTargetSector', 'components'), ('onionduke', 'isMember', 'onionduke-malware-family')], [('onionduke', 'hasTargetSoftware', 'dll-file'), ('onionduke', 'hasTargetSoftware', 'w32/onionduke.a'), ('onionduke', 'hasTargetSoftware', 'w32/onionduке.b'), ('onionduke', 'hasTargetInformation', 'overpict.com'), ('onionduke', 'isIndicatedBy', 'sha1-d433f281cf56016941a1c2cb87066ca61ea1db37'), ('onionduke', 'execute', 'attackpattern'), ('onionduke', 'hasLocation', 'infrastructure'), ('onionduke', 'isMember', 'miniduke'), ('onionduke', 'isIndicatedBy', 'airtravelabroad.com'), ('onionduke', 'isIndicatedBy', 'beijingnewsblog.net'), ('onionduke', 'isIndicatedBy', 'grouptumbler.com'), ('onionduke', 'isIndicatedBy', 'leveldelta.com'), ('onionduke', 'isIndicatedBy', 'nasdaqblog.net'), ('onionduke', 'isIndicatedBy', 'natureinhome.com'), ('onionduke', 'isIndicatedBy', 'nestedmail.com'), ('onionduke', 'isIndicatedBy', 'nostressjob.com'), ('onionduke', 'isIndicatedBy', 'nytunion.com'), ('onionduke', 'isIndicatedBy', 'oilnewsblog.com'), ('onionduke', 'isIndicatedBy', 'sixsquare.net'), ('onionduke', 'isIndicatedBy', 'ustradecomp.com'), ('onionduke', 'isIndicatedBy', 'twitter')], [('onionduke', 'hasTargetSoftware', 'executables'), ('onionduke', 'hasTargetSoftware', 'torrent-files'), ('onionduke', 'hasTargetInformation', 'configuration-data'), ('onionduke', 'hasTargetSoftware', 'pirated-software')], [('onionduke', 'hasTargetSector', 'european'), ('onionduke', 'execute', 'shooting-a-fly-with-a-cannon'), ('onionduke', 'execute', 'surgical-targeting'), ('onionduke', 'hasTargetSoftware', 'tor'), ('onionduke', 'hasLocation', 'region'), ('onionduke', 'isIndicatedBy', 'samples'), ('onionduke', 'isIndicatedBy', 'tor-exit-nodes'), ('onionduke', 'hasAbility', 'encrypt'), ('onionduke', 'controledBy', 'tor-network'), ('onionduke', 'hasTargetSoftware', 'binaries'), ('onionduke', 'hasTargetInformation', 'encryption'), ('onionduke', 'hasTargetSoftware', 'vpns'), ('onionduke', 'hasTargetSoftware', 'freedome-vpn')], [('w32/onionduke.a', 'hasAbility', 'trojan-dropper'), ('w32/onionduke.a', 'hasAbility', 'backdoor'), ('w32/onionduke.b', 'hasAbility', 'backdoor'), ('w32/onionduke.a', 'isIndicatedBy', 'a75995f94854dea879650a2f4a97980b1199d2'), ('w32/onionduke.b', 'isIndicatedBy', 'b491c14d8cfb48636d6095b7b16555e9a175d57f'), ('w32/onionduke.b', 'isIndicatedBy', 'd433f281cf5601594d1a1c2cb87066ca62ea3db37')]]
    entities_class = [[('Malware', 'onionduke', 0.991958498954773), ('System', 'tor-network', 0.9768484830856323), ('URL', 'tor-exit-node', 0.9015107750892639), ('Country', 'russia', 0.9975786805152893), ('File', 'windows-executables', 0.9240490794181824), ('MalwareCategory', 'miniduke', 0.9705886244773865), ('Region', 'european', 0.7025644183158875), ('MalwareCategory', 'malware', 0.6563969850540161)], [('Information', 'user', 0.9833336472511292), ('File', 'executable', 0.966616153717041), ('URL', 'tor-exit-node', 0.8597360253334045), ('File', 'binary', 0.6938443183898926), ('Capability', 'execution', 0.9173249006271362), ('File', 'wrapper', 0.6190620064735413), ('Capability', 'execute', 0.8973701596260071), ('Hash', 'sha1', 0.9821745157241821), ('Hash', 'a75995f94854dea8799650a2f4a97980b71199d2', 0.9340935945510864), ('MalwareCategory', 'trojan-dropper:w32/onionduke.a', 0.7805216312408447), ('File', 'pe-resource', 0.7418766021728516), ('File', 'gif-image-file', 0.6965330243110657), ('Capability', 'encrypted', 0.7779703736305237), ('MalwareCategory', 'dropper', 0.5910753607749939), ('Capability', 'decrypt', 0.9426678419113159), ('File', 'dll', 0.7464938163757324)], [('Capability', 'executed', 0.8957465291023254), ('File', 'dll-file', 0.9655387997627258), ('Hash', 'sha1', 0.994620680809021), ('Hash', 'b491c14d8cfb48636f6095b7b16555e9a575d57f', 0.9778956770896912), ('MalwareCategory', 'backdoor:w32/onionduke.b', 0.8035537004470825), ('Capability', 'decrypt', 0.983073890209198), ('Information', 'configuration', 0.6623179316520691), ('URL', 'c&c-urls', 0.8688616156578064), ('Information', 'configuration-data', 0.8264501094818115), ('System', 'c&cs', 0.5914907455444336), ('MalwareCategory', 'malware', 0.7060694694519043), ('Capability', 'download', 0.5551028251647949), ('Capability', 'execute', 0.8466147184371948)], [('MalwareCategory', 'components', 0.8808639049530029), ('MalwareCategory', 'onionduke-malware-family', 0.9915969967842102), ('Information', 'login-credentials', 0.942865252494812), ('Information', 'victim-machine', 0.6366295218467712), ('Capability', 'gathering', 0.6523578763008118), ('Information', 'compromised-system', 0.8472679853439331), ('Software', 'antivirus-software', 0.9748036861419678), ('Information', 'firewall', 0.7565284371376038), ('Capability', 'downloaded', 0.7438287138938904), ('Capability', 'executed', 0.8226240873336792), ('Capability', 'backdoor-process', 0.7476003170013428), ('Information', 'infection-vector', 0.5543012619018555), ('System', 'c&c', 0.6549661755561829), ('Capability', 'backdoor-process', 0.7476003170013428)], [('File', 'dll-file', 0.9737333059310913), ('Hash', 'sha1-d433f281cf56015941a1c2cb87066ca62ea1db37', 0.9826861619949341), ('Malware', 'onionduke', 0.991958498954773), ('URL', 'overpict.com', 0.946062445640564), ('URL', 'twitter', 0.83980792760849), ('Year', '2011', 0.86692875623703), ('URL', 'airtravelabroad.com', 0.8853099942207336), ('URL', 'beijingnewsblog.net', 0.877036988735199), ('URL', 'grouptumbler.com', 0.9511059522628784), ('URL', 'leveldelta.com', 0.9058969020843506), ('URL', 'nasdaqblog.net', 0.6453448534011841), ('URL', 'natureinhome.com', 0.7731621265411377), ('URL', 'nestedmail.com', 0.6649129390716553), ('URL', 'nostressjob.com', 0.8618592619895935), ('URL', 'nytunion.com', 0.9113917350769043), ('URL', 'oilnewsblog.com', 0.9493889212608337), ('URL', 'sixsquare.net', 0.9290627837181091), ('URL', 'ustradecomp.com', 0.9560861587524414), ('MalwareCategory', 'miniduke', 0.949371337890625), ('System', 'infrastructure', 0.7445005774497986)], [('Malware', 'onionduke', 0.991958498954773), ('File', 'executables', 0.9689855575561523), ('File', 'torrent-files', 0.8644219040870667), ('Software', 'pirated-software', 0.9246464371681213), ('Information', 'configuration-data', 0.780005931854248)], [('Malware', 'onionduke', 0.9641059637069702), ('Region', 'european', 0.888272762298584), ('File', 'binaries', 0.9170202612876892), ('Software', 'tor', 0.8838422894477844), ('Capability', 'encryption', 0.9677538871765137), ('URL', 'exit-node', 0.8796958327293396), ('Software', 'vpns', 0.629795253276825), ('System', 'freedome-vpn', 0.5667175650596619), ('Capability', 'encrypt', 0.9179555177688599), ('System', 'tor-network', 0.969548225402832), ('URL', 'tor-exit-nodes', 0.8967087268829346), ('File', 'samples', 0.8792203664779663)], [('Hash', 'a75995f94854dea8799650a2f4a97980b71199d2', 0.9375011324882507), ('Hash', 'b491c14d8cfb48636f6095b7b16555e9a575d57f', 0.9304121732711792), ('Hash', 'd433f281cf56015941a1c2cb87066ca62ea1db37', 0.868133544921875), ('MalwareCategory', 'trojan-dropper', 0.9615379571914673), ('Malware', 'w32/onionduke.a', 0.8747348785400391), ('MalwareCategory', 'backdoor', 0.9871166348457336), ('Malware', 'w32/onionduke.b', 0.7628850936889648)]]
    source_name = "test"

    ValidationStage = TriplesValidator(ontology_path="ontology/malwareOntology.rdf", output_dir="output")
    ValidationStage.run(triples, entities_class, source_name)