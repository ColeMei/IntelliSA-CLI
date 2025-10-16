"""CLI helper to pre-download iacsec model assets."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from packages.postfilter_llm import engine


def fetch_model(name: str) -> int:
    """Download the requested model and verify backend readiness."""

    try:
        handle = engine.load_model(name)
    except Exception as exc:  # pragma: no cover - network/IO errors bubble up
        print(f"[iacsec] Failed to load model '{name}': {exc}", file=sys.stderr)
        return 1

    backend = "stub"
    try:
        artifacts = engine._load_hf_artifacts(handle)  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - optional GPU/Torch failures
        print(
            f"[iacsec] Model '{name}' fetched, but transformers backend failed to load: {exc}",
            file=sys.stderr,
        )
        print(
            "[iacsec] Install a compatible torch/transformers build before running scans.",
            file=sys.stderr,
        )
        return 2

    if artifacts is not None:
        backend = "hf"

    cache_file = handle.path if handle.path.exists() else None
    print(f"[iacsec] Model '{name}' ready (backend={backend}).")
    if cache_file is not None:
        print(f"[iacsec] Cached weights at: {cache_file}")
    if backend != "hf":
        print(
            "[iacsec] Warning: using deterministic stub fallback. Install torch + transformers for full fidelity.",
            file=sys.stderr,
        )
        return 3
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download iacsec model assets")
    parser.add_argument("model", nargs="?", default="IntelliSA-220m", help="Model name from models/registry.yaml")
    args = parser.parse_args(argv)
    return fetch_model(args.model)


if __name__ == "__main__":
    raise SystemExit(main())
