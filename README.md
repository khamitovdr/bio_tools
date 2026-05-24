# BioExperiment Suite

Python toolbox for managing biological experiment devices (pumps, cell density detectors etc.) and setting up experiments.

## Table of Contents

- [Introduction](#introduction)
- [Features](#features)
- [Installation](#installation)
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
- Graphical user interface (in development)

## Installation

To install the package, you can use `pip`:

```sh
pip install bioexperiment-suite
```

or with GUI support:

```sh
pip install bioexperiment-suite[gui]
```

### Prerequisites

Ensure you have the following installed on your machine:

- Python 3.12 or higher
- [Windows CH340 Driver](https://sparks.gogo.co.nz/ch340.html) (for Windows users if not installed already)

## Usage

### Connecting to your lab machine

Lab machines are addressed by name. The client looks the name up in the lab-bridge roster and opens an HTTP session to that machine's `lab_devices_client` service:

```python
from bioexperiment_suite.interfaces import LabDevicesClient

with LabDevicesClient(user="khamit_desktop") as client:
    devices = client.discover()
    (pump1, pump2) = devices.pumps
    (densitometer,) = devices.densitometers
```

If you don't know which name to use, ask the bridge:

```python
LabDevicesClient.list_registered_users()  # every machine the bridge knows about
LabDevicesClient.list_active_users()      # only the ones currently answering
```

Lookups go through `http://siteapp:8000/api/clients/` by default; override with the `LAB_DEVICES_DISCOVERY_URL` environment variable or the `discovery_url=` keyword argument when running outside the standard `labnet` setup.

### Building an experiment

For comprehensive usage examples, please see the [examples](examples) directory.

## License

This project is licensed under the [MIT License](LICENSE).
