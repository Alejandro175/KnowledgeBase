from dataclasses import dataclass
from typing import List

@dataclass
class Entity:
    label: str
    text: str
    score: float

@dataclass
class ChuckEntities:
    entities: List[Entity]

@dataclass
class Triple:
    subject: str
    predicate: str
    object: str

