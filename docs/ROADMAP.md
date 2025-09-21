# Project Roadmap (Pilot Refactor)

## A) Background — What we did in Stage 1–3

**Problem.** IaC security tools (e.g., GLITCH) are high-recall but **noisy**, creating alert fatigue in real teams.  
**Goal.** Use LLMs to cut false positives **without** hurting recall.

### Stage 1 — Initial Exploration
- Built a two-stage pipeline: **GLITCH detections → LLM decision (TP/FP)**.
- Surveyed four smells across **Chef / Ansible / Puppet**:
  - Use of HTTP without TLS
  - Weak crypto
  - Hard-coded secret
  - Suspicious comment
- Learned that **prompt-only, generative** approaches often **parrot** GLITCH FPs; recall stable, precision poor.

### Stage 2 — Model Training
- Curated deduplicated train/val/test sets; tracked dataset manifests + SHA256s.
- Compared encoders (CodeBERT, CodeT5, CodeT5+) vs. larger generative models (CodeLLaMA, Qwen2.5).
- Found **encoder classifiers** consistently outperform generative reasoning for FP filtering.

### Stage 3 — Evaluation & Comparison
- Metrics: precision/recall, PR curves, FP reduction at fixed recall, bootstrap CIs.
- **Champion**: an encoder model (CodeT5p-220M) with stable thresholds across stacks.
- Negative result captured: a refactored HTTP prompt that **collapsed recall** (kept as an ablation).

**Takeaway:** High-recall GLITCH + **encoder post-filter** is a practical recipe: fewer FPs, recall intact.

---

## B) Why a Tool (Practice) — What we want this tool to do

Real users need **runnable artifacts**, not just plots. This repo packages our findings into a **developer-friendly tool**:

- **End-to-end**: runs GLITCH locally (vendored) and applies the **post-filter**.
- **Deterministic**: pinned model + threshold + dataset manifests for reproducible results.
- **Interoperable**: emits **SARIF** for GitHub Code Scanning and **JSONL** for pipelines.
- **Simple CI**: a composite **GitHub Action** that works without Docker.
- **Extensible**: clear **schema** boundaries so you can swap detectors or models later.

**Pilot scope:**
1. CLI: `iacsec scan …` with `--tech auto`, `--format sarif,json`.
2. Post-filter: load champion encoder, batch inference, thresholding.
3. Exporters: SARIF + JSONL.
4. Action: minimal composite action with SARIF upload example.
5. Tests: one e2e golden SARIF over `examples/sample_repo`.

Stretch (time-boxed):
- ONNX runtime for faster CPU.
- Markdown “triage” report with top rationales per rule.