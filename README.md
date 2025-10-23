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
- Real-time data streaming via WebSocket
- Graphical user interface (in development)

## Installation

To install the package, you can use `pip`:

```sh
pip install bioexperiment-suite
```

or with optional features:

```sh
# With GUI support
pip install bioexperiment-suite[gui]

# With WebSocket streaming support
pip install bioexperiment-suite[websocket]

# With all optional features
pip install bioexperiment-suite[gui,websocket]
```

### Prerequisites

Ensure you have the following installed on your machine:

- Python 3.12 or higher
- [Windows CH340 Driver](https://sparks.gogo.co.nz/ch340.html) (for Windows users if not installed already)

## Usage

For comprehensive usage examples, please see the [examples](examples) directory.

## License

This project is licensed under the [MIT License](LICENSE).
