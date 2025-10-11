# Development Report

> Architecture, design decisions, and contributor guide for iacsec.

## Purpose & Context

This document captures the technical architecture of iacsec, key design decisions, and guidance for extending the tool. It's intended for developers and contributors who need to understand the codebase structure.

**For users**: See [USER_HANDBOOK.md](USER_HANDBOOK.md)  
**For research context**: See [ROADMAP.md](ROADMAP.md)

## Architecture Overview

### High-Level Pipeline

```
IaC Files → GLITCH Scanner → Category Split → Post-Filter → Exporters
                ↓                    ↓              ↓            ↓
            Detection[]      A: Direct pass  B: LLM score   SARIF/JSONL/CSV
                           (high-precision)  (noisy rules)
```

**Flow**:
1. **GLITCH** scans files, produces raw detections
2. **Adapter** normalizes to `Detection` schema, splits into categories:
   - Category A: High-precision rules (empty password, invalid bind, etc.) → label as TP immediately
   - Category B: Noisy rules (HTTP, weak crypto, secrets, comments) → require post-filter
3. **Post-filter** scores Category B with CodeT5p-220M encoder
4. **Exporters** merge both categories, output only TPs

### Module Responsibilities

#### `packages/schema/`
**Purpose**: Immutable Pydantic contracts shared across all modules

**Key types**:
- `Detection`: Normalized finding (rule, file, line, snippet, severity, evidence)
- `Prediction`: Post-filter output (label, score, rationale)
- Enums: `Smell`, `Tech`, `Severity`, `Label`

**Design principle**: `frozen=True`, `extra="forbid"` prevent accidental schema drift

#### `packages/glitch_core/`
**Purpose**: Vendored GLITCH source (upstream snapshot)

**Constraints**:
- **DO NOT MODIFY** upstream code (per AGENTS.md guidelines)
- Preserve original LICENSE and NOTICE files
- Update only when syncing with upstream releases

**Integration**: Added to `sys.path` dynamically by adapter

#### `packages/glitch_adapter/`
**Purpose**: Wraps GLITCH → produces `Detection[]`

**Key files**:
- `run_glitch.py`: Main entry point, orchestrates tech detection and scanning
- `rules_map.yaml`: Maps GLITCH rule codes → schema fields (rule_id, smell, severity, postfilter flag)

**Responsibilities**:
- Invoke GLITCH parsers (Ansible, Chef, Puppet)
- Normalize errors to `Detection` schema
- Deduplicate findings (file, line, rule_id)
- Tag noisy rules with `evidence.postfilter=True`

**Extension point**: Add new rules by updating `rules_map.yaml`

#### `packages/postfilter_llm/`
**Purpose**: Load model, run inference, produce `Prediction[]`

**Key files**:
- `engine.py`: Model loader, predictor, threshold resolver
- Uses `models/registry.yaml` for model metadata

**Flow**:
1. `load_model(name)` → download if needed, verify SHA256, return `ModelHandle`
2. `predict(detections, code_dir, threshold)` → batch inference, apply thresholds
3. Fallback to stub model if torch/transformers unavailable

**Backends**:
- `hf`: PyTorch + transformers (production)
- `stub`: Deterministic hash-based scores (testing only)

**Environment variables**:
- `IACSEC_MODEL_CACHE`: Override default cache (`~/.cache/iacsec`)
- `IACSEC_POSTFILTER_BATCH`: Batch size (default 16)

#### `packages/exporters/`
**Purpose**: Convert `Detection[]` + `Prediction[]` → output formats

**Modules**:
- `sarif.py`: SARIF 2.1.0 spec, GitHub Code Scanning compatible
- `jsonl.py`: One JSON object per line (detection + prediction + metadata)
- `csv.py`: Spreadsheet format (file, line, category)

**Design principle**: Each exporter is pure function taking detections/predictions, returning serializable objects

#### `apps/cli/`
**Purpose**: Typer-based CLI entrypoint

**Key file**: `main.py`

**Responsibilities**:
- Parse arguments
- Orchestrate pipeline (GLITCH → post-filter → export)
- Handle errors, exit codes
- Manage debug logging

**Exit codes**:
- `0`: No blocking findings
- `1`: Findings detected (blocking if not `--fail-on-high` or all findings are high-severity with `--fail-on-high`)
- `2`: Runtime error

### Data Flow Contracts

**GLITCH → Adapter**:
```python
# GLITCH produces error objects
error.code: str          # e.g., "sec_weak_crypto"
error.path: str          # Absolute file path
error.line: int          # Line number (may be 0)
error.repr: Optional[str] # Human-readable detail
```

**Adapter → Schema**:
```python
Detection(
    rule_id="WEAK_CRYPTO",
    smell="weak-crypto",
    tech="ansible",
    file="relative/path.yml",
    line=42,
    snippet="openssl: algorithm=md5",
    message="Weak cryptography algorithm",
    severity="medium",
    evidence={"glitch_code": "sec_weak_crypto", "postfilter": True}
)
```

