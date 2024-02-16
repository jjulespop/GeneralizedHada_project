from core.configdb import ConfigDB
from core.logic_models import *
import  pandas as pd
if __name__ == '__main__':
    path = './algorithms/configs'

    # db = ConfigDB(path)
    # db = ConfigDB.from_remote('http://localhost:5333')
    algorithm = 'anticipate'
    target = 'sol'
    if algorithm == 'anticipate':
        param = "nScenarios"
    else:
        param = "nTraces"
    db = ConfigDB.from_local('./algorithms/configs')
    lr = LogicModels(db, "algorithms/logic_rules", 'CART')
    rules = lr.get_rules(algorithm, 'pc', target)
    #print(rules)
    for rule in rules:
        print(rule)
    print("reducing domain")
    new_rules = lr.reduce_domain(rules)
    print("new rules")


    for rule in new_rules:
        print(rule)
    #exit(0)
    dt = pd.read_csv(f'algorithms/data/{algorithm}_pc.csv')
    input = dt[["load_mean", "load_std", param, "pv_mean", "pv_std"]]
    output = lr.predict(new_rules, dt)
    print(output)
    print(len(output))
    print((dt[target] - output).abs().mean())
    """errors{"sol": {"gridrex": , "gridex": , "cart":, "creepy": }, 
    "memory": {"gridrex": , "gridex": , "cart":, "creepy": }, 
    time{"gridrex": , "gridex": , "cart":, "creepy": } }
    """

    #rules = lr.get_rules_new('contingency', 'pc', 'sol')
    #print(rules)
    #gr = (rules)
    #df = pd.read_csv("algorithms/data/anticipate_pc.csv")
    #pred = gr.predict(df)
    #print(pred[0:100])
    """# print(db.fnames)
    # print(db.db)
    print(db.get_algorithms())
    print(db.get_hyperparams('anticipate'))
    print(db.get_targets('anticipate'))
    print(db.get_hws('anticipate'))
    print(db.get_input_vars('anticipate'))
    print(db.get_prices('anticipate'))
    print(db.get_prices_per_hw('anticipate'))
    print(db.get_type_per_var('anticipate'))"""
