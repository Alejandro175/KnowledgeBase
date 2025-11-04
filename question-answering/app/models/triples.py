import re
from typing import Optional
from pydantic import BaseModel

class Entity(BaseModel):
    uri: str
    confidence: Optional[float] = None

class Triple(BaseModel):
    subject: Entity
    predicate: str
    object: Entity

    def to_text(self) -> str:
        subj = self.subject.uri.split("/")[-1].replace("-", " ")
        obj = self.object.uri.split("/")[-1].replace("-", " ")
        pred = re.sub(r'(?<!^)(?=[A-Z])', ' ', self.predicate).lower()

        return f"{subj} {pred} {obj}"