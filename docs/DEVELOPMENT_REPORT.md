# Repository Development Report

## 1. Purpose and Context
- The README.md positions iacsec as a pilot that bundles GLITCH detections with an encoder-based LLM post-filter to deliver SARIF/JSON outputs for IaC security scanning.
- Docs/ROADMAP.md clarifies the motivation: reduce false positives without sacrificing recall by coupling high-recall GLITCH with a deterministic classifier, and ship runnable artifacts usable by real teams and AI agents.
- This report captures the current repository state, the development decisions we made to realize that vision, and guidance for extending or operating the tool.

## 2. Architecture Overview
### 2.1 Pipeline Composition

- **Post-filter layer**: `packages/postfilter_llm/engine.py` now consumes the champion CodeT5p-220M metadata (config, tokenizer, thresholds) from `models/codet5p-220m/`, downloading weights from Hugging Face and falling back to the stub entry for lightweight tests.
- **Detector layer (GLITCH)** now preserves all 11 upstream security rules. Five high-precision rules (admin-by-default, empty-password, invalid-bind, no-integrity-check, missing-default-switch) flow straight through with rationale `glitch-accepted`, while the four noisy ones (HTTP without TLS, weak crypto, hard-coded secret, suspicious comment) retain the post-filter.
- **Sample repository** includes fixtures for both categories so golden artifacts validate post-filtered and automatically accepted findings.

- **Detector layer (GLITCH)**: Vendored under `packages/glitch_core/` and surfaced via `packages/glitch_adapter/run_glitch.py`. The adapter normalizes raw GLITCH errors into our Pydantic `Detection` contract, mapping upstream rule codes through `rules_map.yaml` and deduplicating results.
- **Schema boundary**: `packages/schema/models.py` defines immutable, validated `Detection` and `Prediction` models exactly as described in docs/SCHEMA.md, enforcing field names, severity enums, and score ranges so every downstream component receives predictable data.
- **Post-filter layer**: `packages/postfilter_llm/engine.py` reads `models/registry.yaml`, resolves the vendored champion weights (with a stub fallback for deterministic tests), verifies SHA256 hashes, and produces deterministic predictions. Determinism preserves reproducibility in line with ROADMAP goals.
- **Exporter layer**: `packages/exporters/sarif.py`, `jsonl.py`, and `csv.py` convert detection/prediction pairs into SARIF/JSONL artifacts plus table-friendly CSV summaries. SARIF exports fix timestamps to keep goldens diff-friendly.
- **CLI surface**: `apps/cli/main.py` implements the single Typer `scan` command described in README. Options mirror README/quickstart flags—`--tech`, `--format`, `--postfilter`—and orchestrate detector, post-filter, and exporters with clear exit codes (`0` clean, `1` findings, `2` error).

### 2.2 Supporting Assets
- **Sample repository**: `examples/sample_repo/` supplies a minimal Ansible play that triggers an HTTP-without-TLS finding, allowing quick smoke tests and golden comparisons.
- **Golden outputs**: `tests/e2e/golden/sample.{sarif,jsonl}` store canonical outputs to ensure changes don’t drift from expected results.
- **Tests**: Unit suites cover schema round-trips, adapter mapping, post-filter determinism, exporters, and CLI behavior. `tests/e2e/test_sample_scan.py` runs the real CLI against the sample repo, verifying outputs against the goldens.

## 3. Development Decisions & Rationale
### 3.1 GLITCH Integration
- ROADMAP emphasises treating GLITCH as a black box; run_glitch only wraps, normalizes rule metadata, and resolves vendored code via a sys.path insert instead of modifying upstream logic.
- Rule mappings live in YAML to keep configuration data-driven; this matches the “extensible schema boundary” emphasis in the ROADMAP.

### 3.2 Schema Contracts
- README and docs/SCHEMA.md require stable field names for `Detection` and `Prediction`. We enforced immutability (`frozen=True`) and `extra="forbid"` to prevent accidental expansion, safeguarding compatibility for exporters and downstream automation.

### 3.3 Post-filter Models
- The champion CodeT5p-220M checkpoint is published at https://huggingface.co/colemei/codet5p-220m-iac-security (metadata mirrored under `models/codet5p-220m/`), so production scans fetch the real encoder by default.
- The registry retains a `codet5p-220m-stub` entry that reuses the same loader but emits deterministic hash-based scores for tests, keeping fixtures stable while exercising the identical code paths.
- The loader verifies SHA256 digests from the registry for every entry, preserving pinned, reproducible artifacts.

