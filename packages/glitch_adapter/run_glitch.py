# Adapter boundary: call vendored GLITCH and normalize to our schema.
from typing import List
from packages.schema.models import Detection


def run_glitch(path: str, tech: str) -> List[Detection]:
    """
    Pilot scaffold:
      - Accepts repo path and tech hint.
      - Returns an empty list for now.
    TODO: invoke packages.glitch_core, parse its outputs, map to Detection.
    """
    _ = (path, tech)
    return []
