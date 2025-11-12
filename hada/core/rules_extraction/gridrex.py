'''To be run with psyke and python <= 3.11'''

import os
import time
import pandas as pd

from psyke.utils.dataframe import get_discrete_features_supervised, get_discrete_features_equal_frequency, get_discrete_dataset
from sklearn.model_selection import train_test_split

from sklearn.tree import DecisionTreeRegressor
from sklearn.preprocessing import StandardScaler

from psyke import Extractor
from psyke.tuning import Objective
from psyke.tuning.pedro import PEDRO
from psyke.utils.logic import pretty_theory
from psyke.utils.metrics import mae, mse, r2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hada.config import config_loader

config = config_loader.load_config(config_path="./hada/config/config.yaml")
    

rule = 'gridrex'
data_path = config['paths'['data']]
lr_path = config['paths']['logic_rules']
lr_info_path = config['paths']['logic_rules_extraction_info']
result_file_name = f"{lr_info_path}/lr_extraction_info_{rule}.csv"
targets = ['sol', 'time', 'memory']

for algorithm in ['anticipate', 'contingency']:

    df = pd.read_csv(f"{data_path}/{algorithm}_pc.csv")
    parameter = 'nScenarios' if algorithm == 'anticipate' else 'nTraces'
    
    for objective in targets:  

        rules_path = f"{lr_path}/{rule}/{algorithm}_pc_{objective}.txt"    

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

        # PEDRO
        start_time_pedro = time.time()
        pedro = PEDRO(predictor, train, min_rule_decrease=0.9, readability_tradeoff=0.1,
                      max_depth=2, patience=1, algorithm=PEDRO.Algorithm.GRIDREX, objective=Objective.MODEL)
        pedro.search()
        (_, _, threshold, grid) = pedro.get_best()[0]
        end_time_pedro = time.time()

        # cart extractor
        start_time_ex = time.time()
        gridREx = Extractor.gridrex(predictor, grid, threshold=threshold, normalization=normalization)
        theory_from_gridREx = gridREx.extract(train)
        end_time_ex = time.time()
        print('GridREx extracted rules:\n\n' + pretty_theory(theory_from_gridREx))

        # save theory rules to txt
        with open(rules_path, "w") as f:
            f.write(pretty_theory(theory_from_gridREx))

        # save results
        data = {
            'extractor': rule,
            'algorithm': algorithm,
            'target': objective,
            'pedro_used': True,
            'threshold': threshold,
            'training_time': (end_time_tr - start_time_tr),
            'pedro_time': (end_time_pedro - start_time_pedro),
            'extraction_time': (end_time_ex - start_time_ex)
        }
        results = pd.DataFrame([data])

        # append results or create new file
        if not os.path.exists(result_file_name):
            res_df = results
        else:
            res_df = pd.read_csv(result_file_name)
            res_df = pd.concat([res_df, results], ignore_index = True)

        # save to csv
        res_df.to_csv(path_or_buf=result_file_name, index=False)

    