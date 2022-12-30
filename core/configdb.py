"""
Class to operate with the JSON configs related to (algorithm, HW) couples.
"""
import os
import json

class ConfigDB():
    def __init__(self, path):
        
        # scan path
        self.fnames = [os.path.join(path, fname) for fname in sorted(os.listdir(path))]

        # dictionary with the name of algorithms as keys and values structured like this:
        #{
        #    'hyperparams': {'var_0': {'type': 'int', 'LB': None, 'UB': None},
        #                    'var_1': {'type': 'int', 'LB': None, 'UB': None}},
        #    'targets': {'time': {'type': 'float', 'LB': None, 'UB': None},
        #                'memory': {'type': 'float', 'LB': None, 'UB': None}},
        #    'hws': {'vm': None,
        #            'pc': None, 
        #            'g100': None}
        #}
        self.db = {}

        for fname in self.fnames:
            # load JSON files
            config = json.load(open(fname))
            
            # checking types for all fields
            self.__check_json(fname, config)

            # internal db structure
            hyperparams = {hyperparam['ID']: {'type': hyperparam['type'],
                                                'LB': hyperparam['LB'],
                                                'UB': hyperparam['UB']}
                            for hyperparam in config['hyperparams']}

            targets = {target['ID']: {'type': target['type'],
                                                'LB': target['LB'],
                                                'UB': target['UB']}
                            for target in config['targets']}


            # checking consistency across hws for a given algorithm
            if config['name'] not in self.db:
                self.db[config['name']] = {'hyperparams': hyperparams,
                                           'targets': targets,
                                           'hws': {config['HW_ID']: config['HW_price']}}
            else:
                # checking consistency of hyperparameters across hws for a given algorithm
                if self.db[config['name']]['hyperparams'] != hyperparams:
                    raise AttributeError(f'Hyperparameters not matching for algorithm {config["name"]} on different hws.')
                # checking consistency of targets across hws for a given algorithm
                if self.db[config['name']]['targets'] != targets:
                    raise AttributeError(f'Targets not matching for algorithm {config["name"]} on different hws.')

                # TODO (eventually): check consistency of HW prices (suggested in config) for a given HW across all algorithms.

                # just adding the new HW and its price, the rest must be the same across hws for the given algorithm.
                self.db[config['name']]['hws'][config['HW_ID']] = config['HW_price']

    def get_algorithms(self):
        '''Get list of all available algorithms.'''
        return list(self.db.keys())

    def get_hyperparams(self, algorithm):
        '''Get list of hyperparameters for a given algorithm.'''
        return list(self.db[algorithm]['hyperparams'].keys())

    def get_targets(self, algorithm):
        '''Get list of targets for a given algorithm.'''
        # price is the only "special" target, with possibly different handling
        return list(self.db[algorithm]['targets'].keys()) + ['price']

    def get_hws(self, algorithm):
        '''Get list of hardware platforms for a given algorithm.'''
        return list(self.db[algorithm]['hws'].keys())

    def get_prices(self, algorithm):
        '''Get list of hardware prices for a given algorithm.'''
        return list(self.db[algorithm]['hws'].values())

    def get_prices_per_hw(self, algorithm):
        '''Get dict HW_name:price for all hws found for a given algorithm.'''
        return self.db[algorithm]['hws']

    def get_lb_per_var(self, algorithm):
        '''Get LBs for all variables (hyperparameters and targets).'''
        lb_per_var = {}

        for var in self.db[algorithm]['hyperparams']:
            lb_per_var[var] = self.db[algorithm]['hyperparams'][var]["LB"]

        for var in self.db[algorithm]['targets']:
            lb_per_var[var] = self.db[algorithm]['targets'][var]["LB"]

        return lb_per_var

    def get_ub_per_var(self, algorithm):
        '''Get UBs for all variables (hyperparameters and targets).'''
        ub_per_var = {}

        for var in self.db[algorithm]['hyperparams']:
            ub_per_var[var] = self.db[algorithm]['hyperparams'][var]["UB"]

        for var in self.db[algorithm]['targets']:
            ub_per_var[var] = self.db[algorithm]['targets'][var]["UB"]

        return ub_per_var

    def __check_json(self, fname, config):
        # checking algorithm
        try:
            if type(config['name']) is not str:
                AttributeError('Algorithm name must be a string')

            # checking hardware
            if type(config['HW_ID']) is not str:
                AttributeError('Hardware platform name must be a string')

            if config['HW_price'] is not None and type(config['HW_price']) not in [int, float]:
                    raise AttributeError("Hardware platform price must be a number or None")

            # checking hyperparams
            for hyperparam in config['hyperparams']:
                if type(hyperparam['ID']) is not str:
                    raise AttributeError(f'ID of hyperparameters must be strings')

                if hyperparam['type'] not in ['int', 'float']:
                    raise AttributeError("Hyperparameter type must be 'int' or 'float'")

                if hyperparam['UB'] is not None and type(hyperparam['UB']) not in [int, float]:
                    raise AttributeError("Hyperparameter upper bound must be a number or None")
                if hyperparam['LB'] is not None and type(hyperparam['LB']) not in [int, float]:
                    raise AttributeError("Hyperparameter lower bound must be a number or None")

            # checking targets
            for target in config['targets']:
                if type(target['ID']) is not str:
                    raise AttributeError(f'ID of targets must be strings; config: {fname}')

                if target['type'] not in ['int', 'float']:
                    raise AttributeError("Targets type must be 'int' or 'float'")

                if target['UB'] is not None and type(target['UB']) not in [int, float]:
                    raise AttributeError("Targets upper bound must be a number or None")
                if target['LB'] is not None and type(target['LB']) not in [int, float]:
                    raise AttributeError("Targets lower bound must be a number or None")
        except AttributeError as e:
            print(f'Error in {fname}')
            raise e
