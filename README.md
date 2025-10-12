# iacsec

> **Project Hub**: [LLM-IaC-SecEval](../00.LLM-IaC-SecEval)  
> **This repository**: Production-ready CLI toolkit  
> See the hub for paper materials, artifact manifest, and links to all repositories.

## Overview

IaC security scanner combining GLITCH static analysis with an encoder-based LLM to filter false positives.

**Supported technologies**: Ansible, Chef, Puppet  
**Output formats**: SARIF (GitHub Code Scanning), JSONL, CSV, console table

## Quick Start

Requires Python 3.10+.

```bash
# Setup environment
python -m venv .venv && source .venv/bin/activate
pip install -U pip wheel
pip install -e .

# Fetch model weights
python -m iacsec.models.fetch codet5p-220m

# Scan a repository
iacsec --path ./examples/sample_repo --tech auto --format sarif --out artifacts/scan.sarif
```

**Exit codes**:
- `0` = no blocking findings
- `1` = findings detected (non-blocking unless `--fail-on-high`)
- `2` = runtime error

## Usage

```bash
iacsec --path /path/to/repo --tech auto --format sarif --out artifacts/scan.sarif
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

1. **GLITCH** scans IaC files for 11 security rules:
   - High-precision rules (empty password, invalid bind, etc.) → accepted directly
   - Noisy rules (HTTP without TLS, weak crypto, hardcoded secrets, suspicious comments) → post-filter

2. **LLM post-filter** (CodeT5p-220M encoder) scores noisy detections as True Positive or False Positive

3. **Exporters** produce SARIF, JSONL, or CSV with only high-confidence findings

Research background: See [docs/ROADMAP.md](docs/ROADMAP.md)

## Troubleshooting

**Stub model warning**:
```
Warning: falling back to deterministic stub model
```

**Fix**: Install PyTorch and transformers:
```bash
pip install torch transformers
```

The stub model produces deterministic but artificial scores for testing only.

## Documentation

- [User Handbook](docs/USER_HANDBOOK.md) - Complete operational guide
- [Development Report](docs/DEVELOPMENT_REPORT.md) - Architecture and contributor guide
- [Roadmap](docs/ROADMAP.md) - Research background and project vision
- [Schema](docs/SCHEMA.md) - Technical data model reference

## Repository Structure

```
├── apps/cli/              # Typer CLI entrypoint
├── packages/
│   ├── glitch_core/       # Vendored GLITCH
│   ├── glitch_adapter/    # GLITCH to schema adapter
│   ├── postfilter_llm/    # CodeT5p-220M loader and inference
│   ├── exporters/         # SARIF / JSONL / CSV
│   └── schema/            # Pydantic contracts
├── models/
│   ├── registry.yaml      # Model index
│   └── codet5p-220m/      # Champion model metadata
├── tests/
│   ├── unit/              # Module-level tests
│   └── e2e/               # End-to-end tests
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
