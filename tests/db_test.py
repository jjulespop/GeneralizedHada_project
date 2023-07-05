import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from vemm.core.configdb import ConfigDB

if __name__ == '__main__':
    #path = './algorithms/configs'
    
    #db = ConfigDB(path)
    #db = ConfigDB.from_remote('http://localhost:5333')
    db = ConfigDB.from_local('./vemm/algorithms/configs/input-independent','./vemm/algorithms/configs/input-dependent')

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
    print(db.get_algorithms(input_dependent=True))
    print(db.get_hyperparams('anticipate', input_dependent=True))
    print(db.get_targets('anticipate', input_dependent=True))
    print(db.get_hws('anticipate', input_dependent=True))
    print(db.get_prices('anticipate', input_dependent=True))
    print(db.get_prices_per_hw('anticipate', input_dependent=True))
    print(db.get_type_per_var('anticipate', input_dependent=True))
    # ...
