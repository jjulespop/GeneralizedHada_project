from core.configdb import ConfigDB

if __name__ == '__main__':
    #path = './algorithms/configs'
    
    #db = ConfigDB(path)
    #db = ConfigDB.from_remote('http://localhost:5333')
    db = ConfigDB.from_local('./algorithms/configs/input-independent','./algorithms/configs/input-dependent')

    #print(db.fnames)
    #print(db.db)
    ### input-independent
    print('input-independent')
    print(db.get_algorithms())
    print(db.get_hyperparams('toyalg'))
    print(db.get_targets('toyalg'))
    print(db.get_hws('toyalg'))
    print(db.get_prices('toyalg'))
    print(db.get_prices_per_hw('toyalg'))
    print(db.get_type_per_var('toyalg'))

    ### input-dependent
    print('input-dependent')
    print(db.get_algorithms(case_dependent=True))
    print(db.get_hyperparams('toyalg', case_dependent=True))
    print(db.get_targets('toyalg', case_dependent=True))
    print(db.get_hws('toyalg', case_dependent=True))
    print(db.get_prices('toyalg', case_dependent=True))
    print(db.get_prices_per_hw('toyalg', case_dependent=True))
    print(db.get_type_per_var('toyalg', case_dependent=True))
    # ...
