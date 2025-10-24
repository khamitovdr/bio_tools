# Development Setup Checklist

Quick setup guide for new contributors.

## Prerequisites

- [ ] Python 3.12+ installed
- [ ] [Poetry](https://python-poetry.org/docs/#installation) installed
- [ ] [Task](https://taskfile.dev/installation/) installed (optional but recommended)

## Setup Steps

### 1. Clone and Install Dependencies

```bash
# Install all dependencies
poetry install --with dev,docs

# Or use Task
task install
```

### 2. Install Pre-commit Hooks

```bash
# With Task
task pre-commit:install

# Or manually
poetry run pre-commit install
```

### 3. IDE Setup (Optional)

#### VS Code

1. Install extensions:
   - [Ruff](https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff)
   - [Mypy Type Checker](https://marketplace.visualstudio.com/items?itemName=ms-python.mypy-type-checker)
   - [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)

2. Copy VS Code settings:
   ```bash
   cp .vscode/settings.json.example .vscode/settings.json
   ```

#### PyCharm

1. Enable Ruff: Settings → Tools → Ruff
2. Enable Mypy: Settings → Tools → External Tools
3. Configure Python interpreter to use the project's Poetry venv

### 4. Verify Setup

```bash
# With Task - run all checks
task check

# Or manually
poetry run ruff check .
poetry run mypy packages/bioexperiment-tools-async/src
```

### 5. Run Tests

```bash
# With Task
task test

# Or manually
poetry run pytest packages/*/tests -v
```

## All-in-One Setup Command

```bash
task setup
```

This command will:
- Install all dependencies
- Install pre-commit hooks
- Display helpful next steps

## Quick Reference

### Common Commands

| Task | Command | Description |
|------|---------|-------------|
| Format code | `task fmt` | Auto-format with Ruff |
| Lint code | `task lint` | Check linting issues |
| Fix linting | `task lint:fix` | Auto-fix linting issues |
| Type check | `task type` | Run Mypy on all packages |
| Run tests | `task test` | Run all tests |
| All checks | `task check` | Lint + type check |
| All fixes | `task fix` | Format + lint:fix |
| CI simulation | `task ci` | Full CI pipeline locally |

### Without Task

| Task | Command |
|------|---------|
| Format code | `poetry run ruff format .` |
| Lint code | `poetry run ruff check .` |
| Fix linting | `poetry run ruff check --fix .` |
| Type check | `poetry run mypy packages/*/src` |
| Run tests | `poetry run pytest packages/*/tests` |

## Troubleshooting

### "Task not found"

Install Task:
- macOS: `brew install go-task`
- Linux: See [installation guide](https://taskfile.dev/installation/)
- Or: `npm install -g @go-task/cli`

### "Command not found: poetry"

Install Poetry:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### Pre-commit hooks failing

```bash
# Update and reinstall hooks
task pre-commit:update
task pre-commit:install
```

### Type checking errors

Legacy packages have relaxed type checking. If you see many errors in a package, check if it has mypy overrides in its `pyproject.toml`.

## Next Steps

1. Read [DEVELOPMENT.md](DEVELOPMENT.md) for detailed documentation
2. Check [examples/](examples/) directory for usage examples
3. Run `task --list` to see all available commands
4. Start coding! 🚀

## Getting Help

- **Project documentation:** Run `task docs:serve` and visit http://localhost:8000
- **Task help:** Run `task --list` for all commands
- **Issues:** Open an issue on GitHub
