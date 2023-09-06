# Vertical Matchmaking service

A service for hardware dimensioning and hyperparameters' selection for arbitrary algorithms.
Based on the HADA engine.

Final users can use the service in order to optimize the deployment of a given algorithm with respect to some target (e.g. minimizing execution time), under some constraints (e.g. <4GB memory usage).
For some algorithms the optimization process can also handle the input variables for the algorithm (the user can optionally provide their value).

The service can work in a standalone fashion, or by using an external Data Exchange service to handle resources.
New algorithms can be added by providing the needed resources (a configuration file and a dataset), more details in the corresponding section.

## Table of Contents
- [Vertical Matchmaking service](#vertical-matchmaking-service)
- [Web service](#web-service)
   - [Requirements](#requirements)
     - [Docker](#docker)
     - [CPLEX](#cplex)
     - [Data Exchange service](#data-exchange-service)
   - [Launching the service](#launching-the-service)
   - [Standalone mode (for developers)](#standalone-mode-for-developers)
- [GUI](#gui)
   - [Usage](#usage)
     - [Prices](#prices)
     - [Inputs](#inputs)
- [API](#api)
   - [Usage and examples](#usage-and-examples)
     - [`/algorithms`](#algorithms-discovery-of-available-algorithms)
     - [`/algorithms/<algorithm>`](#algorithmsalgorithm-get-informations-about-an-algorithm)
     - [`/optimize`](#optimize-request-an-optimization)
- [Adding new algorithms](#adding-new-algorithms)

## Web service
The service runs as a Flask application. It wraps the HADA engine, providing both a GUI and a REST API.
### Requirements
#### Docker
Docker needs to be installed on the system.
#### CPLEX
CPLEX is required, it can be obtained [here](https://www.ibm.com/products/ilog-cplex-optimization-studio) (free for academic use).
Docker can build the image once the file `cplex_studio2210.linux_x86_64.bin` is placed in the main directory and the execution permissions are granted with:
```
chmod +x cplex_studio2210.linux_x86_64.bin
```
#### Data Exchange service
  The Data Exchange service is expected to run at `localhost:5333` prior to the execution of this service.

### Launching the service
Once the requirements are satisfied, the service can be launched with:
```
sudo docker compose up
```
Once everything is completed, the service can be found at `localhost:5000`.

### Standalone mode (for developers)
The web service can run locally in a self-contained manner, using local resources (configuration files and datasets). This can be achieved by using the `from_local` init functions instead of `from_remote` (see the tests, as an example of both modalities).
To run the web service locally, install the required modules and run `flask run` from the `/vemm` folder.

To run the tests, launch `python3 tests/x_test.py` from the root folder.

## GUI
The service offers an intuitive GUI that exposes the capabilities of the engine.

![GUI image](images/gui.png)

### Usage
Once an algorithm is selected, the target and constraints sections are updated accordingly.

<!-- ![GUI image](images/prices.png) -->

Clicking on the "optimize" button will return either:
- A solution, including: the chosen platform, the chosen values for the hyperparameters, an estimated value for the optimization target, estimated values for the (eventually) constrainted targets. 
- A message reporting "no solution".
- A detailed error message.

#### Prices
If price is selected as a target and/or is constrainted, an ulterior section will appear, to insert prices for each hardware platform.

#### Inputs
When optimizing for an algorithm which is input-dependent, the values for the inputs can be submitted. This is done via a JSON file that can be uploaded using the form. The file needs to be structured in this way (example):
```
{"inputs": [
    {"name":"load_std", "value": 167},
    {"name":"load_mean", "value": 314},
    {"name":"pv_std", "value": 276},
    {"name":"pv_mean", "value": 268}
]}
```
where `name` is the name of a given input variable and `value` its value.

Details on the input variables can be found in the corresponding configuration file or by using the `/algorithms/<algorithm>` API endpoint.

## API

A REST API is available, all the functionalities of the engine can be accessed in this way, including ways to retrieve all the information needed to submit complete optimization requests.

| Endpoint | Description | Type |
|----------|-------------|------|
|`/algorithms`| Discovery of available algorithms | `GET`|
|`/algorithms/<algorithm>`| Get informations about an algorithm | `GET` |
|`/optimize` | Request an optimization | `POST` |

### Usage and examples
#### `/algorithms` (discovery of available algorithms)

Response (example):
```
{
  "algorithms": {
    "input-independent": [
      "saxpy",
      "toyalg",
      "fwt",
      "convolution",
      "correlation",
      "mockalgo1"
    ],
    "input-dependent": [
      "contingency",
      "anticipate"
    ]
  }
}
```
The same algorithm (same name) could be present both for input-dependent and input-independent cases.


#### `/algorithms/<algorithm>` (get informations about an algorithm)

Response (example for the `/algorithms/anticipate`):

```
{
  "algorithm": "anticipate",
  "input-independent": null,
  "input-dependent": {
    "hws": {
      "pc": {
        "default_price": null
      }
    },
    "hyperparameters": {
      "nScenarios": {
        "description": null,
        "type": "int",
        "lb": 1,
        "ub": 100
      }
    },
    "targets": {
      "sol": {
        "description": null,
        "lb": 150.0,
        "ub": 420.0
      },
      "time": {
        "description": null,
        "lb": 0.5,
        "ub": 230.0
      },
      "memory": {
        "description": null,
        "lb": 59.0,
        "ub": 345.0
      },
      "price": {
        "description": null,
        "lb": null,
        "ub": null
      }
    },
    "inputs": {
      "pv_mean": {
        "description": null,
        "type": "float",
        "lb": 240,
        "ub": 300
      },
      "pv_std": {
        "description": null,
        "type": "float",
        "lb": 0.0,
        "ub": 1000.0
      },
      "load_mean": {
        "description": null,
        "type": "float",
        "lb": 0.0,
        "ub": 400.0
      },
      "load_std": {
        "description": null,
        "type": "float",
        "lb": 0.0,
        "ub": 1000.0
      }
    }
  }
}
```
The example is for an algorithm which is present only in the input-dependent form; input-independent ones are described in the same manner, but lack an "inputs" field.

#### `/optimize` (request an optimization)

Request (example, input-dependent case):
```
curl -X POST -H 'Content-Type: application/json' -d '
{"algorithm":"anticipate",
"objective": {"target":"time", "type": "min"},
"robustness_fact": null,
"constraints": [
    {"target": "time", "type": "leq", "value": 120}
],
"prices": [
    {"hw":"pc", "price": 100}
],
"inputs": [
    {"name":"load_std", "value": 167},
    {"name":"load_mean", "value": 314},
    {"name":"pv_std", "value": 276},
    {"name":"pv_mean", "value": 268}
]}' localhost:5000/optimize
```

Response (example):
```
{
  "solution": {
    "hw": "pc",
    "nScenarios": 1,
    "time": 1.875
}
```

The presence of the `inputs` field implies the optimization request will be targeted at an input-dependent algorithm; otherwise, if not present, to an input-independent one.

## Adding new algorithms

This can be done using the Data Exchange service, by uploading a configuration file and a matching dataset; refer to the relative documentation.

Note: when a new configuration is added for a new hardware and an already supported algorithm, the string/categorical variables must have no new categories.
A workaround, at the moment, would be to manually delete the current categorical mapping for that algorithm.