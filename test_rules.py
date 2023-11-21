from core.configdb import ConfigDB
from core.logic_models import *
import  pandas as pd
if __name__ == '__main__':
    path = './algorithms/configs'

    # db = ConfigDB(path)
    # db = ConfigDB.from_remote('http://localhost:5333')
    db = ConfigDB.from_local('./algorithms/configs')
    lr = LogicModels(db, "algorithms/logic_rules", 'CART')
    rules = lr.get_rules('anticipate', 'pc', 'memory')
    #print(rules)
    for rule in rules:
        print(rule)
    new_rules = lr.reduce_domain(rules)
    print("new rules")
    for rule in new_rules:
        print(rule)




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
