import os
import json
import requests
from urllib.parse import urljoin


class ConfigDB():
    """Exposes information stored in the JSON configs (one config per algorithm/hardware pair)."""
    @classmethod
    def from_local(cls, path_no_inp, path_inp):
        """Initialize ConfigDB using local configs.

        Args:
            path_no_inp (str): local path containing the configs (non input-dependent case).
            path_inp (str): local path containing the configs (input-dependent case).

        Returns:
            ConfigDB: instance of ConfigDB.
        """

        fnames_no_inp = [os.path.join(path_no_inp, fname) for fname in sorted(os.listdir(path_no_inp))]
        fnames_inp = [os.path.join(path_inp, fname) for fname in sorted(os.listdir(path_inp))]
        #algo_hw_couples = set()
        configs_by_algo_hw_no_inp = {}
        configs_by_algo_hw_inp = {}

        # expected fnames: <algorithm>_<hw>.csv
        for fname in fnames_no_inp:
            algorithm, part = fname.split('_')
            hw = part.split('.')[0]
            #algo_hw_couples.add((algorithm, hw))
            configs_by_algo_hw_no_inp[(algorithm, hw)] = json.load(open(fname))

        for fname in fnames_inp:
            algorithm, part = fname.split('_')
            hw = part.split('.')[0]
            #algo_hw_couples.add((algorithm, hw))
            configs_by_algo_hw_inp[(algorithm, hw)] = json.load(open(fname))
            #configs_inp.append(json.load(open(fname)))
        
        algo_hw_couples = set(list(configs_by_algo_hw_no_inp.keys())+list(configs_by_algo_hw_inp.keys()))

        return cls(configs_by_algo_hw_no_inp, configs_by_algo_hw_inp, algo_hw_couples)

    @classmethod
    def from_remote(cls, address):
        """Initialize ConfigDB using remote configs (VM storage ervice).

        Args:
            address (str): complete URL relative to the service that handles the configs.

        Returns:
            ConfigDB: instance of ConfigDB.
        """
        # test availability
        #requests.head(address)

        # getting list of config files
        configs_url = urljoin(address, '/configs')
        configs_by_algo_hw = {'input-independent': {}, 'input-dependent': {}}
        algo_hw_couples = {}

        for case in ['input-independent', 'input-dependent']:
            algo_hw_couples[case] = [(config['algorithm'], config['hw']) 
                    for config in requests.request('GET', configs_url).json()['configs'][case]]

        # getting the actual configs
        for case, algo_hw_couples_case in algo_hw_couples.items():
            for (algorithm, hw) in algo_hw_couples_case:
                request_url = f'/configs/{algorithm}/{hw}'
                if case == 'input-dependent':
                    request_url += '/input'
                algo_hw_url = urljoin(address, request_url)
                config = json.loads(requests.request('GET', algo_hw_url).content)
                configs_by_algo_hw[case][(algorithm, hw)] = config


        algo_hw_couples = set(algo_hw_couples['input-independent'] + algo_hw_couples['input-dependent'])

        return cls(configs_by_algo_hw['input-independent'], configs_by_algo_hw['input-dependent'], algo_hw_couples)

    def __init__(self, configs_no_inp, configs_inp, algo_hw_couples):
        """Initializes ConfigDB.

        Args:
            configs_no_inp (list[dict]): list of configs, with each configs being represented as a dict (no input-dependent case).
            configs_inp (list[dict]): list of configs, with each configs being represented as a dict (input-dependent case).
            algo_hw_couples (list[tuple[str,str]]): list of (algorith_id, hardware_id) couples, corresponding, in order, to the configs.
        
        Raises:
            AttributeError: Hyperparameters and/or Targets not matching across different hardware given the same algorithm.
        """
        
        # contains two dictionaries, one for the input-dependent case, one for ther inpude-independent one;
        # the first one has an additional 'inputs' field.
        # dictionary with the name of algorithms as keys and values structured like this:
        #{
        #    'hyperparams': {'var_0': {'type': 'int', 'LB': None, 'UB': None},
        #                    'var_1': {'type': 'int', 'LB': None, 'UB': None}},
        #    'targets': {'time': {'LB': None, 'UB': None},
        #                'memory': {'LB': None, 'UB': None}},
        #    'hws': {'vm': None,
        #            'pc': None, 
        #            'g100': None}
        #}
        self.configs_no_inp = configs_no_inp
        self.configs_inp = configs_inp
        self.algo_hw_couples = algo_hw_couples
        self.db = {'input-dependent':{}, 'input-independent': {}}

        for (algorithm, hw) in self.algo_hw_couples:
            # load JSON files
            #config = json.load(open(fname))
            
            if (algorithm, hw) in self.configs_no_inp:
                self.add_to_db(algorithm, hw, self.configs_no_inp[(algorithm, hw)], input_dependent=False)
            if (algorithm, hw) in self.configs_inp:
                self.add_to_db(algorithm, hw, self.configs_inp[(algorithm, hw)], input_dependent=True)

    def add_to_db(self, algorithm, hw, config, input_dependent=False):
        # checking types for all fields
        self.__check_json(algorithm, hw, config, input_dependent=input_dependent)

        # internal db structure
        hyperparams = {hyperparam['ID']: {'type': hyperparam['type'],
                                            'description': hyperparam['description'],
                                            'LB': hyperparam['LB'] if hyperparam['type'] != 'str' else None,
                                            'UB': hyperparam['UB'] if hyperparam['type'] != 'str' else None}
                        for hyperparam in config['hyperparams']}

        #'type': target['type'],
        targets = {target['ID']: {'description': target['description'],
                                    'LB': target['LB'],
                                    'UB': target['UB']}
                        for target in config['targets']}
        
        if input_dependent:
            inputs = {input['ID']: {'type': input['type'],
                                        'description': input['description'],
                                        'LB': input['LB'] if input['type'] != 'str' else None,
                                        'UB': input['UB'] if input['type'] != 'str' else None}
                            for input in config['inputs']}


        # checking for overlap of names among inputs, hyperparams and targets
        if set.intersection(set(hyperparams), set(targets)):
                raise AttributeError(f'Names of hyperparams and targets must not overlap.')
        if input_dependent:
            if set.intersection(set(hyperparams), set(inputs)):
                    raise AttributeError(f'Names of hyperparams and inputs must not overlap.')
            if set.intersection(set(inputs), set(targets)):
                    raise AttributeError(f'Names of inputs and targets must not overlap.')

        case_key = 'input-dependent' if input_dependent else 'input-independent'
        # checking consistency across hws for a given algorithm
        if config['name'] not in self.db[case_key]:
            self.db[case_key][config['name']] = {'hyperparams': hyperparams,
                                        'targets': targets,
                                        'hws': {config['HW_ID']: config['HW_price']}}
            if input_dependent:
                self.db[case_key][config['name']]['inputs'] = inputs

        else:
            # checking consistency of hyperparameters across hws for a given algorithm
            if self.db[case_key][config['name']]['hyperparams'] != hyperparams:
                raise AttributeError(f'Hyperparameters not matching for algorithm {config["name"]} on different hws.')
            # checking consistency of targets across hws for a given algorithm
            if self.db[case_key][config['name']]['targets'] != targets:
                raise AttributeError(f'Targets not matching for algorithm {config["name"]} on different hws.')
            if input_dependent:
                # checking consistency of inputs across hws for a given algorithm
                if self.db[case_key][config['name']]['targets'] != inputs:
                    raise AttributeError(f'Inputs not matching for algorithm {config["name"]} on different hws.')

            # TODO (eventually): check consistency of HW prices (suggested in config) for a given HW across all algorithms.
            # Not needed; prices could be different for same hw and different algorithms (e.g. different contracts) 

            # just adding the new HW and its price, the rest must be the same across hws for the given algorithm.
            self.db[case_key][config['name']]['hws'][config['HW_ID']] = config['HW_price']

    def get_db_by_case(self, input_dependent=False):
        return self.db['input-dependent'] if input_dependent else self.db['input-independent']

    def get_algorithms(self, input_dependent=False):
        """Get list of all available algorithms."""
        return list(self.get_db_by_case(input_dependent).keys())

    def get_inputs(self, algorithm):
        """Get list of inputs for a given algorithm."""
        return list(self.db['input-dependent'][algorithm]['inputs'].keys())

    def get_hyperparams(self, algorithm, input_dependent=False):
        """Get list of hyperparameters for a given algorithm."""
        return list(self.get_db_by_case(input_dependent)[algorithm]['hyperparams'].keys())

    def get_targets(self, algorithm, input_dependent=False):
        """Get list of targets for a given algorithm."""
        # price is the only "special" target, with possibly different handling
        return list(self.get_db_by_case(input_dependent)[algorithm]['targets'].keys()) + ['price']

    def get_hws(self, algorithm, input_dependent=False):
        """Get list of hardware platforms for a given algorithm."""
        return list(self.get_db_by_case(input_dependent)[algorithm]['hws'].keys())

    def get_prices(self, algorithm, input_dependent=False):
        """Get list of hardware prices for a given algorithm."""
        return list(self.get_db_by_case(input_dependent)[algorithm]['hws'].values())

    def get_prices_per_hw(self, algorithm, input_dependent=False):
        """Get dict HW_name:price for all hws found for a given algorithm."""
        return self.get_db_by_case(input_dependent)[algorithm]['hws']

    def get_lb_per_var(self, algorithm, input_dependent=False):
        """Get LBs for all variables (hyperparameters and targets); inputs too for the input-dependent cases."""
        lb_per_var = {}

        if input_dependent:
            for var in self.db['input-dependent'][algorithm]['inputs']:
                lb_per_var[var] = self.db['input-dependent'][algorithm]['inputs'][var]["LB"]

        for var in self.get_db_by_case(input_dependent)[algorithm]['hyperparams']:
            lb_per_var[var] = self.get_db_by_case(input_dependent)[algorithm]['hyperparams'][var]["LB"]

        for var in self.get_db_by_case(input_dependent)[algorithm]['targets']:
            lb_per_var[var] = self.get_db_by_case(input_dependent)[algorithm]['targets'][var]["LB"]

        return lb_per_var

    def get_ub_per_var(self, algorithm, input_dependent=False):
        """Get UBs for all variables (hyperparameters and targets); inputs too for the input-dependent cases."""
        ub_per_var = {}

        if input_dependent:
            for var in self.db['input-dependent'][algorithm]['inputs']:
                ub_per_var[var] = self.db['input-dependent'][algorithm]['inputs'][var]["UB"]

        for var in self.get_db_by_case(input_dependent)[algorithm]['hyperparams']:
            ub_per_var[var] = self.get_db_by_case(input_dependent)[algorithm]['hyperparams'][var]["UB"]

        for var in self.get_db_by_case(input_dependent)[algorithm]['targets']:
            ub_per_var[var] = self.get_db_by_case(input_dependent)[algorithm]['targets'][var]["UB"]

        return ub_per_var
    
    def get_description_per_var(self, algorithm, input_dependent=False):
        """Get description for all variables (hyperparameters and targets); inputs too for the input-dependent cases."""
        description_per_var = {}

        if input_dependent:
            for var in self.db['input-dependent'][algorithm]['inputs']:
                description_per_var[var] = self.db['input-dependent'][algorithm]['inputs'][var]["description"]

        for var in self.get_db_by_case(input_dependent)[algorithm]['hyperparams']:
            description_per_var[var] = self.get_db_by_case(input_dependent)[algorithm]['hyperparams'][var]["description"]

        for var in self.get_db_by_case(input_dependent)[algorithm]['targets']:
            description_per_var[var] = self.get_db_by_case(input_dependent)[algorithm]['targets'][var]["description"]

        return description_per_var

    def get_type_per_input(self, algorithm):
        """Get type for all input variables; input-dependent case only."""
        type_per_input = {}

        for var in self.db['input-dependent'][algorithm]['inputs']:
            type_per_input[var] = self.db['input-dependent'][algorithm]['inputs'][var]["type"]

        return type_per_input

    def get_type_per_var(self, algorithm, input_dependent=False):
        """Get type for all variables (hyperparameters and targets); inputs too for the input-dependent cases."""
        type_per_var = {}

        if input_dependent:
            for var, type in self.get_type_per_input(algorithm).items():
                type_per_var[var] = type

        for var in self.get_db_by_case(input_dependent)[algorithm]['hyperparams']:
            type_per_var[var] = self.get_db_by_case(input_dependent)[algorithm]['hyperparams'][var]["type"]

        # assumption: targets are always continuous
        for var in self.get_db_by_case(input_dependent)[algorithm]['targets']:
            type_per_var[var] = 'float'

        return type_per_var

    def get_str_vars(self, algorithm, input_dependent=False):
        """Get names of all string variables (hyperparameters)."""
        return [var for var,type in self.get_type_per_var(algorithm, input_dependent).items()
                if type == 'str']


    def get_ml_input_vars(self, algorithm, input_dependent=False):
        """Get variables that are fed as input to the ML models."""
        input_vars = self.get_hyperparams(algorithm, input_dependent)

        if input_dependent:
            input_vars.extend(self.get_inputs(algorithm))

        return input_vars

    def __check_json(self, algorithm, hw, config, input_dependent=False):
        """Checks that the fields in the JSON configs are present and of of the expected types."""
        try:
            # checking algorithm
            if type(config['name']) is not str:
                AttributeError('Algorithm name must be a string')

            # checking hardware
            if type(config['HW_ID']) is not str:
                AttributeError('Hardware platform name must be a string')

            if config['HW_price'] is not None and type(config['HW_price']) not in [int, float]:
                    raise AttributeError("Hardware platform price must be a number or None")

            # checking inputs (if input-dependent case), hyperparameters and targets
            if input_dependent:
                for input in config['hyperparams']:
                    if type(input['ID']) is not str:
                        raise AttributeError(f'ID of inputs must be strings')

                    if input['description'] is not None and type(input['description']) is not str:
                        raise AttributeError("Input description must be a string")

                    if input['type'] not in ['bin', 'int', 'float', 'str']:
                        raise AttributeError("Input type must be 'bin', 'int' or 'float'")

                    if input['type'] == 'str':
                        if ('UB' in input or 'LB' in input):
                                raise AttributeError("Inputs of type str cannot have an upper bound nor a lower bound")
                    else:
                        if input['UB'] is not None and type(input['UB']) not in [int, float]:
                            raise AttributeError("Input upper bound must be a number or None")
                        if input['LB'] is not None and type(input['LB']) not in [int, float]:
                            raise AttributeError("Input lower bound must be a number or None")

            for hyperparam in config['hyperparams']:
                if type(hyperparam['ID']) is not str:
                    raise AttributeError(f'ID of hyperparameters must be strings')

                if hyperparam['description'] is not None and type(hyperparam['description']) is not str:
                    raise AttributeError("Hyperparameter description must be a string")

                if hyperparam['type'] not in ['bin', 'int', 'float', 'str']:
                    raise AttributeError("Hyperparameter type must be 'bin', 'int', 'float' or 'str'")

                if hyperparam['type'] == 'str':
                    if ('UB' in hyperparam or 'LB' in hyperparam):
                        raise AttributeError("Hyperparameters of type str cannot have an upper bound nor a lower bound")
                else:
                    if hyperparam['UB'] is not None and type(hyperparam['UB']) not in [int, float]:
                        raise AttributeError("Hyperparameter upper bound must be a number or None")
                    if hyperparam['LB'] is not None and type(hyperparam['LB']) not in [int, float]:
                        raise AttributeError("Hyperparameter lower bound must be a number or None")

            # checking targets
            for target in config['targets']:
                if type(target['ID']) is not str:
                    raise AttributeError(f'ID of targets must be strings; config: ({algorithm}, {hw}')

                if target['description'] is not None and type(target['description']) is not str:
                    raise AttributeError("Target description must be a string")

                #if target['type'] not in ['bin', 'int', 'float']:
                #    raise AttributeError("Targets type must be 'bin', 'int' or 'float'")

                if target['UB'] is not None and type(target['UB']) not in [int, float]:
                    raise AttributeError("Targets upper bound must be a number or None")
                if target['LB'] is not None and type(target['LB']) not in [int, float]:
                    raise AttributeError("Targets lower bound must be a number or None")

        except AttributeError as e:
            print(f'Error in config ({algorithm}, {hw})')
            raise e
