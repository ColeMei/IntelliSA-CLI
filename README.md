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
iacsec --path ./examples/sample_repo --tech auto --format sarif --out artifacts/scan
```

Tip: When a registry entry downloads remote weights, set `IACSEC_MODEL_CACHE` to control where files land:

```bash
IACSEC_MODEL_CACHE=$PWD/artifacts/model_cache \
  iacsec --path ./examples/sample_repo --tech auto --format sarif --out artifacts/scan
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
│  ├─ glitch_core/             # Vendored GLITCH source (upstream snapshot)
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

## CLI (pilot surface)

```bash
iacsec \
  --path . \
  --tech auto \
  --rules http,weak-crypto,hardcoded-secret,suspicious-comment \
  --postfilter codet5p-220m \
  --threshold 0.62 \
  --format sarif --format json --format csv --format table \
  --out artifacts/scan
```

**Exit codes**: `0` = ok, `1` = findings (non-blocking unless `--fail-on-high`), `2` = runtime error.

### CLI Options

- `--path` - Path to scan (default: current directory)
- `--tech` - Technology: `auto|ansible|chef|puppet` (default: auto)
- `--rules` - Comma-separated rule IDs (currently informational)
- `--postfilter` - Post-filter model name (default: codet5p-220m)
- `--threshold` - Override model default threshold
- `--format` - Output formats: `sarif`, `json`, `csv`, `table` (repeatable, default: sarif)
- `--out` - Base output path for all formats (directory or filename prefix)
- `--fail-on-high` - Treat only high-severity TPs as blocking findings
- `--debug-log` - Write debug trace JSONL to specified path

### Debugging & Troubleshooting

Add `--debug-log artifacts/iacsec-debug.jsonl` to capture a JSONL trace of raw GLITCH detections, encoder inputs, and post-filter predictions for each run.

**Stub Model Warning**: If the CLI warns about falling back to the deterministic stub model, install the ML dependencies:

```bash
pip install torch transformers
```

This ensures scans use the real codet5p-220m weights instead of the simplified stub model.

## Licensing

- Retain GLITCH’s original license inside `packages/glitch_core/`.
- This repo’s root `LICENSE` covers our glue code and model packaging.