**Post-filter → Schema**:
```python
Prediction(
    label="TP",          # or "FP"
    score=0.87,          # 0.0-1.0
    rationale="score>=threshold"
)
```

## Design Decisions

### 1. Vendored GLITCH

**Decision**: Copy GLITCH source into `packages/glitch_core/` instead of depending on pip package

**Rationale**:
- GLITCH not published to PyPI
- Ensures version stability (no surprise upgrades)
- Enables AI agents to read/understand detection logic
- Simplifies installation (no external dependencies)

**Trade-off**: Must manually sync with upstream updates

### 2. Two-Category Detection Flow

**Decision**: Split detections into high-precision (Category A) and noisy (Category B)

**Rationale**:
- Avoids false negatives from over-aggressive post-filter
- Preserves 100% recall for reliable rules
- Focuses ML effort where it's needed (noisy rules)
- Research validated this split (Stage 2-3)

**Implementation**:
- `rules_map.yaml` tags noisy rules with `postfilter: true`
- Category A gets `Prediction(label="TP", score=1.0, rationale="glitch-accepted")`
- Only Category B runs through neural network

### 3. Frozen Thresholds

**Decision**: Commit calibrated thresholds to `models/codet5p-220m/frozen_thresholds.yaml`

**Rationale**:
- Deterministic, reproducible results
- Eliminates per-deployment tuning
- Research found stable thresholds generalize across organizations
- Easy to version-control

**Extension**: Add per-smell or per-tech thresholds by updating YAML

### 4. Immutable Schema

**Decision**: Use `frozen=True` and `extra="forbid"` on Pydantic models

**Rationale**:
- Prevents accidental modification of detections/predictions
- Forces explicit schema evolution
- Makes data flow easier to reason about
- Catches bugs at runtime (extra fields rejected)

**Trade-off**: Requires new models for schema changes (cannot mutate existing)

### 5. SHA256-Verified Weights

**Decision**: Store SHA256 checksum in `models/registry.yaml`, verify on load

**Rationale**:
- Prevents corruption or malicious substitution
- Ensures reproducibility (exact weights = exact predictions)
- Detects incomplete downloads

**Implementation**: `engine.py` computes SHA256 on first load, caches result

### 6. Stub Model Fallback

**Decision**: Implement deterministic stub when torch/transformers unavailable

**Rationale**:
- Tests run without heavy dependencies
- Faster CI (no GPU/CPU inference)
- Explicit warning prevents users from trusting stub scores

**Limitation**: Stub produces artificial scores via hash function, unsuitable for production

## Extension Guide

### Adding a New GLITCH Rule

1. Verify GLITCH detects it (check `packages/glitch_core/glitch/analysis/security.py`)
2. Add mapping to `packages/glitch_adapter/rules_map.yaml`:
   ```yaml
   sec_new_rule:
     rule_id: NEW_RULE
     smell: new-smell
     message: "Description of the vulnerability"
     severity: high
     postfilter: false  # true if noisy, false if high-precision
   ```
3. Update `packages/schema/models.py` if new `Smell` enum needed
4. Add test case to `tests/unit/test_glitch_adapter.py`
5. Update golden outputs in `tests/e2e/golden/` if needed

### Adding a New Exporter

1. Create `packages/exporters/new_format.py`
2. Implement function:
   ```python
   def to_new_format(detections: List[Detection], predictions: List[Prediction]) -> dict:
       # Convert to your format
       return result
   ```
3. Wire into CLI (`apps/cli/main.py`):
   ```python
   if "new_format" in fmt_set:
       result = to_new_format(detections, predictions)
       with (output_dir / f"{base_name}.ext").open("w") as f:
           json.dump(result, f)
       outputs["new_format"] = output_dir / f"{base_name}.ext"
   ```
4. Add tests to `tests/unit/test_exporters.py`
5. Update `--format` help text and documentation

### Upgrading the Model

1. Train new model, export safetensors
2. Upload to HuggingFace (or local URI)
3. Compute SHA256:
   ```bash
   sha256sum model.safetensors
   ```
4. Update `models/registry.yaml`:
   ```yaml
   - name: codet5p-220m
     version: 2.0.0  # increment
     uri: https://huggingface.co/.../model.safetensors
     sha256: <new-hash>
     default_threshold: 0.65  # recalibrate if needed
   ```
5. Calibrate thresholds, update `models/codet5p-220m/frozen_thresholds.yaml`
6. Run full test suite, update golden outputs
7. Document changes in release notes

### Adding a New Technology (e.g., Terraform)

1. Integrate/vendor Terraform static analyzer (or use existing like tfsec)
2. Create adapter in `packages/terraform_adapter/` following `glitch_adapter` pattern
3. Update `packages/schema/models.py`:
   ```python
   Tech = Literal["ansible", "chef", "puppet", "terraform"]
   ```
4. Wire into CLI tech detection (`_resolve_techs` in adapter)
5. Add test fixtures in `examples/` and `tests/`
6. Update documentation

## Testing Strategy

### Unit Tests (`tests/unit/`)

