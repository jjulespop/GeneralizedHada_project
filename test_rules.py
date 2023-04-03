from core.configdb import ConfigDB
from core.logic_rules import LogicModels, get_linear_expression
if __name__ == '__main__':
    path = './algorithms/configs'

    # db = ConfigDB(path)
    # db = ConfigDB.from_remote('http://localhost:5333')
    db = ConfigDB.from_local('./algorithms/configs')
    lr = LogicModels(db, "algorithms/rules")
    rules = lr.get_rules('contingency', 'pc', 'sol')
    print(rules)

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
