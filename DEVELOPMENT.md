# Development Guide

This guide covers the development workflow, code quality tools, and best practices for the BioExperiment monorepo.

## Quick Start

### Initial Setup

1. **Install dependencies:**
   ```bash
   poetry install --with dev,docs
   ```

2. **Install Task (if not already installed):**
   - macOS: `brew install go-task`
   - Linux: See [Task installation guide](https://taskfile.dev/installation/)
   - Or use npm: `npm install -g @go-task/cli`

3. **Install pre-commit hooks:**
   ```bash
   task pre-commit:install
   ```
   Or use the combined setup command:
   ```bash
   task setup
   ```

## Code Quality Tools

The monorepo uses a modern, strict code quality setup with the following tools:

### Ruff (Linting & Formatting)
- **Replaces:** black, isort, flake8, pylint
- **Purpose:** Fast all-in-one linter and code formatter
- **Configuration:** `[tool.ruff]` in `pyproject.toml`

### Mypy (Type Checking)
- **Purpose:** Static type checking with strict mode enabled
- **Configuration:** `[tool.mypy]` in `pyproject.toml`
- **Package exceptions:** Legacy packages have relaxed settings in their individual `pyproject.toml` files

### Pre-commit Hooks
- **Purpose:** Automated checks on git commit
- **Configuration:** `.pre-commit-config.yaml`
- **Runs:** Ruff (lint + format), Mypy, toml-sort, and basic file checks

## Common Commands

All development tasks are available through the Taskfile. Run `task` or `task --list` to see all available commands.

### Code Quality

```bash
# Auto-format code
task fmt

# Check linting (no fixes)
task lint

# Auto-fix linting issues
task lint:fix

# Run type checking
task type

# Run all checks (lint + type)
task check

# Run all auto-fixes (format + lint:fix)
task fix
```

### Testing

```bash
# Run all tests
task test

# Run tests for a specific package
task test:package PACKAGE=bioexperiment-tools-async

# Run tests with coverage
task test:cov
```

### Pre-commit

```bash
# Run pre-commit on all files
task pre-commit:run

# Update pre-commit hook versions
task pre-commit:update
```

### CI Simulation

```bash
# Run the full CI pipeline locally
task ci
```

This checks:
- Code formatting (check mode)
- Linting
- Type checking
- All tests

### Documentation

```bash
# Serve documentation locally
task docs:serve

# Build documentation
task docs:build
```

### Cleanup

```bash
# Clean build artifacts and cache files
task clean
```

## Git Workflow

### Before Committing

Pre-commit hooks will automatically run on changed files when you commit. To manually check your changes:

```bash
# Run all fixes
task fix

# Run all checks
task check
```

### If Pre-commit Fails

If pre-commit hooks fail:
1. Review the error messages
2. Run `task fix` to auto-fix issues
3. Manually fix any remaining issues
4. Stage the changes: `git add .`
5. Commit again: `git commit -m "your message"`

### Bypassing Hooks (Not Recommended)

Only bypass hooks if absolutely necessary:
```bash
git commit --no-verify -m "your message"
```

## Configuration Structure

### Root Level (`pyproject.toml`)
- **Strict settings** for new code
- Comprehensive linting rules
- Strict type checking enabled
- Applies to all packages by default

### Package Level
- **Inherits** root configuration
- **Can override** specific settings for legacy code
- Example: `bioexperiment-tools` has relaxed mypy settings

### Per-file Ignores
Configured in root `pyproject.toml`:
- `tests/**/*`: Allow assert statements, magic values, etc.
- `examples/**/*`: Allow print statements
- `**/conftest.py`: Allow unused arguments

## Type Checking Strategy

### Strict Packages
- `bioexperiment-tools-async` - fully typed with strict checks

### Legacy Packages (Relaxed Settings)
- `bioexperiment-tools`
- `bioexperiment-api`
- `bioexperiment-experiment`
- `bioexperiment-gui`

These packages have `disallow_untyped_defs = false` in their `pyproject.toml` to allow gradual adoption of type hints without CI failures.

### Gradually Improving Types

To improve typing in legacy packages:
1. Add type hints to new code
2. Incrementally add types to existing code
3. Once a module is fully typed, you can enable stricter checks for that module

## IDE Integration

### VS Code
Install extensions:
- [Ruff](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff)
- [Mypy](https://marketplace.visualstudio.com/items?itemName=ms-python.mypy-type-checker)

Add to `.vscode/settings.json`:
```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": true,
      "source.organizeImports": true
    }
  }
}
```

### PyCharm
1. Enable "Ruff" in Settings → Tools → Ruff
2. Enable "Mypy" in Settings → Tools → External Tools
3. Configure to use the project's `pyproject.toml`

## Continuous Integration

GitHub Actions automatically runs the CI pipeline on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

The CI pipeline:
1. Checks code formatting
2. Runs linting
3. Runs type checking
4. Runs all tests
5. Generates coverage reports

See `.github/workflows/lint.yml` for details.

## Troubleshooting

### Dependency Conflicts
```bash
# Update lock files
task lock

# Reinstall dependencies
poetry install --with dev,docs
```

### Pre-commit Issues
```bash
# Update hooks to latest versions
task pre-commit:update

# Reinstall hooks
task pre-commit:install
```

### Type Checking Errors in Legacy Code
If mypy reports too many errors in a legacy package, you can temporarily disable specific checks in that package's `pyproject.toml`:
```toml
[tool.mypy]
disallow_untyped_defs = false
check_untyped_defs = false
```

## Best Practices

1. **Run `task fix` before committing** - Auto-fixes most issues
2. **Run `task check` to verify** - Ensures all checks pass
3. **Write tests** for new functionality
4. **Add type hints** to new code
5. **Keep commits small** and focused
6. **Write descriptive commit messages**
7. **Run `task ci` before pushing** - Simulates the CI pipeline

## Additional Resources

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Mypy Documentation](https://mypy.readthedocs.io/)
- [Pre-commit Documentation](https://pre-commit.com/)
- [Task Documentation](https://taskfile.dev/)
- [Poetry Documentation](https://python-poetry.org/docs/)
