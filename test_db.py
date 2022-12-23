from core.configdb import ConfigDB

if __name__ == '__main__':
    path = './algorithms/configs'
    
    db = ConfigDB(path)
    #print(db.fnames)
    #print(db.db)
    print(db.get_algorithms())
    print(db.get_hyperparams('fwt'))
    print(db.get_targets('fwt'))
    print(db.get_hws('fwt'))
    print(db.get_prices('fwt'))
    print(db.get_prices_per_hw('fwt'))
    # ...
