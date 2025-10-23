# Bioexperiment Tools

Tools and interfaces for biological experiment devices including pumps and spectrophotometers.

## Installation

```bash
poetry add bioexperiment-tools
```

Or with pip:

```bash
pip install bioexperiment-tools
```

## Usage

### Import devices

```python
from bioexperiment_tools import Pump, Spectrophotometer, get_connected_devices
```

### Discover connected devices

```python
pumps, spectrophotometers = get_connected_devices()
```

### Use a pump

```python
pump = Pump("/dev/ttyUSB0")
pump.set_default_flow_rate(5.0)  # mL/min
pump.pour_in_volume(10.0, direction="right")  # Pour 10 mL
```

### Use a spectrophotometer

```python
spectrophotometer = Spectrophotometer("/dev/ttyUSB1")
temperature = spectrophotometer.get_temperature()
optical_density = spectrophotometer.measure_optical_density()
```

## Development

This package is part of the bioexperiment monorepo. To set up for development:

```bash
cd packages/bioexperiment-tools
poetry install
```

## License

MIT