### 3.4 Exporters
- SARIF output adheres to the format quoted in README (tool driver metadata, rule IDs, location URIs). Setting a fixed conversion timestamp supports golden comparisons and caching scenarios.
- JSONL exporter mirrors docs/SCHEMA.md’s “joined” structure (detection/prediction/threshold/model). We guard against mismatched iterables to surface errors early.
- CSV exporter lists detections alongside empty file slots so practitioners can triage coverage in spreadsheets or dashboards.

### 3.5 CLI Behavior
- README’s quickstart expects `iacsec scan --path … --format sarif --out …`. The Typer command honors those defaults and adds `--format json` and `--format table` for extra views, keeping exit codes consistent with README’s note (0 success, 1 findings, 2 error).
- `--fail-on-high` enables future gating logic, aligning with the roadmap’s need for CI-friendly enforcement without yet failing on all findings.

### 3.6 Testing Strategy
- Unit tests isolate each layer, providing fast feedback required by ROADMAP’s “AI agents extend easily” goal.
- The e2e test ensures the whole pipeline—from adapter through exporters—behaves deterministically, echoing the roadmap’s “runnable artifacts” deliverable.
- Full pytest (including vendored GLITCH tests) would require packaging the entire GLITCH suite; we document the limitation and focus CI on our maintained suites.

### 3.7 Automation & Action Design
- The composite action in `action.yml` installs the package, relies on the vendored registry entries for weights, and runs `iacsec scan`. It tolerates exit code 1 (findings) but fails on runtime errors, matching practical CI needs described in README (“non-blocking unless fail-on-high”).
- `.github/workflows/ci.yaml` runs unit + e2e tests, then exercises the composite action against the sample repo and uploads the SARIF artifact, providing an end-to-end validation path.

## 4. Usage Guide
1. **Local setup** (README quickstart):
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -U pip
   pip install -e .
   python -m iacsec.models.fetch codet5p-220m
   iacsec --help
   ```
2. **Sample scan**:
   ```bash
   IACSEC_MODEL_CACHE=$PWD/artifacts/model_cache    iacsec --path examples/sample_repo --tech ansible      --format sarif --format json --out artifacts/iacsec.sarif
   ```
   Exit code `1` indicates findings; SARIF/JSONL appear under `artifacts/`.
   Add `--debug-log artifacts/scan-debug.jsonl` when you need a JSONL trace of GLITCH detections, encoder inputs, predictions for troubleshooting.
   A stub-warning indicates the HF deps (torch/transformers) are missing; install them before interpreting scores.
3. **Tests**:
   ```bash
   pytest tests/unit
   pytest tests/e2e/test_sample_scan.py
   ```
4. **GitHub Action**: Reference `action.yml` in workflows to scan a repository and gather SARIF; CI example under `.github/workflows/ci.yaml` runs unit/e2e suites and publishes artifacts.

## 5. Maintenance & Extension Tips
- Update `models/registry.yaml` with real weight metadata once available; the loader already handles SHA verification and cache directories.
- Extend `packages/glitch_adapter/rules_map.yaml` when onboarding new GLITCH rules; unit tests in `tests/unit/test_glitch_adapter.py` should be updated to reflect new mappings.
- When adding formats, enrich `_export_results` and exporters in tandem, ensuring schema tests remain green.
- If onboarding new sample repos, add golden outputs under `tests/e2e/golden/` and extend the e2e suite for regression coverage.

## 6. Future Considerations (per ROADMAP)
- **Model upgrades**: Calibrate per-tech thresholds, explore quantized/ONNX variants, and document the procedure for refreshing the champion weights.
- **Additional exporters**: The roadmap mentions SARIF and JSONL; future iterations could add Markdown triage reports or ONNX-based fast inference.
- **ONNX runtime**: Stage 3 stretch goal includes ONNX for CPU speed; wiring would occur in `postfilter_llm/engine.py` with registry flags.
- **Action enhancements**: Add optional upload to GitHub code scanning, or allow multi-repo scans via matrices.

## 7. Known Limitations
- Vendored GLITCH tests are excluded; running `pytest` without filtering attempts to import `glitch` as an installable package and fails. Our CI intentionally targets maintained suites.
- The stub model remains for deterministic tests only; it emits artificial scores and should stay out of production pipelines.
- The sample repo covers a single smell (HTTP without TLS); broaden coverage as more smells become critical.

---
This report reflects the repository as of the latest commits. For ongoing updates, synch with README.md and docs/ROADMAP.md objectives: keep the pipeline deterministic, schema-bound, and easy for both humans and agents to extend.
