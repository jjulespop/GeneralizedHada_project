# Generalized HADA

Repository for development of the new (generalized) HADA version.

## Web Service
### Requirements
#### Docker
Docker needs to be installed on the system.
#### CPLEX
CPLEX is required, it can be obtained [here](https://www.ibm.com/products/ilog-cplex-optimization-studio) (free for academic use).
Docker can build the image once the file `cplex_studio2210.linux_x86_64.bin` is placed in the main directory and the execution permissions are granted with:
```
chmod +x cplex_studio2210.linux_x86_64.bin
```

### Launching the service
Once the requirements are satisfied, the service can be launched with:
```
sudo docker compose up
```

Once everything is completed, the service can be found at `localhost:5000`.

### GUI usage
When optimizing for an algorithm which is input-dependent, the values for the inputs must be submitted. This is done via a JSON file that can be uploaded using the form. The file needs to be structured in this way (example):
```
{"inputs": [
    {"name":"load_std", "value": 167},
    {"name":"load_mean", "value": 314},
    {"name":"pv_std", "value": 276},
    {"name":"pv_mean", "value": 268}
]}
```
where `name` is the name of a given input variable and `value` its value.
### API usage

#### Get list of algorithms
Route: `http://localhost:5000/algorithms`

`GET` request.

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


#### Get informations about an algorithm
Route: `http://localhost:5000/algorithms/<algorithm>`

`GET` request.

Response (example for the "anticipate" algorithm):
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

### Request an optimization (algorithm-specific)

Route: `http://localhost:5000/optimize`

`POST` request (application/json).

The presence of the "inputs" field implies the optimization request will be targeted at an input-dependent algorithm; otherwise, if not present, to an input-independent one.

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