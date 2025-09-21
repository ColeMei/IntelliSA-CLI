# Minimal SARIF scaffold. Return a dict but do not fully map yet.
from typing import List, Dict, Any
from packages.schema.models import Detection, Prediction


def to_sarif(detections: List[Detection], predictions: List[Prediction]) -> Dict[str, Any]:
    """
    Build a SARIF v2.1.0 structure (placeholder).
    TODO: Implement proper rules, results, locations, and levels mapping.
    """
    _ = (detections, predictions)  # silence unused for now
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {"driver": {"name": "iacsec (pilot)", "version": "0.0.0"}},
                "results": [],
            }
        ],
    }
