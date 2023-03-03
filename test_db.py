from core.configdb import ConfigDB

if __name__ == '__main__':
    path = './algorithms/configs'
    
    db = ConfigDB(path)
    #print(db.fnames)
    #print(db.db)
    print(db.get_algorithms())
    print(db.get_hyperparams('toyalg'))
    print(db.get_targets('toyalg'))
    print(db.get_hws('toyalg'))
    print(db.get_prices('toyalg'))
    print(db.get_prices_per_hw('toyalg'))
    print(db.get_type_per_var('toyalg'))
    # ...