**Coverage**:
- Schema validation (frozen, extra fields rejected)
- Adapter mapping (GLITCH errors → Detections)
- Post-filter thresholding
- Exporter output format
- CLI argument parsing

**Approach**: Mock heavy dependencies (GLITCH, PyTorch), test pure logic

**Example**:
```python
def test_detection_immutable():
    det = Detection(...)
    with pytest.raises(ValidationError):
        det.line = 99  # Should fail (frozen)
```

### E2E Tests (`tests/e2e/`)

**Coverage**:
- Full pipeline (GLITCH → post-filter → export)
- Golden SARIF comparison
- Real model inference (stub model for speed)

**Approach**: Run CLI against `examples/sample_repo`, compare outputs

**Golden files**: `tests/e2e/golden/sample.{sarif,jsonl}`

**Updating goldens**:
```bash
iacsec --path examples/sample_repo --tech ansible --format sarif --out tests/e2e/golden/sample.sarif
```

Document rationale in commit message when updating.

### CI Workflow (`.github/workflows/ci.yml`)

**Steps**:
1. Lint (future: ruff, black)
2. Unit tests (fast, no model inference)
3. E2E tests (stub model)
4. Composite action test (real scan of sample repo)

**Coverage goal**: 80%+ for non-vendored code

## Troubleshooting Development Issues

### Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'packages'`

**Fix**: Install in editable mode:
```bash
pip install -e .
```

### GLITCH Import Failures

**Symptom**: `ModuleNotFoundError: No module named 'glitch'`

**Fix**: Ensure `packages/glitch_core` in `sys.path` (adapter handles this)

### Schema Validation Errors

**Symptom**: `ValidationError: extra fields not permitted`

**Debug**:
```python
from packages.schema.models import Detection
Detection.model_validate(your_dict)  # See which field is extra
```

### Test Failures After Model Update

**Symptom**: Golden SARIF mismatches

**Fix**:
1. Verify model loaded correctly: `python -m iacsec.models.fetch codet5p-220m`
2. Re-run scan, inspect diff
3. If intentional, update goldens with rationale
4. If unintentional, check threshold/model version

## Performance Considerations

### Batch Size

Default: 16 detections per batch (optimal for CPU)

**Tuning**:
- CPU: 8-32
- GPU: 64-128

**Set via**: `export IACSEC_POSTFILTER_BATCH=64`

### Model Cache

**Default**: `~/.cache/iacsec/`

**CI optimization**: Mount cache volume
```yaml
- uses: actions/cache@v3
  with:
    path: ~/.cache/iacsec
    key: iacsec-${{ hashFiles('models/registry.yaml') }}
```

### Memory Usage

- **GLITCH**: ~100MB per 1000 files
- **CodeT5p-220M**: ~1GB loaded model
- **Batch inference**: ~50MB per batch

**Total**: ~2GB for typical repository scan

## Code Style & Conventions

### Python

- **Version**: 3.10+ (use modern type hints)
- **Formatter**: Follow `.editorconfig` (4 spaces for Python)
- **Type hints**: Required for public functions
- **Docstrings**: For complex logic only (code should be self-documenting)

### Module Organization

```
packages/
└── module_name/
    ├── __init__.py       # Exports public API
    ├── core.py           # Main logic
    ├── utils.py          # Helpers
    └── tests/            # Unit tests (optional, prefer tests/unit/)
```

### Naming Conventions

- **Functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: `_leading_underscore`
- **CLI flags**: `--kebab-case`

### Git Commits

- **Format**: `Verb noun: brief description`
  - `Add Terraform adapter for HCL parsing`
  - `Fix threshold application for Chef rules`
  - `Update golden SARIF after model upgrade`
- **Length**: 50 chars subject, 72 chars body
- **Reference**: Link issues in body

## Maintenance Checklist

### Monthly

- [ ] Review open issues
- [ ] Update dependencies (`pip list --outdated`)
- [ ] Run full test suite
- [ ] Check for GLITCH upstream updates

### Quarterly

- [ ] Evaluate model performance on recent IaC patterns
- [ ] Review and update thresholds if needed
- [ ] Update documentation for accuracy
- [ ] Archive old debug logs

### Yearly

- [ ] Retrain model on expanded dataset
- [ ] Major version bump if schema changes
- [ ] Security audit of dependencies
- [ ] Benchmark against competing tools

## Future Technical Debt

1. **ONNX runtime**: Implement for faster CPU inference
2. **Parallel GLITCH**: Scan files concurrently (currently serial)
3. **Incremental scans**: Only scan changed files in large repos
4. **Model quantization**: INT8 weights for smaller footprint
5. **Attention visualization**: Export attention maps for explainability

## Resources

- **Pydantic docs**: https://docs.pydantic.dev/
- **SARIF spec**: https://docs.oasis-open.org/sarif/sarif/v2.1.0/
- **Typer docs**: https://typer.tiangolo.com/
- **PyTorch optimization**: https://pytorch.org/tutorials/recipes/recipes/tuning_guide.html

---

**Last Updated**: 2025-01  
**Maintainers**: See CODEOWNERS
