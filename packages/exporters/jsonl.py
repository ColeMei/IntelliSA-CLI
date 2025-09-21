# Simple JSONL writer for debugging pipelines (ok for pilot).
from pathlib import Path
from typing import List
import json

from packages.schema.models import Detection, Prediction


def write_jsonl(
    path: Path,
    detections: List[Detection],
    predictions: List[Prediction],
    threshold: float,
    model_name: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for det, pred in zip(detections, predictions):
            rec = {
                "detection": det.model_dump(),
                "prediction": pred.model_dump(),
                "threshold": threshold,
                "model": model_name,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
