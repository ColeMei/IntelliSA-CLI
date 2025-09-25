# iacsec (pilot)

> GLITCH ➜ LLM Post-Filter ➜ SARIF/JSON — a practical IaC security checker with fewer false positives.

This is a **pilot** repo whose goal is to ship a minimal, working tool that:
- runs **GLITCH** locally,
- passes detections through our **encoder-based LLM post-filter**,
- emits **SARIF** (for GitHub code scanning), **JSONL**, and **CSV**,
- is easy for AI agents to extend (GLITCH source is vendored in-repo).

## Quickstart

Requires Python 3.10+.

```bash
# 1) Create & activate venv
python -m venv .venv && source .venv/bin/activate

# 2) Install (editable)
pip install -U pip wheel
pip install -e .

# 3) Fetch the champion weights
python -m iacsec.models.fetch codet5p-220m  # downloads weights from Hugging Face

# 4) Scan a repo
iacsec scan --path ./examples/sample_repo --tech auto --format sarif --out artifacts/iacsec.sarif
```

Tip: When a registry entry downloads remote weights, set `IACSEC_MODEL_CACHE` to control where files land:

```bash
IACSEC_MODEL_CACHE=$PWD/artifacts/model_cache \
  iacsec scan --path ./examples/sample_repo --tech auto --format sarif --out artifacts/iacsec.sarif
```

The champion encoder (`codet5p-220m`) references metadata under `models/`, while the actual weights download from Hugging Face on first use. The `codet5p-220m-stub` entry remains for deterministic tests.

- Outputs from trees now include both high-precision GLITCH findings (empty passwords, invalid binds, missing default switches, etc.) and noisy smells filtered through `codet5p-220m`.

## Repo layout (pilot)

```
iacsec/
├─ apps/
│  └─ cli/                     # Typer-based CLI entrypoints
├─ packages/
│  ├─ schema/                  # Stable Pydantic contracts for detections/results
│  ├─ glitch_core/             # 🚨 Vendored GLITCH source (upstream snapshot)
│  ├─ glitch_adapter/          # Wraps glitch_core → schema.Detection
│  ├─ postfilter_llm/          # Loads champion model, scores, thresholds
│  └─ exporters/               # SARIF / JSONL / CSV / table
├─ models/
│  ├─ registry.yaml            # Model index (name, version, uri, sha256, threshold)
│  └─ codet5p-220m/            # Champion weights + tokenizer bundle
├─ docs/
│  ├─ ROADMAP.md               # Background (Stage 1–3) + Why a tool (practice)
│  └─ DEVELOPMENT_REPORT.md    # Current architecture + decisions
├─ examples/
│  └─ sample_repo/             # Tiny IaC repo used by e2e tests
├─ tests/
│  ├─ unit/                    # schema, thresholding, adapters
│  └─ e2e/                     # scan sample_repo → golden SARIF
├─ .github/
│  └─ workflows/ci.yml         # Lint + unit + e2e (CPU)
├─ pyproject.toml              # Minimal build metadata
├─ action.yml                  # Composite GitHub Action (pilot)
├─ .editorconfig
├─ .gitignore
├─ LICENSE
└─ README.md
```

## Initialize this repo (human or AI agent)

1. **Vendor GLITCH**: copy the GLITCH source into `packages/glitch_core/` (keep its original LICENSE and NOTICE files in that folder).
2. **Wire the adapter**: implement `packages/glitch_adapter/run_glitch.py` exposing:

   ```python
   def run_glitch(path: str, tech: str) -> list[schema.Detection]: ...
   ```
3. **Install** (`pip install -e .`) and run `iacsec scan --help` to verify CLI wiring.
4. **Models**: the champion encoder (`codet5p-220m`) ships in `models/`; keep the stub entry for deterministic tests or update `models/registry.yaml` if you swap weights.
5. **E2E**: `pytest -q` should produce a SARIF under `tests/e2e/golden/` with a stable hash.
6. **Action smoke test**: see `AGENTS.md` for CI pointers and workflows.

## CLI (pilot surface)

```bash
iacsec scan \
  --path . \
  --tech auto \
  --rules http,weak-crypto,hardcoded-secret,suspicious-comment \
  --postfilter codet5p-220m \
  --threshold 0.62 \
  --format sarif --format json --format csv \
  --out artifacts/iacsec.sarif
```

**Exit codes**: `0` = ok, `1` = findings (non-blocking unless `--fail-on-high`), `2` = runtime error.

Add `--debug-log artifacts/iacsec-debug.jsonl` to capture a JSONL trace of raw GLITCH detections, encoder inputs, and post-filter predictions for each run.

If the CLI warns about falling back to the deterministic stub model, install `torch` and `transformers` so scans use the real codet5p-220m weights.

## Licensing

* Retain GLITCH’s original license inside `packages/glitch_core/`.
* This repo’s root `LICENSE` covers our glue code and model packaging.
