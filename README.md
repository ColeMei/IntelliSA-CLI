# iacsec

> **GLITCH + LLM Post-Filter** — IaC security scanner with fewer false positives.

A research-backed tool that combines [GLITCH](https://github.com/sr-lab/GLITCH) static analysis with an encoder-based LLM to filter false positives from Infrastructure-as-Code security scans.

**Supported technologies**: Ansible, Chef, Puppet  
**Output formats**: SARIF (GitHub Code Scanning), JSONL, CSV, console table

## Quick Start

Requires **Python 3.10+**.

```bash
# 1. Setup environment
python -m venv .venv && source .venv/bin/activate
pip install -U pip wheel
pip install -e .

# 2. Fetch model weights from Hugging Face
python -m iacsec.models.fetch codet5p-220m

# 3. Scan a repository
iacsec --path ./examples/sample_repo --tech auto --format sarif --out artifacts/scan.sarif
```

**Exit codes**:
- `0` = no blocking findings
- `1` = findings detected (non-blocking unless `--fail-on-high`)
- `2` = runtime error

## Basic Usage

```bash
iacsec \
  --path /path/to/repo \
  --tech auto \
  --format sarif \
  --out artifacts/scan.sarif
```

**Common options**:
- `--path` - Directory or file to scan (default: current directory)
- `--tech` - Technology: `auto|ansible|chef|puppet` (default: auto)
- `--format` - Output format: `sarif`, `json`, `csv`, `table` (repeatable)
- `--out` - Output path (directory or file prefix)
- `--postfilter` - Model name from `models/registry.yaml` (default: codet5p-220m)
- `--threshold` - Override model's default threshold
- `--fail-on-high` - Exit code 1 only for high-severity findings
- `--debug-log` - Write detailed trace to JSONL file

Run `iacsec --help` for all options.

## How It Works

1. **GLITCH** scans your IaC files for 11 security rules across 3 categories:
   - High-precision rules (empty password, invalid bind, etc.) → accepted directly
   - Noisy rules (HTTP without TLS, weak crypto, hardcoded secrets, suspicious comments) → post-filter

2. **LLM post-filter** (CodeT5p-220M encoder) scores noisy detections as True Positive (TP) or False Positive (FP)

3. **Exporters** produce SARIF, JSONL, or CSV with only high-confidence findings

**Research background**: See [docs/ROADMAP.md](docs/ROADMAP.md) for the 3-stage research process that validated this approach.

## Troubleshooting

**Stub model warning**:
```
Warning: falling back to deterministic stub model; install torch+transformers for codet5p-220m.
```

**Fix**: Install PyTorch and transformers:
```bash
pip install torch transformers
```

The stub model produces deterministic but artificial scores for testing purposes only.

## Documentation

- **[User Handbook](docs/USER_HANDBOOK.md)**: Complete operational guide (installation, all CLI flags, CI/CD integration)
- **[Development Report](docs/DEVELOPMENT_REPORT.md)**: Architecture and contributor guide
- **[Roadmap](docs/ROADMAP.md)**: Research background and project vision
- **[Schema](docs/SCHEMA.md)**: Technical data model reference

## Repository Structure

```
├── apps/cli/              # Typer CLI entrypoint
├── packages/
│   ├── glitch_core/       # Vendored GLITCH (upstream snapshot)
│   ├── glitch_adapter/    # GLITCH → schema.Detection
│   ├── postfilter_llm/    # CodeT5p-220M loader + inference
│   ├── exporters/         # SARIF / JSONL / CSV
│   └── schema/            # Pydantic contracts
├── models/
│   ├── registry.yaml      # Model index (name, URI, SHA256, threshold)
│   └── codet5p-220m/      # Champion model metadata
├── tests/
│   ├── unit/              # Module-level tests
│   └── e2e/               # End-to-end golden SARIF tests
└── examples/sample_repo/  # Minimal test repository
```

## GitHub Action

Use as a composite action in workflows:

```yaml
- uses: your-org/iacsec@main
  with:
    path: .
    format: sarif
    output: iacsec.sarif
    fail-on-high: true
```

See [action.yml](action.yml) for all inputs.

## License

- **This repository**: Apache 2.0 (see [LICENSE](LICENSE))
- **GLITCH**: Original license retained in `packages/glitch_core/`

## Citation

If you use this tool in research, please cite our work (publication pending).
