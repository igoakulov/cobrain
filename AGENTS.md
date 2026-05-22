# AGENTS.md - CoBrain Development Guide

This file provides guidelines for agentic coding agents working on CoBrain.

---

## Breaking Changes Policy

**No soft-deprecation.** When making breaking changes:
- Delete old code fully
- No migration scripts, no deprecated warnings

---

## Key Design Decisions

### Files as Source of Truth

Topic markdown files are primary truth. graph.yaml is derived display cache.

### CLI-First for Token Efficiency

Use CLI for: metadata updates (avoids full file reads), graph traversal, backup.
Use files for: creating topics, editing content, searching.

### argparse over Click

For ~6 simple commands, argparse is sufficient. No extra dependency.

### Connections: Single Parent

Single `parent` field. Multiple parent needs → create intermediate topic.

---

## Code Style

### Naming
- snake_case for functions/methods
- PascalCase for classes and exceptions
- ALL_CAPS for constants
- Prefixes for private members: `_internal_state`
- Common prefixes: `add_`, `build_`, `get_`, `set_`, `is_`, `has_`, `can_`, `validate_`

### Types
- Built-in generics: `list[str]`, `dict[str, str]`, `str | None`
- Use built-in union syntax (`|`) over `typing.Union` or `typing.Optional`
- Use built-in generics over `typing.Dict`, `typing.List`, etc.
- `typing.Any` is acceptable for genuinely untyped values (e.g., arbitrary YAML data); prefer `object` as a supertype where applicable
- Annotate public functions with return types

### Imports
- Sort alphabetically within groups (stdlib, third-party, local)
- Avoid importing inside functions unless required by order or deferred heavy deps
- Use `from cobrain.module import something` for local imports

### Formatting
- Use ruff for formatting (`make format`)
- One class per file; one primary function per file
- Early returns as guards to avoid deep nesting
- Keep functions focused; extract helpers for repeated logic
- No comments unless explicitly requested

### Control Flow
- Early returns as guards
- Minimize nesting via small helpers
- Keep try/except narrow around risky statements

### Class Structure
```python
class ClassName:
    SOME_CONSTANT = "value"

    @staticmethod
    def build_default(...):
        ...

    @property
    def some_property(self) -> ...:
        ...

    def __init__(self, ...):
        ...

    def do_something(self, ...) -> ...:
        ...

    def close(self) -> None:
        ...
```

### Decorators and Registration
- Use decorators to register plugins/providers in a central registry
- Registration decorators should be idempotent and safe on repeated imports

---

## Error Handling

- Library layer: raise specific exceptions, add context when re-raising
- CLI layer: let exceptions bubble, print to stderr with non-zero exit
- Avoid broad `except Exception:`
- Use ValueError for invalid options/values (e.g., unknown output format)
- Use RuntimeError for operational conditions (e.g., missing optional dependencies)
- Centralize user-facing error mapping at CLI boundary

---

## Graph Modifications

Before write operations:
1. Backup
2. Validate
3. Write diff log

---

## Commands

### Running Tests

```bash
make test              # Run all tests (unit + integration)
make lint              # Run ruff linter
make format            # Run ruff formatter
make clean             # Clean cache files
```

**Single test:** Use Python's unittest with the pattern flag:
```bash
python -m unittest tests.test_validation.TestValidation.test_validation_cases -v
python -m unittest tests.test_chatgpt -v  # Run all tests in a file
```

### Running CLI

```bash
.venv/bin/cobrain <command> [options]
# or
source .venv/bin/activate && cobrain <command> [options]
```

### Type Checking

```bash
uv run pyright src/ tests/
```

---

## Testing

- Mock filesystem operations
- One assertion per test
- Descriptive names: `test_meta_get_returns_frontmatter`
- Tests may or may not always be source of truth. If unclear from known context, ask human before assuming tests are correct.

---

## Git Operations

- **Never use `git checkout`** (to reset files) without explicit human permission.
- This prevents accidental loss of uncommitted work.

---

## Important Patterns

### Runtime and Environment
- Set environment defaults via `os.environ.setdefault` to avoid overriding user settings
- Suppress noisy third-party logs unless errors occur
- Defer heavy or optional imports to call sites or helper methods to keep startup fast

### YAML Frontmatter
- Block between `---` delimiters
- Can appear anywhere in file
- Strip comments on parse
- Use YAML parser, not regex

### Graph Derivation
- Scan topics/*.md
- Parse frontmatter
- Build graph.yaml from files
- Never reverse (graph.yaml → files)

### Backup
- Scope: frontmatter only, not prose content
- Configurable retention (default 20)

### CLI Commands

- **sync:** `cobrain sync [--warnings]`
- **vault:** `cobrain vault [--ids <ids>] [--set key=value...]`
- **sources:** `cobrain sources [--warnings]`
- **show:** `cobrain show`
- **backup:** `cobrain backup`

**Sync triggers:** `cobrain sync`, `cobrain vault --set ...` (auto-syncs after update)

### CLI Output Patterns

- **Token efficiency:** Avoid repetition. Use lists/headers over repeated lines.
- **Section separation:** Blank line between distinct sections (summary + details).
- **Section headings:** Use caps `ERRORS:` / `WARNINGS:` as headers only.
- **Filepath placement:** For created files, filepath comes last.

**Error messages:** `Missing topic id`, `Duplicate topic id: {id}`, `Frontmatter not at top`, `Empty body`, `No sources`, `No parent`, `Parent not found: {parent}`

### UX Messaging
- Centralize user-visible strings in a dedicated module to unify tone and wording
- Keep constants in ALL_CAPS and grouped by domain (headers, messages, links)

---

## Package Management

**Use `.venv` and `uv sync`** to manage dependencies. Never use `pip install` directly.

Adding a new dependency:
1. Add to `pyproject.toml` dependencies
2. Run `uv sync` to install
3. Verify with `uv pip list`
