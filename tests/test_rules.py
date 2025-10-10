import os
import sys
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hada.core.configdb import ConfigDB
from hada.core.logic_models import *
from hada.config import config_loader

config = config_loader.load_config(config_path="./hada/config/config.yaml")


if __name__ == '__main__':

    # load paths from config
    data_path = config['paths']['data']
    algorithms_configs_path = config['paths']['algorithms_configs']
    logic_rules_path = config['paths']['logic_rules']
    storage_ws_url = config['paths']['storage_ws_url']

    # variables setup
    algorithm = config["algorithms"]["anticipate"]
    rules_type = config["rules_types"]["cart"]
    target = 'sol'

    param = "nScenarios" if algorithm == "anticipate" else "nTraces"

    ### Init ###
    # db config
    db = ConfigDB.from_local(algorithms_configs_path)
    # db = ConfigDB.from_remote(storage_ws_url)

    lr = LogicModels(db, logic_rules_path, rules_type)
    rules = lr.get_rules(algorithm, 'pc', target)

    # print original rules
    print("ORIGINAL RULES")
    for rule in rules:
        print(rule)

    # reduce rule domain
    print("\nReducing domain")
    new_rules = lr.reduce_domain(rules)

    print("\nREDUCED RULES")
    for rule in new_rules:
        print(rule)

    # load dataset
    dataset_path = f'{data_path}/{algorithm}_pc.csv'
    dt = pd.read_csv(dataset_path)

    # select input features
    inputs_df = dt[["load_mean", "load_std", param, "pv_mean", "pv_std"]]

    # generate predictions using the reduced rules
    predictions = lr.predict(new_rules, dt)

    print("\nPREDICTIONS")
    print(predictions)
    print(f"\nNumber of predictions: {len(predictions)}")

    # Compute mean absolute error between actual and predicted values
    mean_abs_error = (dt[target] - predictions).abs().mean()
    print(f"Mean Absolute Error for target '{target}': {mean_abs_error}")

    """
    Example structure for storing model errors:
    errors = {
        "sol": {"gridrex": ..., "gridex": ..., "cart": ..., "creepy": ...},
        "memory": {"gridrex": ..., "gridex": ..., "cart": ..., "creepy": ...},
        "time": {"gridrex": ..., "gridex": ..., "cart": ..., "creepy": ...}
    }
    """

