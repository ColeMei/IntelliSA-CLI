
import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app
from packages.schema.models import Detection, Prediction


runner = CliRunner()


def _dummy_detection(**overrides) -> Detection:
    data = {
        "rule_id": "HTTP_NO_TLS",
        "smell": "http",
        "tech": "ansible",
        "file": "roles/web/tasks/main.yml",
        "line": 10,
        "snippet": "get_url: url=http://example.com",
        "message": "HTTP used without TLS",
        "severity": "medium",
        "evidence": {},
    }
    data.update(overrides)
    return Detection(**data)


def _dummy_prediction(**overrides) -> Prediction:
    data = {"label": "TP", "score": 0.9, "rationale": "score>=threshold"}
    data.update(overrides)
    return Prediction(**data)


class DummyModel:
    def __init__(self, name: str = "stub", version: str = "1.0.0", threshold: float = 0.5):
        self.name = name
        self.version = version
        self.default_threshold = threshold
        self.path = Path("/tmp/model.bin")
        self.framework = "torch"
        self.labels = ["TP", "FP"]


def test_scan_writes_sarif_and_json(monkeypatch, tmp_path):
    detection = _dummy_detection()
    prediction = _dummy_prediction()

    monkeypatch.setattr("apps.cli.main.run_glitch", lambda path, tech: [detection])
    monkeypatch.setattr("apps.cli.main.load_model", lambda name: DummyModel(name=name))
    monkeypatch.setattr("apps.cli.main.predict", lambda dets, code_dir, threshold: [prediction])

    out_path = tmp_path / "iacsec.sarif"
    result = runner.invoke(
        app,
        [
            "--path",
            str(tmp_path),
            "--out",
            str(out_path),
            "--format",
            "sarif",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 1
    sarif_data = json.loads(out_path.read_text())
    assert sarif_data["runs"][0]["results"][0]["ruleId"] == "HTTP_NO_TLS"
    jsonl_path = out_path.with_suffix(".jsonl")
    lines = jsonl_path.read_text().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["model"].startswith("codet5p-220m@")


def test_scan_returns_zero_when_no_blocking(monkeypatch, tmp_path):
    detection = _dummy_detection(severity="medium")
    prediction = _dummy_prediction(label="FP", score=0.1, rationale="score<threshold")

    monkeypatch.setattr("apps.cli.main.run_glitch", lambda path, tech: [detection])
    monkeypatch.setattr("apps.cli.main.load_model", lambda name: DummyModel(name=name))
    monkeypatch.setattr("apps.cli.main.predict", lambda dets, code_dir, threshold: [prediction])

    out_path = tmp_path / "scan.sarif"
    result = runner.invoke(
        app,
        [
            "--path",
            str(tmp_path),
            "--out",
            str(out_path),
            "--format",
            "sarif",
        ],
    )

    assert result.exit_code == 0
    assert out_path.exists()
