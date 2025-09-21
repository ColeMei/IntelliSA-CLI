# Schema (Pilot)

## Detection (from GLITCH adapter)
```json
{
  "rule_id": "HTTP_NO_TLS",
  "smell": "http",
  "tech": "ansible",
  "file": "roles/web/tasks/main.yml",
  "line": 42,
  "snippet": "get_url: url=http://example.com/app.tar.gz",
  "message": "HTTP used without TLS",
  "severity": "medium",
  "evidence": {"keys": ["url"], "values": ["http://example.com/app.tar.gz"]}
}
````

## Prediction (post-filter output per detection)

```json
{
  "label": "TP",
  "score": 0.87,
  "rationale": "Direct network fetch over http://; no checksum or SSL enforcement nearby."
}
```

## Joined JSONL (one line per finding)

```json
{
  "detection": { ... Detection ... },
  "prediction": { ... Prediction ... },
  "threshold": 0.62,
  "model": "codet5p-220m@1.0.0"
}
```