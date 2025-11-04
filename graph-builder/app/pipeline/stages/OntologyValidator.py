from typing import List
from app.pipeline.datatypes.data_models import Triple, ChuckEntities
from owlready2 import *
import time
from difflib import SequenceMatcher

class RDFsTriplesValidator:
    def __init__(self, ontology_path: str, output_dir: str = "temp"):
        if not os.path.exists(ontology_path):
            raise ValueError(f"Ontology don't found in: {ontology_path}")

        os.makedirs(output_dir, exist_ok=True)
        self._output_dir = output_dir
        self._ontology = get_ontology(ontology_path).load()

    @staticmethod
    def _search_hash(string, hash_codes):
        for h in hash_codes:
            similarity = SequenceMatcher(None, h, string).ratio()
            if similarity > 0.90:
                return h
            else:
                return None
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

    def _get_class(self, class_name: str):
        individual_class = self._ontology[class_name]
        if individual_class is None:
            individual_class = self._ontology.search_one(label=class_name)
        return individual_class
    
    def _get_property(self, prop_name: str):
        object_property = self._ontology[prop_name]
        if object_property is None:
            object_property = self._ontology.search_one(label=prop_name)
        return object_property
    
    def _save_knowledge(self, input_name: str) -> str:
        timestamp = int(time.time())
        input_name = input_name.split(".", 1)[0]
        
        file_name = f"{input_name}_{timestamp}.rdf"
        rdf_output = f"{self._output_dir}/{file_name}"
        
        self._ontology.save(file=rdf_output, format="rdfxml")
        return rdf_output

    def _verify_relation(self, subject_class: ThingClass, object_class: ThingClass, property_relation: PropertyClass) -> bool:
        """
        Verifica: subject_class ∈ domain(prop) e object_class ∈ range(prop),
        considerando le sottoclassi.
        """
        domains = list(getattr(property_relation, "domain", []))
        ranges  = list(getattr(property_relation, "range", []))

        domain_ok = True if not domains else self._matches_any_super(subject_class, domains)
        range_ok  = True if not ranges  else self._matches_any_super(object_class,  ranges)

        #print(f"[verify] prop={prop.name} subj={subject_class}∈{[c.name for c in domains]}? {domain_ok} | "f"obj={object_class}∈{[c.name for c in ranges]}? {range_ok}")
        return domain_ok and range_ok

    def _add_triple(self, subj_name: str, subj_class: ThingClass, relation, obj_name: str, obj_class: ThingClass) -> bool:
        with self._ontology:
            try:
                #print(f"\n({subj_name}) --{relation}--> ({obj_name})")

                if subj_class is None or obj_class is None or relation is None:
                    print("[skip] subject, object or property not found in ontology")
                    return False

                if not self._verify_relation(subj_class, obj_class, relation):
                    print("[skip] domain/range mismatch")
                    return False

                subj_ind = subj_class(subj_name)
                obj_ind = obj_class(obj_name)
                relation[subj_ind].append(obj_ind)
                #print("Success!")
                return True
                
            except Exception as e:
                print(f"[ERROR during add triple] {e}")
                return False

    def _add_confidence_property(self, individual_name: str, individual_class: ThingClass, value: float) -> bool:
        with self._ontology:
            try:
                individual_target = individual_class(individual_name)
                individual_target.confidence = [float(value)]
                #print("Success DataProperty!")
                return True

            except Exception as e:
                print(f"[ERROR during add data property] {e}")
                return False

    def run(
        self,
        generate_triples: List[Triple],
        entities: List[ChuckEntities],
        source_file_name: str
    ) -> str:

        text2class: dict[str, tuple[str, float]] = {}
        hash_codes = []
        malware_on_report = []

        #print("---------Entities---------")
        #print(entities)

        for chuck_entities in entities:
            for entity_item in chuck_entities.entities:

                if entity_item.label == "Hash":
                    hash_codes.append(entity_item.text)
                    continue

                if entity_item.label == "Malware":
                    malware_on_report.append(entity_item.text)

                key = entity_item.text
                if key and key not in text2class:
                    text2class[key] = (entity_item.label, entity_item.score)

        #print("---------TEXT2CLASS---------:")
        #print(text2class)

        for triple in generate_triples:
            try:
                subj = triple.subject
                obj = triple.object
                relation = triple.predicate

                subject_class_name, subject_confidence = text2class[subj]
                object_class_name, object_confidence = text2class[obj]

                subject_cls = self._get_class(subject_class_name)
                object_cls  = self._get_class(object_class_name)
                predicate_property = self._get_property(relation)


                if object_class_name == "Hash":
                    obj = self._search_hash(obj, hash_codes)

                if subj in text2class and obj in text2class:
                    if self._add_triple(subj, subject_cls, predicate_property, obj, object_cls):
                        self._add_confidence_property(subj, subject_cls, subject_confidence)
                        self._add_confidence_property(obj, object_cls, object_confidence)
                else:
                    print("[skip] subject or object not found in recognized entities")
                    continue
            except Exception as e:
                print(f"[ERROR during triple processing] {e}")
                continue

        # Meta dati
        print("Aggiunta metadati...")

        ReportClass = self._get_class("Report")
        MalwareClass = self._get_class("Malware")
        MentionedIn = self._get_property("mentionedIn")
        MentionedWith = self._get_property("mentionedWith")

        for a in malware_on_report:
            self._add_triple(a, MalwareClass, MentionedIn, source_file_name, ReportClass)
            for b in malware_on_report:
                if a != b:
                    self._add_triple(a, MalwareClass, MentionedWith, b, MalwareClass)

        print("Reasoning...")
        try:
            with self._ontology:
                sync_reasoner_pellet(
                    infer_property_values=True,
                    infer_data_property_values=True
                )
        except Exception as e:
            print(f"[ERROR during sync reasoning] {e}")
            raise Exception("[ERROR during sync reasoning in ontology validation]")
        finally:
            print("Save triples...")
            rdf_file_path = self._save_knowledge(source_file_name)

        return rdf_file_path