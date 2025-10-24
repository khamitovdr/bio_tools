<!-- 4cf294da-2c1f-40e4-ada3-8fe289791f26 b3cfa9a9-2445-4987-b076-09997599fc1f -->
# Linting and Type Checking Setup

## Overview

Configure a modern, strict code quality setup for the monorepo with centralized configuration and per-package exceptions for legacy code.

## Tools Selection

- **Ruff**: Replaces black, isort, flake8, and pylint (all-in-one linter + formatter)
- **Mypy**: Static type checking with strict mode
- **toml-sort**: Keep pyproject.toml files organized
- **Pre-commit**: Automated git hooks
- **Taskfile**: Central task orchestration (go-task)

## Implementation Steps

### 1. Consolidate Configuration

**File: `/Users/khamitovdr/bio_tools/pyproject.toml`**

- Merge `mypy.ini` settings into `[tool.mypy]` section with strict settings from `bioexperiment-tools-async`
- Expand `[tool.ruff]` with comprehensive linting rules (based on tools-async config)
- Add `[tool.ruff.format]` configuration
- Add per-file ignores for tests, examples, and legacy code
- Add `toml-sort` to dev dependencies

**File: `/Users/khamitovdr/bio_tools/mypy.ini`**

- Delete after migration (no longer needed)

### 2. Configure Pre-commit Hooks

**File: `/Users/khamitovdr/bio_tools/.pre-commit-config.yaml`** (new)

- Hook for ruff linting (with auto-fix)
- Hook for ruff formatting
- Hook for mypy type checking
- Hook for toml-sort
- Hook for trailing whitespace and end-of-file fixer

### 3. Create Taskfile

**File: `/Users/khamitovdr/bio_tools/Taskfile.yml`** (new)

- `task fmt`: Format all code with ruff
- `task lint`: Run ruff linting (check mode)
- `task lint:fix`: Run ruff with auto-fixes
- `task type`: Run mypy type checking
- `task check`: Run all checks (lint + type)
- `task fix`: Run all auto-fixes (format + lint:fix)
- `task test`: Run pytest across all packages
- `task pre-commit:install`: Install pre-commit hooks
- `task pre-commit:run`: Run pre-commit on all files

### 4. Update Individual Package Configs

For packages with minimal configs (`bioexperiment-tools`, `bioexperiment-api`, `bioexperiment-experiment`, `bioexperiment-gui`):

- Remove redundant ruff config (inherit from root)
- Add package-specific mypy exceptions if needed (e.g., `disallow_untyped_defs = false` for legacy code)

For `bioexperiment-tools-async` (already has strict settings):

- Keep its strict settings as-is (already compliant)

### 5. Add CI/CD Support Files

**File: `/Users/khamitovdr/bio_tools/.github/workflows/lint.yml`** (optional, if using GitHub)

- Workflow to run checks on PRs

## Package-Level Exception Strategy

Individual packages can override root strict settings in their `pyproject.toml`:

```toml
[tool.mypy]
# Override strict settings for legacy code
disallow_untyped_defs = false
```

## Post-Setup Tasks

1. Run `task pre-commit:install` to install git hooks
2. Run `task fix` to auto-format entire codebase
3. Address any remaining mypy errors or add exceptions for legacy packages
4. Run `task check` to verify all checks pass

### To-dos

- [ ] Merge mypy.ini into pyproject.toml and expand ruff configuration with strict settings
- [ ] Create .pre-commit-config.yaml with ruff, mypy, and toml-sort hooks
- [ ] Create Taskfile.yml with commands for linting, formatting, type checking, and testing
- [ ] Update individual package pyproject.toml files to remove redundant configs and add exceptions where needed
- [ ] Document setup instructions and verify the tooling works correctly
