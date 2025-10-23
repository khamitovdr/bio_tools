# Bioexperiment Experiment

Experiment orchestration framework for biological experiments with actions, measurements, and conditions.

## Installation

```bash
poetry add bioexperiment-experiment
```

Or with pip:

```bash
pip install bioexperiment-experiment
```

For websocket support (streaming measurements):

```bash
poetry add bioexperiment-experiment -E websocket
```

## Usage

### Basic experiment

```python
from bioexperiment_experiment import Experiment
from bioexperiment_tools import Pump, Spectrophotometer

# Create experiment
experiment = Experiment(output_dir="./results")

# Add devices (assuming they're initialized)
pump = Pump("/dev/ttyUSB0")
spectrophotometer = Spectrophotometer("/dev/ttyUSB1")

# Add actions
experiment.add_action(pump.pour_in_volume, volume=10.0, flow_rate=5.0, direction="right")
experiment.add_wait(60)  # Wait 60 seconds

# Add measurements
experiment.add_measurement(spectrophotometer.get_temperature, measurement_name="Temperature")
experiment.add_measurement(spectrophotometer.measure_optical_density, measurement_name="OD")

# Run experiment
experiment.start()
```

### Conditional actions

```python
from bioexperiment_experiment import Experiment, Condition
from bioexperiment_experiment.experiment.collections import Relation, Statistic

# Create a metric
metric = experiment.create_metric("Temperature", statistic=Statistic.LAST())

# Create condition
condition = Condition(metric, Relation.GREATER_THAN(30.0))

# Add conditional action
experiment.add_action(pump.stop_continuous_rotation, condition=condition)
```

## Development

This package is part of the bioexperiment monorepo. To set up for development:

```bash
cd packages/bioexperiment-experiment
poetry install
```

## License

MIT

