# Schema Reference

> Pydantic data models for detections, predictions, and pipeline outputs.

## Overview

All pipeline data flows through immutable, validated Pydantic models defined in `packages/schema/models.py`.

**Properties**:
- `frozen=True`: Instances are immutable after creation
- `extra="forbid"`: Unknown fields cause validation errors
- Strict enums: Technology, severity, and labels use literal types

## Detection

Normalized security finding from GLITCH or other analyzers.

### Type Definition

```python
from typing import Literal, Dict, Any
from pydantic import BaseModel, Field

Smell = Literal[
    "http",
    "weak-crypto",
    "hardcoded-secret",
    "suspicious-comment",
    "admin-by-default",
    "empty-password",
    "invalid-bind",
    "no-integrity-check",
    "missing-default-switch",
]

Tech = Literal["ansible", "chef", "puppet"]
Severity = Literal["low", "medium", "high"]

class Detection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    
    rule_id: str                    # Human-readable rule identifier
    smell: Smell                    # Vulnerability category
    tech: Tech                      # IaC technology
    file: str                       # Relative path from scan root
    line: int                       # Line number (>= 1)
    snippet: str                    # Source code excerpt
    message: str                    # Human-readable description
    severity: Severity              # Risk level
    evidence: Dict[str, Any] = {}   # Tool-specific metadata
```

### Example

```json
{
  "rule_id": "HTTP_NO_TLS",
  "smell": "http",
  "tech": "ansible",
  "file": "roles/web/tasks/main.yml",
  "line": 42,
  "snippet": "url: http://example.com/app.tar.gz",
  "message": "HTTP used without TLS",
  "severity": "medium",
  "evidence": {
    "glitch_code": "sec_http_no_ssl",
    "postfilter": true,
    "keys": ["url"],
    "values": ["http://example.com/app.tar.gz"]
  }
}
```

### Field Descriptions

**`rule_id`**: Uppercase identifier for the security rule (e.g., `HTTP_NO_TLS`, `WEAK_CRYPTO`)

**`smell`**: Category from predefined enum. Maps multiple rule IDs to semantic groups.

**`tech`**: IaC technology that produced this finding.

**`file`**: Path relative to scan root (not absolute). Use `/` separators on all platforms.

**`line`**: 1-indexed line number where finding occurs. Must be >= 1.

**`snippet`**: Source code line(s) showing the vulnerability. May span multiple lines (newline-separated).

**`message`**: Human-readable explanation suitable for display in UIs.

**`severity`**: Risk level. Used for prioritization and `--fail-on-high` filtering.

**`evidence`**: Flexible dict for tool-specific metadata:
- `glitch_code`: Original GLITCH rule code
- `postfilter`: `true` if detection requires ML scoring, `false`/absent if high-precision
- Additional keys vary by detector (keys, values, contexts, etc.)

## Prediction

Post-filter judgment for a single detection.

### Type Definition

```python
Label = Literal["TP", "FP"]

class Prediction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    
    label: Label                     # True Positive or False Positive
    score: float                     # Confidence score (0.0-1.0)
    rationale: Optional[str] = None  # Human-readable explanation
```

### Example

```json
{
  "label": "TP",
  "score": 0.87,
  "rationale": "score>=threshold"
}
```

### Field Descriptions

**`label`**: Classification result.
- `"TP"`: True Positive (real security issue)
- `"FP"`: False Positive (benign pattern)

**`score`**: Model confidence between 0.0 (definitely FP) and 1.0 (definitely TP).

**`rationale`**: Explanation for the decision:
- `"score>=threshold"`: Score exceeded threshold
- `"score<threshold"`: Score below threshold
- `"glitch-accepted"`: High-precision rule, bypassed post-filter
- Custom rationales possible for future models

## Joined Output (JSONL)

JSONL exports combine detection, prediction, and metadata on each line.

### Structure

```json
{
  "detection": { /* Detection object */ },
  "prediction": { /* Prediction object */ },
  "threshold": 0.61,
  "model": "codet5p-220m@1.0.0"
}
```

