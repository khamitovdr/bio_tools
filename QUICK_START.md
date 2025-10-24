# Quick Start Guide

## ✅ Implementation Complete!

All linting, formatting, and type checking tools have been successfully configured.

## 🚀 Getting Started (3 Steps)

### 1. Install Dependencies

```bash
poetry install --with dev,docs
```

This installs:
- Ruff (linter & formatter)
- Mypy (type checker)
- Pre-commit (git hooks)
- toml-sort (TOML formatter)
- Testing tools

### 2. Install Pre-commit Hooks

```bash
task pre-commit:install
```

Or manually:
```bash
poetry run pre-commit install
```

### 3. Verify Setup

```bash
# List all available commands
task --list

# Run all checks
task check
```

## 📋 Daily Workflow

### Before Committing

```bash
# Auto-fix all issues (format + lint)
task fix

# Verify all checks pass
task check
```

### Pre-commit Hooks (Automatic)

When you commit, these run automatically:
- ✓ Ruff formatting
- ✓ Ruff linting
- ✓ Mypy type checking
- ✓ TOML sorting
- ✓ File cleanup (trailing whitespace, EOF, etc.)

### Common Commands

| Command | What it does |
|---------|-------------|
| `task fix` | Auto-format and fix linting issues |
| `task check` | Run all quality checks |
| `task test` | Run all tests |
| `task ci` | Simulate full CI pipeline |
| `task fmt` | Format code only |
| `task lint` | Check linting only |
| `task type` | Type check only |

## 🔧 What's Been Configured

### Root Level Configuration
- ✅ **pyproject.toml**: Strict Ruff + Mypy settings
- ✅ **.pre-commit-config.yaml**: Automated git hooks
- ✅ **Taskfile.yml**: Task orchestration (all fixed!)
- ✅ **.github/workflows/lint.yml**: CI/CD pipeline

### Package Level
All packages inherit root config with legacy exceptions:
- ✅ `bioexperiment-tools`: Relaxed mypy
- ✅ `bioexperiment-api`: Relaxed mypy
- ✅ `bioexperiment-experiment`: Relaxed mypy
- ✅ `bioexperiment-gui`: Relaxed mypy
- ✅ `bioexperiment-tools-async`: Strict (already compliant)

### Documentation
- ✅ **DEVELOPMENT.md**: Complete development guide
- ✅ **SETUP.md**: Detailed setup checklist
- ✅ **IMPLEMENTATION_SUMMARY.md**: Full change summary
- ✅ **QUICK_START.md**: This file!

## 🎯 Tools Overview

### Ruff
**Replaces:** black, isort, flake8, pylint
- Super fast (written in Rust)
- Auto-fixes most issues
- 30+ rule categories enabled

### Mypy
**Type Checking:** Strict mode for new code
- Catches type errors before runtime
- Legacy packages have relaxed settings
- Gradual adoption path

### Pre-commit
**Git Hooks:** Runs checks automatically
- Prevents bad code from being committed
- Fast feedback loop
- Can skip with `--no-verify` if needed

### Task
**Task Runner:** Single entrypoint
- Cross-platform
- Simple YAML syntax
- Better than Makefiles

## 🐛 Troubleshooting

### "task: command not found"

Install Task:
```bash
# macOS
brew install go-task

# Or via npm
npm install -g @go-task/cli

# Or download binary: https://taskfile.dev/installation/
```

### Pre-commit hooks failing?

```bash
# Fix most issues automatically
task fix

# Then commit again
git add .
git commit -m "your message"
```

### Mypy errors in legacy package?

That's expected! Legacy packages have relaxed type checking. You can:
1. Add type hints gradually
2. Or ignore for now - won't break CI

### Want to skip hooks temporarily?

```bash
git commit --no-verify -m "your message"
```

⚠️ Use sparingly - the hooks are there to help!

## 📚 More Information

- **Detailed Guide**: [DEVELOPMENT.md](DEVELOPMENT.md)
- **Setup Checklist**: [SETUP.md](SETUP.md)
- **All Changes**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

## 🎉 You're All Set!

The monorepo now has professional-grade code quality tooling. Just run:

```bash
task setup
```

And start coding! 🚀

---

**Need help?** Run `task --list` to see all available commands.
