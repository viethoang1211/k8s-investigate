# Contributing to k8s-investigate

Thank you for your interest in contributing! This document covers how to set up your development environment, the code conventions used, and the process for submitting changes.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Code Style](#code-style)
- [Adding a New Scanner](#adding-a-new-scanner)
- [Submitting Changes](#submitting-changes)

---

## Development Setup

**Requirements:** Python 3.10+, a working `kubectl` context (for manual testing)

```bash
git clone https://github.com/viethoang1211/k8s-investigate.git
cd k8s-investigate

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

---

## Project Structure

```
k8s_investigate/
├── cli.py           # Click CLI entrypoint, scan orchestration
├── config.py        # ScanOptions dataclass
├── scanner.py       # BaseScanner, UnusedResource, scanner registry
├── k8s_client.py    # Kubernetes API client wrapper
├── formatters.py    # Table/JSON/YAML output formatters
├── delete.py        # Resource deletion logic
├── exporter.py      # Prometheus metrics exporter
└── scanners/        # One file per resource type
    ├── configmaps.py
    ├── secrets.py
    ├── pods.py
    └── ...
tests/
├── test_config.py
├── test_formatters.py
└── test_scanner.py
```

---

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ -v --cov=k8s_investigate --cov-report=term-missing

# Run a specific test file
python -m pytest tests/test_scanner.py -v
```

---

## Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and import sorting.

```bash
# Check for issues
ruff check k8s_investigate/

# Auto-fix fixable issues (import sorting, etc.)
ruff check k8s_investigate/ --fix
```

**Key conventions:**
- All files start with `from __future__ import annotations`
- Type hints are required for all public functions
- System-managed resources (e.g. `kube-root-ca.crt`, default StorageClasses) must be explicitly excluded in scanners — never flag resources the user cannot safely delete
- CI runs `ruff check` and `pytest` on every push — both must pass before merging

---

## Adding a New Scanner

Each resource type lives in its own file under `k8s_investigate/scanners/`. To add a new one:

**1. Create the scanner file**

```python
# k8s_investigate/scanners/myresource.py
"""MyResource scanner - describe what "unused" means here."""

from __future__ import annotations

from k8s_investigate.scanner import BaseScanner, UnusedResource, register_scanner


@register_scanner
class MyResourceScanner(BaseScanner):
    resource_type = "myresources"   # used as CLI argument
    namespaced = True               # False for cluster-scoped resources

    def scan(self, namespace: str = "") -> list[UnusedResource]:
        results = []
        items = self.k8s.core_v1.list_namespaced_my_resource(namespace).items

        for item in items:
            if self.should_skip(item.metadata):
                continue
            if self.is_marked_unused(item.metadata):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="MyResource",
                    name=item.metadata.name, reason="Marked as unused via label",
                ))
                continue
            # Your detection logic here
            if _is_unused(item):
                results.append(UnusedResource(
                    namespace=namespace, resource_type="MyResource",
                    name=item.metadata.name, reason="<clear reason for the user>",
                ))
        return results
```

**2. Register the import**

Add the import to `k8s_investigate/scanners/__init__.py`:

```python
from k8s_investigate.scanners import myresource  # noqa: F401
```

**3. Add CLI aliases** (optional)

Add short name aliases to the `_ALIASES` dict in `k8s_investigate/cli.py`:

```python
"mr": "myresources",
"myresource": "myresources",
```

**4. Write tests**

Add test coverage in `tests/`. At minimum, test that:
- Unused resources are correctly detected
- System/excluded resources are skipped
- `should_skip()` filters work correctly

**5. Update README**

Add an entry to the "Supported Resource Types" table in `README.md`.

---

## Submitting Changes

1. Fork the repository and create a branch from `main`:
   ```bash
   git checkout -b feat/my-new-scanner
   ```

2. Make your changes, ensuring tests and lint pass:
   ```bash
   ruff check k8s_investigate/ --fix
   python -m pytest tests/ -v
   ```

3. Commit with a clear message:
   ```
   feat(scanners): add MyResource scanner
   fix(pvcs): skip PVCs owned by scaled-down StatefulSets
   ```

4. Open a Pull Request against `main` with a description of what the change does and why.

---

## Reporting Issues

When opening a bug report, please include:
- The command you ran (`k8s-investigate scan ...`)
- Kubernetes version and cloud provider (EKS, AKS, GKE, etc.)
- Whether the resource flagged is genuinely unused or a false positive
- Any relevant output (use `--output json` for structured results)
