# Post-filter scaffold. Replace stubs with real model loading/inference later.
from pathlib import Path
from typing import List, Optional

from packages.schema.models import Detection, Prediction


class ModelHandle:
    def __init__(self, name: str):
        self.name = name


def load_model(name: str) -> ModelHandle:
    """
    TODO: read models/registry.yaml, resolve URI, cache to ~/.cache/iacsec, verify sha256.
    Pilot returns a lightweight handle only.
    """
    return ModelHandle(name)


def predict(
    detections: List[Detection],
    code_dir: Path,
    threshold: Optional[float],
) -> List[Prediction]:
    """
    TODO: run encoder classifier and threshold.
    Pilot: label everything 'TP' with a neutral score.
    """
    _ = (code_dir, threshold)
    return [Prediction(label="TP", score=0.5, rationale="pilot placeholder") for _ in detections]
