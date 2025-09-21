# Pilot CLI scaffold (no real scanning yet).
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console

app = typer.Typer(add_completion=False)
console = Console()


@app.command()
def scan(
    path: Path = typer.Option(Path("."), "--path", help="Path to scan"),
    tech: str = typer.Option("auto", "--tech", help="auto|ansible|chef|puppet"),
    rules: str = typer.Option(
        "http,weak-crypto,hardcoded-secret,suspicious-comment",
        "--rules",
        help="Comma-separated rule ids",
    ),
    postfilter: str = typer.Option("codet5p-220m", "--postfilter", help="Model name"),
    threshold: Optional[float] = typer.Option(None, "--threshold", help="Override model default"),
    format: List[str] = typer.Option(["sarif"], "--format", help="One or more of: sarif,json,table"),
    out: Path = typer.Option(Path("artifacts/iacsec.sarif"), "--out", help="Output file"),
    fail_on_high: bool = typer.Option(False, "--fail-on-high", help="Future: fail build on high severity"),
) -> int:
    """
    Pilot entrypoint. Wires modules and writes placeholder outputs.
    """
    console.log("[bold]iacsec[/] pilot CLI — scaffold only.")

    # Lazy imports so the repo can install before implementations exist.
    try:
        from packages.glitch_adapter.run_glitch import run_glitch
        from packages.postfilter_llm.engine import load_model, predict
        from packages.exporters.sarif import to_sarif
        from packages.exporters.jsonl import write_jsonl
    except Exception as e:
        console.print(f"[red]Imports not ready yet: {e}[/]")
        raise typer.Exit(code=2)

    # 1) Run detector (GLITCH adapter)
    detections = run_glitch(str(path), tech)

    # 2) Load post-filter & predict
    model = load_model(postfilter)
    preds = predict(detections, path, threshold)

    # 3) Export
    out.parent.mkdir(parents=True, exist_ok=True)
    if "sarif" in {f.lower() for f in format}:
        sarif_obj = to_sarif(detections, preds)
        # Placeholder: write a minimal marker; real SARIF implementation TBD
        out.write_text("// TODO: replace with real SARIF JSON\n", encoding="utf-8")

    if "json" in {f.lower() for f in format}:
        write_jsonl(out.with_suffix(".jsonl"), detections, preds, threshold or 0.0, postfilter)

    console.print("[green]Done (pilot).[/]")
    return 0


if __name__ == "__main__":
    app()
