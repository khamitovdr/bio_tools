# Bioexperiment GUI

Graphical user interface for biological experiment orchestration and device control.

## Installation

```bash
poetry add bioexperiment-gui
```

Or with pip:

```bash
pip install bioexperiment-gui
```

## Usage

### Launch the GUI

```bash
bioexperiment-gui
```

Or from Python:

```python
from bioexperiment_gui import main

main()
```

## Features

- Device discovery and management for pumps and spectrophotometers
- Interactive controls for pumps (continuous rotation, volume pouring, flow rate)
- Real-time measurements from spectrophotometers (temperature, optical density)
- Experiment configuration and execution with automated measurements
- CSV output for measurement data

## Development

This package is part of the bioexperiment monorepo. To set up for development:

```bash
cd packages/bioexperiment-gui
poetry install
```

## License

MIT
