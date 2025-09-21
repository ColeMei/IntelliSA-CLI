
"""Typer CLI entrypoint for iacsec scans."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import typer
from rich.console import Console
from rich.table import Table

from packages.exporters.jsonl import write_jsonl
from packages.exporters.sarif import to_sarif
from packages.glitch_adapter.run_glitch import run_glitch
from packages.postfilter_llm.engine import ModelHandle, load_model, predict
from packages.schema.models import Detection, Prediction

app = typer.Typer(add_completion=False)
console = Console()

_VALID_TECH = {"auto", "ansible", "chef", "puppet"}
_VALID_FORMATS = {"sarif", "json", "table"}
_DEFAULT_RULES = "http,weak-crypto,hardcoded-secret,suspicious-comment"


def _normalize_formats(values: Sequence[str]) -> List[str]:
    if not values:
        return ["sarif"]
    normalized = []
    for value in values:
        fmt = value.lower()
        if fmt not in _VALID_FORMATS:
            raise typer.BadParameter(
                f"Unsupported format '{value}'. Choose from {sorted(_VALID_FORMATS)}"
            )
        if fmt not in normalized:
            normalized.append(fmt)
    return normalized


def _normalize_rules(rules_option: str) -> List[str]:
    return [part.strip() for part in rules_option.split(",") if part.strip()]


@app.command()
def scan(
    path: Path = typer.Option(Path("."), "--path", help="Path to scan"),
    tech: str = typer.Option("auto", "--tech", help="auto|ansible|chef|puppet"),
    rules: str = typer.Option(
        _DEFAULT_RULES,
        "--rules",
        help="Comma-separated rule ids (currently informational)",
    ),
    postfilter: str = typer.Option("codet5p-220m", "--postfilter", help="Post-filter model name"),
    threshold: Optional[float] = typer.Option(None, "--threshold", help="Override model default"),
    format: List[str] = typer.Option(
        ["sarif"], "--format", help="Repeatable option: sarif, json, table"
    ),
    out: Path = typer.Option(Path("artifacts/iacsec.sarif"), "--out", help="Output path for SARIF"),
    fail_on_high: bool = typer.Option(
        False,
        "--fail-on-high",
        help="Treat only high-severity TPs as blocking findings",
    ),
) -> None:
    """Run GLITCH + post-filter pipeline and export findings."""

    if tech not in _VALID_TECH:
        raise typer.BadParameter(
            f"Unsupported tech '{tech}'. Choose from {sorted(_VALID_TECH)}"
        )

    formats = _normalize_formats(format)
    selected_rules = _normalize_rules(rules)
    console.log(
        f"Starting scan: path={path} tech={tech} rules={selected_rules} formats={formats}"
    )

    try:
        raw_detections = run_glitch(str(path), tech)
    except Exception as exc:  # pragma: no cover - defensive logging
        console.print(f"[red]GLITCH execution failed: {exc}[/]")
        raise typer.Exit(code=2) from exc

    category_a: list[Detection] = []
    category_a_preds: list[Prediction] = []
    category_b: list[Detection] = []

    for det in raw_detections:
        needs_postfilter = bool(det.evidence.pop("postfilter", False))
        if needs_postfilter:
            category_b.append(det)
        else:
            category_a.append(det)
            category_a_preds.append(
                Prediction(label="TP", score=1.0, rationale="glitch-accepted")
            )

    console.log(
        "GLITCH returned %s detections (accepted=%s, postfilter=%s)"
        % (len(raw_detections), len(category_a), len(category_b))
    )

    try:
        model = load_model(postfilter)
    except Exception as exc:  # pragma: no cover
        console.print(f"[red]Failed to load model '{postfilter}': {exc}[/]")
        raise typer.Exit(code=2) from exc

    effective_threshold = threshold if threshold is not None else model.default_threshold
    try:
        postfiltered = predict(category_b, path, threshold)
    except Exception as exc:  # pragma: no cover
        console.print(f"[red]Post-filtering failed: {exc}[/]")
        raise typer.Exit(code=2) from exc

    detections = category_a + category_b
    predictions = category_a_preds + postfiltered

    console.log(
        f"Post-filter complete: threshold={effective_threshold:.2f}"
        f" TP={sum(1 for p in predictions if p.label == 'TP')}"
    )

    _export_results(
        detections,
        predictions,
        formats=formats,
        out=out,
        model=model,
        threshold=effective_threshold,
    )

    blocking = _blocking_findings(detections, predictions, fail_on_high)
    if blocking:
        console.print(f"[red]{len(blocking)} blocking finding(s) detected[/]")
        raise typer.Exit(code=1)

    console.print("[green]No blocking findings identified[/]")
    raise typer.Exit(code=0)


def _blocking_findings(
    detections: Iterable[Detection],
    predictions: Iterable[Prediction],
    fail_on_high: bool,
) -> List[tuple[Detection, Prediction]]:
    pairs = list(zip(detections, predictions))
    if fail_on_high:
        return [
            (det, pred)
            for det, pred in pairs
            if pred.label == "TP" and det.severity == "high"
        ]
    return [(det, pred) for det, pred in pairs if pred.label == "TP"]




def _export_results(
    detections: List[Detection],
    predictions: List[Prediction],
    *,
    formats: Sequence[str],
    out: Path,
    model: ModelHandle,
    threshold: float,
) -> None:
    fmt_set = set(formats)
    model_descriptor = f"{model.name}@{model.version}"

    if "sarif" in fmt_set:
        sarif_obj = to_sarif(
            detections,
            predictions,
            tool_name="iacsec",
            tool_version=str(model.version),
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as handle:
            json.dump(sarif_obj, handle, indent=2)
            handle.write("\n")
        console.print(f"[blue]SARIF written to[/] {out}")

    if "json" in fmt_set:
        json_path = out if out.suffix == ".jsonl" and fmt_set == {"json"} else out.with_suffix(".jsonl")
        write_jsonl(json_path, detections, predictions, threshold, model_descriptor)
        console.print(f"[blue]JSONL written to[/] {json_path}")

    if "table" in fmt_set:
        table = Table(title="iacsec findings")
        table.add_column("Rule")
        table.add_column("Severity")
        table.add_column("Prediction")
        table.add_column("Score", justify="right")
        table.add_column("Location")
        for det, pred in zip(detections, predictions):
            location = f"{det.file}:{det.line}"
            table.add_row(
                det.rule_id,
                det.severity,
                pred.label,
                f"{pred.score:.2f}",
                location,
            )
        console.print(table)





if __name__ == "__main__":  # pragma: no cover - manual execution
    app()
