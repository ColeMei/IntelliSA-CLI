# Repository Guidelines

## Project Structure & Module Organization
- `apps/cli` hosts the Typer-based entrypoints; extend `main.py` when adding subcommands.
- Core libraries live under `packages/`: `glitch_adapter` wraps the vendored engine, `postfilter_llm` runs the model scorer, and `exporters` formats SARIF/JSONL.
- Vendored GLITCH source stays isolated in `packages/glitch_core` (retain upstream LICENSE/NOTICE).
- Models and weights sit in `models/`; fetch new weights via the registry before scanning.
- Tests mirror runtime layers: fast checks in `tests/unit`, end-to-end flows under `tests/e2e` using `examples/sample_repo`.

## Build, Test, and Development Commands
```bash
python -m venv .venv && source .venv/bin/activate  # create isolated env
pip install -U pip wheel && pip install -e .       # install in editable mode
python -m iacsec.models.fetch codet5p-220m         # hydrate champion weights
pytest                                             # run unit + e2e suites (-q via pyproject)
iacsec scan --path ./examples/sample_repo --tech auto --format sarif --out artifacts/iacsec.sarif
```

## Coding Style & Naming Conventions
- Target Python 3.10+, type-annotate public functions, and keep CLI commands declarative.
- Follow `.editorconfig`: LF endings, UTF-8, 2-space indents globally, 4 spaces for `*.py`.
- Use descriptive snake_case for Python modules and functions; prefer kebab-case for CLI flags.
- Keep adapter contracts aligned with `packages/schema`; document tricky flows with concise docstrings.

## Testing Guidelines
- Pytest is the single runner; tag purely synthetic cases as unit tests and keep E2E fixtures stable.
- Add regression tests beside the affected module (`tests/unit/...`) and update golden SARIF outputs cautiously.
- Run `pytest` before commits; for CLI changes, also execute the sample `iacsec scan` to ensure artifacts produce.

## Commit & Pull Request Guidelines
- Follow the existing history: short, imperative subjects (`Add pilot CLI and core components for scanning`).
- Reference related issues in the body, outline testing performed, and note model weight impacts.
- PRs should link to `docs/AI_AGENT_BRIEFING.md` steps when relevant and include screenshots or SARIF hashes for UI/workflow changes.
- Seek review for changes touching `packages/glitch_core` to avoid diverging from upstream.
