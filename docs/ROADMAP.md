# Research Roadmap

> Background on the research that led to iacsec and future directions.

## The Problem

Infrastructure-as-Code (IaC) security tools like GLITCH achieve high recall but generate excessive false positives, creating alert fatigue for development teams. Practitioners need tools that maintain high recall while dramatically reducing false alarms.

**Research Question**: Can LLMs filter false positives from IaC security detections without sacrificing recall?

## Research Journey

### Stage 1: Initial Exploration (Prompt Engineering)

**Hypothesis**: Generative LLMs with careful prompting can distinguish true positives from false positives.

**Approach**:
- Built two-stage pipeline: GLITCH detections → LLM decision (TP/FP)
- Tested prompt-based approaches with GPT-3.5, GPT-4
- Evaluated four security smells across Ansible, Chef, and Puppet:
  - HTTP without TLS
  - Weak cryptography
  - Hardcoded secrets
  - Suspicious comments

**Key Finding**: Prompt-only generative approaches tend to **parrot GLITCH's decisions**, achieving high recall but poor precision. The models struggled to contradict the initial detection even when clearly wrong.

**Conclusion**: Pure generative reasoning insufficient for this task.

### Stage 2: Model Training & Comparison

**Hypothesis**: Fine-tuned encoder models outperform generative approaches for binary classification.

**Approach**:
- Curated deduplicated train/validation/test datasets
- Tracked dataset manifests with SHA256 checksums for reproducibility
- Compared architectures:
  - **Encoders**: CodeBERT, CodeT5, CodeT5+ (220M)
  - **Generative**: CodeLLaMA (7B, 13B), Qwen2.5 (7B)
- Evaluated with precision, recall, F1, PR curves, bootstrap confidence intervals

**Key Finding**: **Encoder classifiers consistently outperform larger generative models** for FP filtering:
- Better precision at fixed recall
- More stable thresholds across technologies
- 100x smaller (220M vs 7B+ parameters)
- Faster inference, lower resource requirements

**Champion Model**: CodeT5p-220M
- Combined F1: 0.78
- Per-tech F1: Chef 0.70, Ansible 0.88, Puppet 0.76
- Threshold: 0.61 (calibrated across all technologies)

**Negative Result**: A refactored HTTP prompt that improved few-shot examples **collapsed recall** from 0.85 to 0.23. This ablation study confirmed that even carefully crafted prompts cannot match trained encoders.

### Stage 3: Production Evaluation

**Hypothesis**: The champion model generalizes to real-world repositories with diverse IaC patterns.

**Approach**:
- Evaluated on held-out test set
- Measured FP reduction at fixed recall thresholds
- Computed bootstrap confidence intervals
- Validated stability across Chef, Ansible, Puppet

**Key Findings**:
- **60-70% FP reduction** at 95% recall retention
- Consistent performance across technology stacks
- Stable thresholds eliminate per-deployment tuning
- Model exhibits minimal overfitting (validation/test gap < 2%)

**Conclusion**: Encoder post-filter ready for production deployment.

## Why Build a Tool?

Research artifacts alone don't change practice. We built iacsec to:

1. **Make research actionable**: Practitioners need runnable tools, not just papers and plots
2. **Enable reproducibility**: Pinned weights, versioned thresholds, deterministic outputs
3. **Support integration**: SARIF output works with GitHub Code Scanning and CI/CD pipelines
4. **Facilitate extension**: Clear schema boundaries allow swapping detectors or models
5. **Demonstrate feasibility**: Proof that research-backed tools can run without Docker/cloud dependencies

**Design Principles**:
- **End-to-end**: Vendored GLITCH + post-filter + exporters in one package
- **Deterministic**: Reproducible results via fixed seeds, frozen thresholds, SHA-verified weights
- **Interoperable**: Standard formats (SARIF, JSONL) for ecosystem compatibility
- **Transparent**: Debug logs expose all intermediate decisions
- **Extensible**: Pydantic schemas enable clean module boundaries

## Current Scope (Pilot)

**Implemented**:
- 11 GLITCH security rules (4 post-filtered, 7 high-precision passthrough)
- CodeT5p-220M encoder with frozen thresholds
- SARIF, JSONL, CSV exporters
- GitHub Action integration
- Comprehensive test suite (unit + e2e)

**Technologies**:
- Ansible (.yml, .yaml)
- Chef (.rb)
- Puppet (.pp)

## Future Directions

### Short Term (Next 6 Months)

1. **Additional smells**: Expand beyond current 11 rules to cover GLITCH's full rule set
2. **Threshold calibration**: Per-technology thresholds for optimal precision/recall trade-offs
3. **ONNX runtime**: Quantized model for 3-5x faster CPU inference
4. **Triage reports**: Markdown summaries with top rationales per finding

### Medium Term (6-12 Months)

5. **Model updates**: Retrain on expanded datasets (Terraform, Kubernetes manifests)
6. **Terraform support**: Extend beyond configuration management to IaC provisioning
7. **Kubernetes manifests**: YAML-based Kubernetes security patterns
8. **Confidence intervals**: Per-finding uncertainty estimates for risk-based prioritization

### Long Term (12+ Months)

9. **Active learning**: Human-in-the-loop feedback to improve model on organization-specific patterns
10. **Explainability**: Attention visualization and saliency maps for findings
11. **Multi-model ensembles**: Combine multiple architectures for improved robustness
12. **Real-time IDE integration**: LSP server for live feedback during development

### Research Extensions

- **Transfer learning**: Evaluate zero-shot performance on other IaC technologies (CloudFormation, Pulumi)
- **Adversarial robustness**: Test model against obfuscated vulnerabilities
- **Temporal drift**: Monitor performance degradation as IaC patterns evolve
- **Comparative analysis**: Benchmark against commercial tools (Snyk, Checkov, etc.)

## Open Questions

1. **Generalization**: How well do frozen thresholds work for organizations with different security standards?
2. **Maintenance burden**: What's the effort required to keep the model current as IaC ecosystems evolve?
3. **Edge cases**: Which vulnerability patterns consistently evade both GLITCH and the post-filter?
4. **Threshold adaptation**: Can we automatically tune thresholds based on organizational feedback?

## Publications & Artifacts

**Planned Publications**:
- Conference paper (target: ICSE 2026 or FSE 2026)
- Dataset release with annotations
- Model card and reproducibility package

**Open Artifacts**:
- This repository (code + models)
- Frozen training/test datasets (with licenses)
- Evaluation scripts and metrics

## Lessons Learned

1. **Encoders over generative models**: For binary classification tasks with labeled data, smaller encoder models outperform larger generative models
2. **Prompt engineering limits**: Even sophisticated prompts cannot overcome fundamental architectural constraints
3. **Determinism matters**: Reproducible research requires pinned seeds, frozen thresholds, and SHA-verified artifacts
4. **Tooling bridges research-practice**: Academic results need production-ready packaging to drive adoption
5. **Schema boundaries**: Clear contracts between modules enable independent evolution

## Community & Collaboration

We welcome contributions:
- **Bug reports**: File issues for incorrect classifications
- **Dataset contributions**: Share anonymized IaC examples (with permission)
- **Model improvements**: Propose alternative architectures or training procedures
- **Integration feedback**: Report CI/CD integration challenges

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

---

**Last Updated**: 2025-01  
**Next Review**: 2025-04 (post-initial deployments)
