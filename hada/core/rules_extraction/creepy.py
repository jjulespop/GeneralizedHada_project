'''To be run with psyke and python <= 3.11'''

import os
import sys
import time
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sklearn.model_selection import train_test_split

from sklearn.tree import DecisionTreeRegressor
from sklearn.preprocessing import StandardScaler

from psyke import Extractor
from psyke.utils import Target
from psyke.utils.logic import pretty_theory
from psyke.utils.metrics import mae, mse, r2
from psyke import Clustering
from psyke.clustering import HyperCubeClustering
from psyke.extraction.hypercubic import HyperCubeExtractor

    

rule = 'creepy'
file_name = f"./giulia/logic_rules/lr_extraction_info_{rule}.csv"
targets = ['sol', 'time', 'memory']

for algorithm in ['anticipate', 'contingency']:

    df = pd.read_csv(f"./giulia/datasets/{algorithm}_pc.csv")
    parameter = 'nScenarios' if algorithm == 'anticipate' else 'nTraces'
    
    for objective in targets:  

        rules_path = f"./giulia/logic_rules/{rule}/{algorithm}_pc_{objective}.txt"  

        # set x and y
        if objective == 'sol':
            x = df.drop(columns=targets)
        else:
            x = df[[parameter]]
        y = df[objective]

        # final dataset
        dataset = x.join(y)

        start_time_tr = time.time()
        # split into train test
        train, test = train_test_split(dataset, test_size=0.5, random_state=10)

        scaler = StandardScaler().fit(train)
        train = pd.DataFrame(scaler.transform(train), columns=train.columns, index=train.index)
        test = pd.DataFrame(scaler.transform(test), columns=test.columns, index=test.index)

        normalization = {key: (m, s) for key, m, s in zip(train.columns, scaler.mean_, scaler.scale_)}

        # train predictor
        predictor = DecisionTreeRegressor().fit(train.iloc[:, :-1], train.iloc[:, -1])

        m, s = normalization[test.columns[-1]]

        predicted = predictor.predict(test.iloc[:, :-1]).flatten() * s + m
        true = test.iloc[:, -1] * s + m
        end_time_tr = time.time()

        print(f'MAE = {mae(true, predicted):.2f}')
        print(f'MSE = {mse(true, predicted):.2f}')
        print(f'R2 = {r2(true, predicted):.2f}')

        # cart extractor
        start_time_ex = time.time()
        creepy = Extractor.creepy(predictor, clustering=Clustering.exact, depth=3, error_threshold=0.02, output=Target.REGRESSION, normalization=normalization)
        theory_from_creepy = creepy.extract(train)
        end_time_ex = time.time()
        print('CReEPy extracted rules:\n\n' + pretty_theory(theory_from_creepy))
        

        # save theory rules to txt
        with open(rules_path, "w") as f:
            f.write(pretty_theory(theory_from_creepy))

        # save results
        data = {
            'extractor': rule,
            'algorithm': algorithm,
            'target': objective,
            'max_depth': 3,
            'error_threshold': 0.02,
            'training_time': (end_time_tr - start_time_tr),
            'extraction_time': (end_time_ex - start_time_ex)
        }
        results = pd.DataFrame([data])

        # append results or create new file
        if not os.path.exists(file_name):
            res_df = results
        else:
            res_df = pd.read_csv(file_name)
            res_df = pd.concat([res_df, results], ignore_index = True)

        # save to csv
        res_df.to_csv(path_or_buf=file_name, index=False)