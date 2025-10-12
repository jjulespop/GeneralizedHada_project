"""
Testing ConfigDB methods for initialization and data retrieval

"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hada.core.config.configdb import ConfigDB
from hada.config import config_loader

config = config_loader.load_config(config_path="./hada/config/config.yaml")


if __name__ == "__main__":

    # load paths from config
    algorithms_configs_path = config["paths"]["algorithms_configs"]
    # storage_ws_url = config["paths"]["storage_ws_url"]

    ### Init ###
    # db load
    db = ConfigDB.from_local(algorithms_configs_path)
    # db = ConfigDB.from_remote(storage_ws_url)
    
    ### Test db content###
    # print("File names in the configuration database:", db.fnames)
    # print("Full configuration database content:", db.db)

    # methods testing
    print("\nAVAILABLE ALGORITHMS")
    print(db.get_algorithms())

    algorithm = config['algorithms']['anticipate']
    print(f"\nChosen Algorithm: {algorithm}")

    print("\nHYPERPARAMETERS")
    print(db.get_hyperparams(algorithm))

    print("\nTARGETS")
    print(db.get_targets(algorithm))

    print("\nHARDWARE")
    print(db.get_hws(algorithm))

    print("\nINPUT VARIABLES")
    print(db.get_input_vars(algorithm))

    print("\nPRICES")
    print(db.get_prices(algorithm))

    print("\nPRICES PER HARDWARE")
    print(db.get_prices_per_hw(algorithm))

    print("\nVARIABLE TYPE")
    print(db.get_type_per_var(algorithm))
