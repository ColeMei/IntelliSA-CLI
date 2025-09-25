# iacsec User Handbook (v1)

> Production checklist and day-to-day guide for running the iacsec CLI in your environments.

## 1. Prerequisites
- **Python**: 3.10 or newer.
- **System packages**: ensure you can build native wheels (`python -m pip install --upgrade pip setuptools wheel`).
- **Hardware**: CPU-only is supported; GPUs work if PyTorch detects them.
- **Python deps**: `torch`, `transformers`, `safetensors`, `typer`, `rich`, `pydantic`, `ruamel.yaml`, `ply`, `puppetparser`, `safetensors` (installed automatically via `pip install -e .`).
- **Models**: metadata (tokenizer + thresholds) lives under `models/codet5p-220m/`; weights download from Hugging Face when fetched.

## 2. Installation (fresh workspace)
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e .
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```
If you already have functional `torch`+`transformers`, skip the last line.

## 3. Downloading Model Weights
```bash
python -m iacsec.models.fetch codet5p-220m
```
This pulls the safetensors bundle from Hugging Face and verifies that transformers can load it. Review the output for any stub warnings.

## 4. Verifying Model Backend
After activating the venv, confirm the real model will load:
```bash
python - <<'PY'
from packages.postfilter_llm.engine import load_model, _load_hf_artifacts, torch
handle = load_model("codet5p-220m")
print("torch available?", torch is not None)
print("HF artifacts loaded?", _load_hf_artifacts(handle) is not None)
PY
```
Both lines must print `True`. If not, reinstall `torch`/`transformers` before scanning; otherwise the CLI will fall back to the deterministic stub with misleading scores.

## 5. Running Scans
Standard command:
```bash
IACSEC_MODEL_CACHE=$PWD/artifacts/model_cache \
  iacsec scan --path /path/to/repo \
              --tech auto \
              --format sarif --format json --format csv \
              --postfilter codet5p-220m \
              --out artifacts/iacsec.sarif \
              --debug-log artifacts/iacsec-debug.jsonl
```
Key flags:
- `--tech auto`: autodetect Ansible/Chef/Puppet. Override if your repo is homogeneous.
- `--format`: choose one or multiple (`sarif`, `json`, `csv`, `table`).
- `--postfilter`: name from `models/registry.yaml`.
- `--debug-log`: strongly recommended; stores a JSONL trace of detector output, encoder inputs, predictions, and final decisions.
- `--fail-on-high`: set if you want exit code 1 only for high-severity true positives.

## 6. Interpreting Outputs
- **SARIF** (`artifacts/iacsec.sarif`): canonical for GitHub code scanning.
- **JSONL** (`artifacts/iacsec.jsonl`): per-detection records with prediction metadata.
- **CSV** (`artifacts/iacsec.csv`): trimmed list of surviving true positives plus coverage rows for untouched files.
- **Console table** (if `--format table`): quick triage view.

Each surviving detection includes the original GLITCH evidence and the post-filter label/score. CSV only lists detections labeled `TP`.

## 7. Debugging & Troubleshooting
- **Stub warning**: If the CLI prints `Warning: falling back to deterministic stub model...`, install `torch` and `transformers` in your venv before trusting results. The debug log will also record an event `{ "event": "warning", "stage": "postfilter", "message": "using stub model" }`.
- **Missing weights**: run `python -m iacsec.models.fetch codet5p-220m` to rehydrate safetensors from Hugging Face. If you refresh weights, update `models/registry.yaml` + SHA.
- **Large repositories**: set `IACSEC_MODEL_CACHE` to a fast local SSD to avoid repeated downloads.
- **Errors from GLITCH**: see `glitch_detections` entries in the debug log. Parser issues are logged with stage=`glitch` or `predict`.

## 8. CI/CD Integration
- Always run the post-filter on the same platform where you validated `torch`/`transformers`.
- Capture the debug log as a build artifact for auditability.
- Fail builds with `--fail-on-high` or parse SARIF severity to gate merges.

## 9. Support & Maintenance Checklist
- Run `pytest` before publishing new releases (`tests/unit` + `tests/e2e`).
- Keep `AGENTS.md` and this handbook in sync when adding new CLI flags.
- Update `models/registry.yaml` and docs whenever champion weights or thresholds change.
- Periodically re-run the backend verification snippet to catch environment drift.

## 10. Release Notes Template
When publishing updates, include:
1. Model version & SHA.
2. CLI changes / new flags.
3. Tests executed (unit/e2e, sample scan).
4. Known limitations (e.g., unsupported tech, stub fallback).

---
Future features (e.g., ONNX runtime, new exporters) should extend this handbook with additional setup and verification steps.
