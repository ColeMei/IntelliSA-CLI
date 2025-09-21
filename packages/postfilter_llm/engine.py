
"""Encoder post-filter loader/predictor facade."""
from __future__ import annotations

import hashlib
import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from packages.schema.models import Detection, Prediction

_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "models" / "registry.yaml"
_DEFAULT_CACHE = Path(os.environ.get("IACSEC_MODEL_CACHE", str(Path.home() / ".cache/iacsec")))
_LOADED_MODEL: Optional["ModelHandle"] = None


@dataclass(frozen=True)
class ModelHandle:
    """Metadata describing a loaded encoder model."""

    name: str
    version: str
    path: Path
    framework: str
    default_threshold: float
    labels: List[str]

    def as_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "version": self.version,
            "path": str(self.path),
            "framework": self.framework,
        }


def load_model(name: str) -> ModelHandle:
    """Resolve and cache the requested model, returning a handle."""

    registry = _load_registry()
    if name not in registry:
        raise KeyError(f"Model '{name}' not found in registry at {_REGISTRY_PATH}")

    entry = registry[name]
    uri = entry["uri"]
    target_path = _target_path(entry)
    expected_sha = entry.get("sha256")
    should_verify = _is_hex_digest(expected_sha)

    if not target_path.exists() or (should_verify and not _verify_sha(target_path, expected_sha)):  # type: ignore[arg-type]
        _download_file(uri, target_path)
        if should_verify and not _verify_sha(target_path, expected_sha):  # type: ignore[arg-type]
            raise RuntimeError(
                f"Checksum mismatch for model '{name}' after download."
            )

    handle = ModelHandle(
        name=name,
        version=str(entry.get("version", "0")),
        path=target_path,
        framework=str(entry.get("framework", "unknown")),
        default_threshold=float(entry.get("default_threshold", 0.5)),
        labels=list(entry.get("labels", [])),
    )

    global _LOADED_MODEL
    _LOADED_MODEL = handle
    return handle


def predict(
    detections: List[Detection],
    code_dir: Path,
    threshold: Optional[float],
) -> List[Prediction]:
    """Produce deterministic predictions for detections."""

    if _LOADED_MODEL is None:
        raise RuntimeError("No model loaded. Call load_model() before predict().")

    model = _LOADED_MODEL
    effective_threshold = threshold if threshold is not None else model.default_threshold

    predictions: List[Prediction] = []
    for det in detections:
        score = _stable_score(det, code_dir, model)
        label = "TP" if score >= effective_threshold else "FP"
        rationale = "score>=threshold" if label == "TP" else "score<threshold"
        predictions.append(
            Prediction(label=label, score=score, rationale=rationale)
        )
    return predictions


def _stable_score(det: Detection, code_dir: Path, model: ModelHandle) -> float:
    payload = json.dumps(
        {
            "model": model.name,
            "version": model.version,
            "rule": det.rule_id,
            "file": det.file,
            "snippet": det.snippet,
            "code_dir": str(code_dir),
        },
        sort_keys=True,
    ).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    value = int.from_bytes(digest[:8], "big")
    return value / float(1 << 64)


def _load_registry() -> Dict[str, Dict[str, object]]:
    if not _REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Registry file missing: {_REGISTRY_PATH}")
    data = yaml.safe_load(_REGISTRY_PATH.read_text()) or {}
    entries: Dict[str, Dict[str, object]] = {}
    for entry in data.get("models", []):
        entries[entry["name"]] = entry
    return entries


def _cache_dir() -> Path:
    override = os.environ.get("IACSEC_MODEL_CACHE")
    if override:
        path = Path(override)
    else:
        path = _DEFAULT_CACHE
    path.mkdir(parents=True, exist_ok=True)
    return path


def _target_path(entry: Dict[str, object]) -> Path:
    cache_dir = _cache_dir()
    uri = str(entry["uri"])
    name = entry["name"]
    version = str(entry.get("version", "0"))
    parsed = urllib.parse.urlparse(uri)
    filename = Path(parsed.path).name or f"{name}-{version}.bin"
    return cache_dir / filename


def _download_file(uri: str, target_path: Path) -> None:
    parsed = urllib.parse.urlparse(uri)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if parsed.scheme in {"", "file"}:
        source_path = Path(parsed.path)
        if not source_path.exists():
            raise FileNotFoundError(f"Model source file not found: {source_path}")
        target_path.write_bytes(source_path.read_bytes())
        return

    try:
        with urllib.request.urlopen(uri) as response:  # nosec - trusted sources configured in registry
            data = response.read()
    except Exception as exc:  # pragma: no cover - network/IO errors
        raise RuntimeError(f"Failed to download model from {uri}: {exc}") from exc

    target_path.write_bytes(data)


def _verify_sha(path: Path, expected: str) -> bool:
    if not path.exists():
        return False
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest() == expected


def _is_hex_digest(value: Optional[str]) -> bool:
    if not value or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


__all__ = ["ModelHandle", "load_model", "predict"]
