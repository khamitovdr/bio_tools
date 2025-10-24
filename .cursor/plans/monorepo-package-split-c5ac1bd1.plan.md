<!-- c5ac1bd1-dc8e-42be-969b-40a9da5e1b4b e43acb33-2a81-425a-a302-b034ad966948 -->
# Monorepo Package Split Refactoring

## Overview

Transform the current monolithic structure into a monorepo with three independent packages: `bioexperiment-tools`, `bioexperiment-experiment`, and `bioexperiment-gui`, while maintaining docs at the root level.

## Target Structure

```
bio_tools/
├── packages/
│   ├── bioexperiment-tools/
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   └── src/
│   │       └── bioexperiment_tools/
│   │           ├── __init__.py
│   │           ├── interfaces/
│   │           ├── tools/
│   │           ├── loader.py (duplicated)
│   │           ├── settings.py (duplicated)
│   │           └── device_interfaces.json
│   │
│   ├── bioexperiment-experiment/
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   └── src/
│   │       └── bioexperiment_experiment/
│   │           ├── __init__.py
│   │           ├── experiment/
│   │           ├── loader.py (duplicated)
│   │           └── settings.py (duplicated)
│   │
│   └── bioexperiment-gui/
│       ├── pyproject.toml
│       ├── README.md
│       └── src/
│           └── bioexperiment_gui/
│               ├── __init__.py
│               └── gui/
│
├── docs/ (unchanged)
├── examples/ (updated imports)
├── README.md (updated)
└── mkdocs.yml (unchanged)
```

## Dependency Relationships

- `bioexperiment-tools`: No dependencies on other packages (base package)
  - Dependencies: loguru, munch, pyserial, python-dotenv
- `bioexperiment-experiment`: Depends on `bioexperiment-tools`
  - Dependencies: bioexperiment-tools, websockets
- `bioexperiment-gui`: Depends on both `bioexperiment-tools` and `bioexperiment-experiment`
  - Dependencies: bioexperiment-tools, bioexperiment-experiment, ttkbootstrap

## Implementation Steps

### 1. Create Monorepo Structure

- Create `packages/` directory at root
- Create subdirectories for each package with proper `src/` layout
- Preserve underscore naming in package names (bioexperiment_tools, etc.)

### 2. Package: bioexperiment-tools

**Files to move:**

- `src/bioexperiment_suite/interfaces/` → `packages/bioexperiment-tools/src/bioexperiment_tools/interfaces/`
- `src/bioexperiment_suite/tools/` → `packages/bioexperiment-tools/src/bioexperiment_tools/tools/`
- `src/bioexperiment_suite/loader.py` → duplicate here
- `src/bioexperiment_suite/settings.py` → duplicate here
- `src/bioexperiment_suite/device_interfaces.json` → move here
- `src/bioexperiment_suite/py.typed` → duplicate here

**Update imports:**

- Change all `from bioexperiment_suite.` to `from bioexperiment_tools.` within this package
- Update `interfaces/__init__.py` and `tools/__init__.py` exports

**Create pyproject.toml:**

- Name: `bioexperiment-tools`
- Version: 0.1.0 (fresh start)
- Dependencies: loguru, munch, pyserial, python-dotenv
- Include device_interfaces.json and py.typed

### 3. Package: bioexperiment-experiment

**Files to move:**

- `src/bioexperiment_suite/experiment/` → `packages/bioexperiment-experiment/src/bioexperiment_experiment/experiment/`
- `src/bioexperiment_suite/loader.py` → duplicate here
- `src/bioexperiment_suite/settings.py` → duplicate here (if needed for future expansion)
- `src/bioexperiment_suite/py.typed` → duplicate here

**Update imports:**

- Change `from bioexperiment_suite.experiment.` to `from bioexperiment_experiment.experiment.`
- Keep imports from `bioexperiment_tools` (external dependency)
- Update `experiment/__init__.py` to maintain clean API

**Create pyproject.toml:**

- Name: `bioexperiment-experiment`
- Version: 0.1.0
- Dependencies: bioexperiment-tools, websockets, loguru
- Extras: websocket feature

### 4. Package: bioexperiment-gui

**Files to move:**

- `src/bioexperiment_suite/gui/` → `packages/bioexperiment-gui/src/bioexperiment_gui/gui/`
- `gui.py` (root level) → integrate or document

**Update imports:**

- Change `from bioexperiment_suite.interfaces` to `from bioexperiment_tools.interfaces`
- Change `from bioexperiment_suite.experiment` to `from bioexperiment_experiment.experiment`
- Update `gui/__init__.py`

**Create pyproject.toml:**

- Name: `bioexperiment-gui`
- Version: 0.1.0
- Dependencies: bioexperiment-tools, bioexperiment-experiment, ttkbootstrap
- Script: `run_gui` entry point

### 5. Update Documentation

**Files to update:**

- `docs/api/interfaces/*.md` - update import examples to `bioexperiment_tools`
- `docs/api/experiment/*.md` - update import examples to `bioexperiment_experiment`
- `docs/api/tools.md` - update import examples to `bioexperiment_tools`
- Root `README.md` - add monorepo structure explanation and installation instructions
- Create individual README.md for each package

### 6. Update Examples

Move examples to root level and update all imports:

- `examples/experiment_example.py` - update imports to use new package names
- `examples/experiment_example.ipynb` - update imports to use new package names
- `examples/three_pumps_experiment.py` - update imports to use new package names
- `examples/sample.env` - verify if changes needed
- Create `examples/README.md` with setup instructions using poetry

### 7. Root Configuration

**Options:**

- Create root `pyproject.toml` as a workspace coordinator (Poetry doesn't support workspaces, but can document structure)
- OR keep current `pyproject.toml` as deprecated wrapper that depends on all three packages
- Update `mypy.ini` to handle multiple packages

### 8. Cleanup

- Remove old `src/bioexperiment_suite/` directory
- Update `dist/` builds or clear old builds
- Update `.gitignore` if needed for multiple package builds

## Key Considerations

**Import Compatibility:**

- Old imports like `from bioexperiment_suite.interfaces import Pump` will break
- Users need migration guide in documentation
- Consider publishing one final version with deprecation warnings

**Version Management:**

- Start all packages at 0.1.0
- Document compatibility between package versions
- Consider using compatible version ranges in dependencies

**Development Workflow:**

- Install all packages in editable mode using poetry:
  ```bash
  cd packages/bioexperiment-tools && poetry install
  cd ../bioexperiment-experiment && poetry install
  cd ../bioexperiment-gui && poetry install
  ```

- Or use poetry's path dependencies in a root pyproject.toml for coordinated development
- Document this workflow in root README.md

**Publishing:**

- Each package publishes independently to PyPI
- Build from each package directory: `cd packages/bioexperiment-tools && poetry build`
- Coordinate releases when changes affect multiple packages

### To-dos

- [ ] Create monorepo directory structure with packages/ and subdirectories
- [ ] Set up bioexperiment-tools package: move files, create pyproject.toml, update imports
- [ ] Set up bioexperiment-experiment package: move files, create pyproject.toml, update imports
- [ ] Set up bioexperiment-gui package: move files, create pyproject.toml, update imports
- [ ] Update documentation with new import paths and monorepo structure
- [ ] Update examples/ with new imports from split packages
- [ ] Update root configuration files (README, mypy.ini, etc.)
- [ ] Remove old src/bioexperiment_suite directory and clean up artifacts
