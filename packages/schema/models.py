# Contract-only models. Keep names/fields stable.
from typing import Dict, Any, Literal, Optional
from pydantic import BaseModel, Field


Smell = Literal["http", "weak-crypto", "hardcoded-secret", "suspicious-comment"]
Tech = Literal["ansible", "chef", "puppet"]
Severity = Literal["low", "medium", "high"]
Label = Literal["TP", "FP"]


class Detection(BaseModel):
    rule_id: str
    smell: Smell
    tech: Tech
    file: str
    line: int
    snippet: str
    message: str
    severity: Severity
    evidence: Dict[str, Any] = Field(default_factory=dict)


class Prediction(BaseModel):
    label: Label
    score: float
    rationale: Optional[str] = None
