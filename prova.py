from core.hada import HADA
from core.configdb import ConfigDB
from core.optimization_request import OptimizationRequest, UserConstraints, HardwarePrices, Inputs
from core.datasets import Datasets
from core.logic_models import LogicModels
import tracemalloc
import pandas as pd

#to inprove
if __name__ == '__main__':
    tracemalloc.start()
    configs_path = './algorithms/configs'
    data_path = './algorithms/data'
    models_path = 'algorithms/logic_rules'
    storage_ws_url = 'http://localhost:5333'

    ##### Init #####
    db = ConfigDB.from_local(configs_path)
    # db = ConfigDB.from_remote(storage_ws_url)

    datasets = Datasets.from_local(db, data_path)
    # datasets = Datasets.from_remote(db, storage_ws_url)

    models = LogicModels(db, models_path)
    df = pd.read_csv("algorithms/data/ValidationSet.csv")
    for index, row in df.iterrows():
        print(row["nInst"])