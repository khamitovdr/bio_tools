# BioExperiment Suite

Python toolbox for managing biological experiment devices (pumps, cell density detectors etc.) and setting up experiments.

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Monorepo Structure](#monorepo-structure)
- [Installation](#installation)
- [Development](#development)
- [Usage](#usage)
- [License](#license)

## Introduction

This project is a Python toolbox for managing biological experiment devices (pumps, cell density detectors etc.) and setting up experiments. Communication protocol is specific for devices produced by my lab in [Institute of Protein Research RAS](https://protres.ru/en), so it may not be suitable for other devices, but you can easily adapt it for your needs by overriding corresponding methods. The toolbox is designed to be easily extensible and customizable.

## Features

- Abstraction above COM-port communication
- Automatic device discovery
- High-level API for device control
- Easy-to-use experiment setup
- Scrupulous logging
- Real-time data streaming via WebSocket
- Graphical user interface

## Monorepo Structure

This repository is structured as a monorepo containing three independent packages:

- **bioexperiment-tools** (`packages/bioexperiment-tools/`) - Core tools and device interfaces for pumps and spectrophotometers
- **bioexperiment-experiment** (`packages/bioexperiment-experiment/`) - Experiment orchestration framework with actions, measurements, and conditions
- **bioexperiment-gui** (`packages/bioexperiment-gui/`) - Graphical user interface for device control and experiment management

Each package can be installed and used independently.

## Installation

You can install the packages individually based on your needs:

### Installing with pip

```sh
# Tools and device interfaces only
pip install bioexperiment-tools

# Experiment framework (includes tools as dependency)
pip install bioexperiment-experiment

# GUI (includes both tools and experiment as dependencies)
pip install bioexperiment-gui
```

### Installing with poetry

```sh
# Tools and device interfaces only
poetry add bioexperiment-tools

# Experiment framework (includes tools as dependency)
poetry add bioexperiment-experiment

# GUI (includes both tools and experiment as dependencies)
poetry add bioexperiment-gui
```

For websocket support with experiments:

```sh
poetry add bioexperiment-experiment -E websocket
```

### Prerequisites

Ensure you have the following installed on your machine:

- Python 3.12 or higher
- [Windows CH340 Driver](https://sparks.gogo.co.nz/ch340.html) (for Windows users if not installed already)

## Development

> **📘 New to the project?** See [QUICK_START.md](QUICK_START.md) for a streamlined setup guide.

### Quick Start

To set up the development environment:

```sh
# Install Task (task runner) - macOS
brew install go-task

# Or on Linux/other platforms, see: https://taskfile.dev/installation/

# Complete setup (dependencies + pre-commit hooks)
task setup
```

### Development Workflow

The monorepo uses modern code quality tools with automated checks:

```sh
# Format and fix linting issues
task fix

# Run all quality checks (lint + type checking)
task check

# Run tests
task test

# Run full CI pipeline locally
task ci
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed documentation on:
- Code quality tools (Ruff, Mypy, pre-commit)
- Available commands and workflows
- IDE integration
- Best practices and troubleshooting

### Manual Setup (without Task)

```sh
# Install all packages in coordinated development mode
poetry install --with dev,docs

# Install pre-commit hooks
pre-commit install

# Run examples and tests
poetry run python examples/experiment_example.py
poetry run jupyter notebook examples/
```

### Building Documentation

Documentation is maintained at the root level and covers all packages:

```sh
# Serve documentation locally (with Task)
task docs:serve

# Or manually
mkdocs serve
```

## Usage

### Basic Device Control

```python
from bioexperiment_tools import Pump, Spectrophotometer, get_connected_devices

# Discover devices
pumps, spectrophotometers = get_connected_devices()

# Use a pump
pump = pumps[0]
pump.set_default_flow_rate(5.0)
pump.pour_in_volume(10.0, direction="right")
```

### Running Experiments

```python
from bioexperiment_experiment import Experiment
from bioexperiment_tools import Pump, Spectrophotometer

experiment = Experiment(output_dir="./results")
experiment.add_action(pump.pour_in_volume, volume=10.0, flow_rate=5.0)
experiment.add_measurement(spectrophotometer.measure_optical_density,
                          measurement_name="OD")
experiment.start()
```

### Launching the GUI

```sh
bioexperiment-gui
```

For more comprehensive usage examples, please see the [examples](examples) directory.

## License

This project is licensed under the [MIT License](LICENSE).
