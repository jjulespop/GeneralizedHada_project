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

### API usage

#### Get list of algorithms
Route: `http://localhost:5000/algorithms`

`GET` request.

Response (example):
```
{
  "algorithms": [
    "correlation",
    "fwt",
    "convolution",
    "mockalgo1",
    "saxpy"
  ]
}
```


#### Get informations about an algorithm
Route: `http://localhost:5000/algorithms/<algorithm>`

`GET` request.

Response (example for "fwt" algorithm):
```
{
  "algorithm": "fwt",
  "hyperparameters": {
    "var_0": {
      "lb": 3,
      "ub": 52
    },
    "var_1": {
      "lb": 3,
      "ub": 52
    }
  },
  "targets": {
    "memory": {
      "lb": 24.450379,
      "ub": 52.31878
    },
    "price": {
      "lb": null,
      "ub": null
    },
    "time": {
      "lb": 60.57580995559693,
      "ub": 864.9205942153931
    }
  }
}
```

### Request an optimization (algorithm-specific)

Route: `http://localhost:5000/optimize`

`POST` request (application/json).

Request (example):
```
curl -X POST -H 'Content-Type: application/json' -d 
'{"algorithm":"correlation",
  "objective": {"target":"memory", "type": "min"},
  "robustness_fact": null,
  "constraints": [
    {'target': "time", "type": "leq", "value": 120},
    ...
   ],
   "price_per_hw": [
    {"hw":"pc", "price": 30},
    ...
   ]
   }'
http://localhost:5000/optimize
```

Response (example):
```
{
  "solution": {
    "hw": "vm",
    "memory": 18.916514999999983,
    "price": 30.0,
    "time": 83.51820898,
    "var_0": 3.0,
    "var_1": 3.0,
    "var_2": 3.0,
    "var_3": 3.0,
    "var_4": 3.0,
    "var_5": 3.0,
    "var_6": 10.0
  }
}
```