### Example

```json
{
  "detection": {
    "rule_id": "HTTP_NO_TLS",
    "smell": "http",
    "tech": "ansible",
    "file": "roles/web/tasks/main.yml",
    "line": 42,
    "snippet": "url: http://example.com/app.tar.gz",
    "message": "HTTP used without TLS",
    "severity": "medium",
    "evidence": {
      "glitch_code": "sec_http_no_ssl",
      "postfilter": true
    }
  },
  "prediction": {
    "label": "TP",
    "score": 0.87,
    "rationale": "score>=threshold"
  },
  "threshold": 0.61,
  "model": "codet5p-220m@1.0.0"
}
```

### Field Descriptions

**`detection`**: Full `Detection` object as defined above.

**`prediction`**: Full `Prediction` object as defined above.

**`threshold`**: Effective threshold used for this detection (may vary per-smell or per-tech).

**`model`**: Model identifier with version (`name@version`).

## SARIF Mapping

SARIF 2.1.0 export maps schema fields as follows:

| Schema Field | SARIF Path |
|--------------|------------|
| `rule_id` | `result.ruleId` |
| `message` | `result.message.text` |
| `severity` | `result.level` (low→note, medium→warning, high→error) |
| `file` | `result.locations[0].physicalLocation.artifactLocation.uri` |
| `line` | `result.locations[0].physicalLocation.region.startLine` |
| `snippet` | `result.locations[0].physicalLocation.region.snippet.text` |
| `prediction.label` | Omitted (only TPs exported) |
| `prediction.score` | `result.properties.score` |
| `prediction.rationale` | `result.properties.rationale` |

**Note**: Only detections with `prediction.label == "TP"` appear in SARIF output.

## CSV Mapping

CSV export produces three columns:

| Column | Description |
|--------|-------------|
| `file` | Detection file path (or scanned file if no findings) |
| `line` | Detection line number (0 = no findings in this file) |
| `category` | Human-readable category (from `CATEGORY_LABELS`) or "none" |

**Example**:
```csv
file,line,category
roles/web/tasks/main.yml,42,Use of HTTP without SSL/TLS
roles/db/tasks/creds.yml,15,Empty password
roles/app/tasks/config.yml,0,none
```

## Validation Rules

### Detection Constraints

- `line >= 1` (enforced by Pydantic `Field(ge=1)`)
- `file` must be non-empty string
- `smell` must be one of the enum values
- `tech` must be one of: ansible, chef, puppet
- `severity` must be one of: low, medium, high

### Prediction Constraints

- `score` must be in range [0.0, 1.0]
- `label` must be "TP" or "FP"
- `rationale` is optional (None allowed)

### Immutability

All fields are immutable after creation:

```python
detection = Detection(...)
detection.line = 99  # Raises ValidationError
```

## Extension Examples

### Adding a New Smell

Update `packages/schema/models.py`:

```python
Smell = Literal[
    "http",
    "weak-crypto",
    # ... existing ...
    "new-smell-category",  # Add here
]
```

Then update adapters to produce detections with `smell="new-smell-category"`.

### Adding Evidence Fields

Evidence dict is flexible. Just populate in adapter:

```python
Detection(
    # ... required fields ...
    evidence={
        "glitch_code": "sec_custom",
        "postfilter": True,
        "context_lines": ["line1", "line2", "line3"],
        "cwe": "CWE-79"  # Add any metadata
    }
)
```

No schema changes needed unless you want strict validation.

### Custom Prediction Rationales

Override in post-filter:

```python
Prediction(
    label="TP",
    score=0.95,
    rationale="High entropy string detected (entropy=7.2)"
)
```

## See Also

- **Implementation**: `packages/schema/models.py`
- **Usage examples**: `tests/unit/test_schema_models.py`
- **SARIF spec**: [OASIS SARIF 2.1.0](https://docs.oasis-open.org/sarif/sarif/v2.1.0/)
