# BioExperiment Suite Examples

This directory contains example scripts and notebooks demonstrating how to use the BioExperiment Suite packages.

## Setup

Before running the examples, you need to install the required packages. Make sure you're in the root of the monorepo.

### Install all packages

```bash
cd packages/bioexperiment-tools && poetry install && cd ../..
cd packages/bioexperiment-experiment && poetry install && cd ../..
cd packages/bioexperiment-gui && poetry install && cd ../..
```

Alternatively, if the packages are published to PyPI:

```bash
poetry add bioexperiment-tools bioexperiment-experiment bioexperiment-gui
```

### Environment Configuration

Copy the sample environment file and configure it:

```bash
cp sample.env .env
```

Edit `.env` to set:
- `EMULATE_DEVICES=true` for testing without physical devices
- `N_VIRTUAL_PUMPS` and `N_VIRTUAL_SPECTROPHOTOMETERS` for the number of emulated devices

## Examples

### experiment_example.py

Basic example showing how to set up and run an automated experiment with pumps and a spectrophotometer.

```bash
python examples/experiment_example.py
```

### experiment_example.ipynb

Interactive Jupyter notebook demonstrating conditional experiment logic based on optical density measurements.

```bash
jupyter notebook examples/experiment_example.ipynb
```

### three_pumps_experiment.py

Advanced example using three pumps (waste removal, food, drug) with conditional actions based on optical density threshold.

```bash
python examples/three_pumps_experiment.py
```

## Key Concepts

All examples demonstrate:
- Device discovery with `get_connected_devices()`
- Creating an `Experiment` instance
- Adding measurements with `add_measurement()`
- Adding actions with `add_action()`
- Using wait times with `add_wait()`
- Conditional actions based on metrics
- Running experiments with `start()`

## Device Emulation

For testing without physical hardware, set environment variables:

```bash
export EMULATE_DEVICES=true
export N_VIRTUAL_PUMPS=2
export N_VIRTUAL_SPECTROPHOTOMETERS=1
```

Or use the `.env` file with these settings.
