# iacsec User Handbook

> Complete operational guide for installation, usage, troubleshooting, and CI/CD integration.

## Prerequisites

- **Python**: 3.10 or newer
- **Operating System**: Linux, macOS, or Windows with WSL
- **Dependencies**: Automatically installed via pip (torch, transformers, safetensors, typer, pydantic, etc.)

**Hardware**:
- CPU-only supported (no GPU required)
- GPUs automatically used if PyTorch detects them
- Minimum 2GB RAM recommended

## Installation

### Standard Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Upgrade pip and install
pip install --upgrade pip setuptools wheel
pip install -e .
```

### Installing PyTorch

If you see stub model warnings, install PyTorch:

```bash
# CPU-only (recommended for most users)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# GPU (CUDA 11.8)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# GPU (CUDA 12.1)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

See [PyTorch installation guide](https://pytorch.org/get-started/locally/) for other configurations.

## Fetching Model Weights

Download the champion model from Hugging Face:

```bash
python -m iacsec.models.fetch codet5p-220m
```

**What this does**:
- Downloads model weights (`model.safetensors`) from HuggingFace
- Caches to `~/.cache/iacsec/` by default
- Verifies SHA256 checksum
- Tests that transformers can load the model

**Output**:
```
[iacsec] Model 'codet5p-220m' ready (backend=hf).
[iacsec] Cached weights at: /Users/you/.cache/iacsec/codet5p-220m_v1.0.0.safetensors
```

### Advanced: Custom Cache Location

Set `IACSEC_MODEL_CACHE` to override the default cache directory:

```bash
export IACSEC_MODEL_CACHE=/mnt/fast-ssd/models
python -m iacsec.models.fetch codet5p-220m
```

**When to use this**:
- CI/CD pipelines with dedicated cache volumes
- Limited home directory space
- Shared model cache across multiple projects

## Running Scans

### Basic Scan

```bash
iacsec --path /path/to/repo --tech auto --format sarif --out scan.sarif
```

### Scan Current Directory

```bash
iacsec --format sarif --out artifacts/scan.sarif
```

### Multiple Output Formats

```bash
iacsec \
  --path ./my-infrastructure \
  --tech ansible \
  --format sarif \
  --format json \
  --format csv \
  --out artifacts/scan
```

**Produces**:
- `artifacts/scan.sarif`
- `artifacts/scan.jsonl`
- `artifacts/scan.csv`

### Console Table Output

```bash
iacsec --path . --tech auto --format table
```

Displays findings in a terminal-friendly table (not written to file).

## CLI Options Reference

### Required Options

None (all have sensible defaults).

### Path Options

**`--path PATH`**  
Directory or file to scan. Default: `.` (current directory)

```bash
iacsec --path /home/user/ansible-playbooks
iacsec --path single-file.yml
```

**`--tech {auto|ansible|chef|puppet}`**  
Technology to scan. Default: `auto` (detects from file extensions)

- `auto`: Scans `.yml`/`.yaml` (Ansible), `.rb` (Chef), `.pp` (Puppet)
- `ansible`: Only `.yml`/`.yaml` files
- `chef`: Only `.rb` files
- `puppet`: Only `.pp` files

### Output Options

**`--format {sarif|json|csv|table}`**  
Output format(s). Repeatable. Default: `sarif`

- `sarif`: GitHub Code Scanning format (SARIF 2.1.0)
- `json`: JSONL with detection/prediction/metadata per line
- `csv`: Spreadsheet-friendly summary
- `table`: Terminal table (console only, not written to file)

**`--out PATH`**  
Base output path. Default: `artifacts/iacsec`

If `--out` is a directory, outputs use default names:
```bash
--out artifacts/  →  artifacts/iacsec.sarif, artifacts/iacsec.jsonl
```

If `--out` is a file prefix, extensions are appended:
```bash
--out results/scan  →  results/scan.sarif, results/scan.jsonl
```

### Post-Filter Options

**`--postfilter MODEL_NAME`**  
Model from `models/registry.yaml`. Default: `codet5p-220m`

```bash
iacsec --postfilter codet5p-220m-stub  # Deterministic stub for testing
```

**`--threshold FLOAT`**  
Override model's default threshold (0.0-1.0)

```bash
iacsec --threshold 0.7  # Higher threshold = fewer FPs, more FNs
iacsec --threshold 0.5  # Lower threshold = fewer FNs, more FPs
```

### Detection Options

**`--rules RULE_IDS`**  
Comma-separated rule IDs. Default: all rules

```bash
iacsec --rules http,weak-crypto,hardcoded-secret
```

**Available rules**:
- `http` - HTTP without TLS
- `weak-crypto` - Weak cryptography
- `hardcoded-secret` - Hardcoded secrets
- `suspicious-comment` - Suspicious comments
- `admin-by-default` - Admin by default
- `empty-password` - Empty password
- `invalid-bind` - Unrestricted IP bind
- `no-integrity-check` - Missing integrity check
- `missing-default-switch` - Missing default case

**Note**: Currently informational only (all rules run regardless).

### Behavior Options

**`--fail-on-high`**  
Exit code 1 only for high-severity findings

Without this flag:
- Exit 1 if ANY true positive detected

With this flag:
- Exit 1 only if high-severity TP detected
- Medium/low severity findings don't fail the scan

```bash
iacsec --fail-on-high  # CI-friendly: only fail on critical issues
```

**`--debug-log PATH`**  
Write detailed trace to JSONL file

```bash
iacsec --debug-log artifacts/debug.jsonl
```

**Debug log contents**:
- GLITCH raw detections
- Post-filter inputs (snippets + context)
- Model predictions (score, label, rationale)
- Export file paths
- Timing information

## Understanding Output Formats

### SARIF (GitHub Code Scanning)

Standard format for security tools. Upload to GitHub Code Scanning:

```yaml
- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: artifacts/scan.sarif
```

**Structure**:
```json
{
  "runs": [{
    "tool": { "driver": { "name": "iacsec" } },
    "results": [{
      "ruleId": "HTTP_NO_TLS",
      "level": "warning",
      "message": { "text": "HTTP used without TLS" },
      "locations": [{
        "physicalLocation": {
          "artifactLocation": { "uri": "roles/web/tasks/main.yml" },
          "region": { "startLine": 42 }
        }
      }]
    }]
  }]
}
```

### JSONL (Structured Logs)

One detection per line with prediction metadata:

```json
{"detection": {...}, "prediction": {"label": "TP", "score": 0.87}, "threshold": 0.61, "model": "codet5p-220m@1.0.0"}
```

**Use cases**:
- Data pipelines
- Custom analytics
- Audit trails

### CSV (Spreadsheet)

Columns: `file`, `line`, `category`

```csv
file,line,category
roles/web/tasks/main.yml,42,Use of HTTP without SSL/TLS
roles/db/tasks/main.yml,15,Empty password
roles/app/tasks/config.yml,0,none
```

**Features**:
- Lists all scanned files (findings + clean files)
- Line 0 with "none" = no findings
- Easy triage in Excel/Google Sheets

## Troubleshooting

### Stub Model Warning

**Symptom**:
```
Warning: falling back to deterministic stub model; install torch+transformers for codet5p-220m.
```

**Cause**: PyTorch or transformers not installed, or incompatible version

**Fix**:
```bash
pip install torch transformers
python -m iacsec.models.fetch codet5p-220m  # Re-verify
```

### Model Fetch Fails

**Symptom**:
```
[iacsec] Failed to load model 'codet5p-220m': HTTP Error 404
```

**Possible causes**:
1. Network issue (firewall, proxy)
2. HuggingFace down
3. Model moved/deleted

**Fix**:
```bash
# Check network
curl https://huggingface.co

# Retry with verbose output
python -m iacsec.models.fetch codet5p-220m

# Use custom cache location if home directory has issues
export IACSEC_MODEL_CACHE=/tmp/models
python -m iacsec.models.fetch codet5p-220m
```

### GLITCH Parser Errors

**Symptom**: Files skipped during scan

**Check debug log**:
```bash
iacsec --debug-log debug.jsonl --path .
grep "GLITCH parser failed" debug.jsonl
```

**Common causes**:
- Syntax errors in IaC files
- Unsupported Ansible/Chef/Puppet constructs
- File encoding issues

**Fix**: Validate IaC files with native tools first (ansible-lint, cookstyle, puppet-lint).

### No Findings Detected

**Verify GLITCH is working**:
```bash
iacsec --path examples/sample_repo --tech ansible --format table --debug-log debug.jsonl
```

Expected: 3-4 detections from sample repo.

**If still no results**:
1. Check `--tech` matches your IaC type
2. Verify file extensions (`.yml`, `.rb`, `.pp`)
3. Review debug log for parser errors

## CI/CD Integration

### GitHub Actions

```yaml
name: IaC Security Scan

on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install iacsec
        run: |
          pip install -e .
          pip install torch transformers
          python -m iacsec.models.fetch codet5p-220m
      
      - name: Scan IaC
        run: |
          iacsec \
            --path . \
            --tech auto \
            --format sarif \
            --format json \
            --out artifacts/scan.sarif \
            --fail-on-high \
            --debug-log artifacts/debug.jsonl
      
      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: artifacts/scan.sarif
      
      - name: Archive artifacts
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: iacsec-results
          path: artifacts/
```

### GitLab CI

```yaml
iacsec_scan:
  image: python:3.10
  before_script:
    - pip install -e .
    - pip install torch --index-url https://download.pytorch.org/whl/cpu
    - python -m iacsec.models.fetch codet5p-220m
  script:
    - iacsec --path . --format sarif --format json --out scan --fail-on-high
  artifacts:
    reports:
      sast: scan.sarif
    paths:
      - scan.sarif
      - scan.jsonl
```

### Jenkins

```groovy
pipeline {
    agent any
    stages {
        stage('Setup') {
            steps {
                sh 'python3 -m venv .venv'
                sh '. .venv/bin/activate && pip install -e .'
                sh '. .venv/bin/activate && pip install torch transformers'
                sh '. .venv/bin/activate && python -m iacsec.models.fetch codet5p-220m'
            }
        }
        stage('Scan') {
            steps {
                sh '. .venv/bin/activate && iacsec --path . --format sarif --out scan.sarif --fail-on-high'
            }
        }
    }
    post {
        always {
            archiveArtifacts artifacts: 'scan.sarif', allowEmptyArchive: true
        }
    }
}
```

## Best Practices

### Performance

- **Batch size**: Default 16 is optimal for CPU. Increase for GPU:
  ```bash
  export IACSEC_POSTFILTER_BATCH=64
  iacsec --path .
  ```

- **Cache models**: In CI, persist `~/.cache/iacsec/` between runs:
  ```yaml
  - uses: actions/cache@v3
    with:
      path: ~/.cache/iacsec
      key: iacsec-models-${{ hashFiles('models/registry.yaml') }}
  ```

### Security

- **Pin model versions**: Update `models/registry.yaml` SHA256 when upgrading
- **Review findings**: Always inspect high-severity TPs before deployment
- **Audit trails**: Archive debug logs for compliance

### Threshold Tuning

Default thresholds are calibrated for balanced precision/recall. Adjust per your risk tolerance:

| Threshold | Precision | Recall | Use Case |
|-----------|-----------|--------|----------|
| 0.5 | Lower | Higher | Exploratory, find all potential issues |
| 0.61 (default) | Balanced | Balanced | Production |
| 0.7 | Higher | Lower | Critical systems, minimize false alarms |

## Verification Checklist

Before production deployment:

- [ ] `iacsec --help` runs without warnings
- [ ] `python -m iacsec.models.fetch codet5p-220m` succeeds
- [ ] Sample scan produces expected findings:
  ```bash
  iacsec --path examples/sample_repo --tech ansible --format table
  ```
- [ ] PyTorch and transformers installed (no stub warning)
- [ ] CI pipeline caches model weights
- [ ] SARIF uploads to code scanning successfully
- [ ] Team trained on interpreting findings

## Support

- **Issues**: Report bugs at repository issue tracker
- **Architecture**: See [DEVELOPMENT_REPORT.md](DEVELOPMENT_REPORT.md)
- **Research**: See [ROADMAP.md](ROADMAP.md) for background
