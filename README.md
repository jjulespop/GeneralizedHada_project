# Generalized HADA

Repository for development of the new (generalized) HADA version.

## Web Service
### Requirements
#### Docker
Docker needs to be installed on the system.
#### CPLEX
CPLEX is required, it can be obtained [here](https://www.ibm.com/products/ilog-cplex-optimization-studio) (free for academic use).


### Launching the service
#### Locally
CPLEX needs to be installed on the machine. 
If the latest version is used (22.1.2), Pyhton packages `cplex` and `docplex` are required. To upgrade the packages to their unlimited version, `docplex` must be linked to the installed CPLEX with:
```
docplex config --upgrade <path_to_cplex_installation_folder>
```

#### Docker
Docker can build the image once the file `cplex_studio2212.linux_x86_64.bin` is placed in the main directory and the execution permissions are granted with:
```
chmod +x cplex_studio2212.linux_x86_64.bin
```

Once the requirements are satisfied, the service can be launched with:
```
sudo docker compose up
```

Once everything is completed, the service can be found at `localhost:5000`.

### Model Training
Decision Trees are automatically trained, if not already present for a specific algorithm-hardware pair. Class `ml_models` oversees the training and the storing of the models.

### Rules Extraction
It is possible to extract new logic rules with CART, CReEPy, GridEx, and GridREx extractors, using the Python library `psyke` and the scripts in the `hada/core/rules_extraction` folder. The library requires Python <= `3.11` and JDK 11+ (with `JAVA_HOME` variable properly configured).

### Testing
Both the version with Logic Rules and with Decision Trees can be tested on a standard dataset, the `ValidationDataset`. Scripts can be found in the `tests` folder.

### Results
Folder `results` contains the results of all the computations done on the `ValidationDataset`, as well as the results of the analysis done on those outputs (plots, tables, csv).

### Analysis
Folder `analysis` contains the script to analyze the previous results. It is possible to calculate the execution time, n. variables, and n. constraints means, mean and max memory  usages, and the ratio of valid solutions, as well as plot bar diagrams for these results.

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
