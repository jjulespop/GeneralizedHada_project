'''
Class that handles operations that have to be carried out on the datasets.
'''
import os
from collections import defaultdict
import pandas as pd
from core.optimization_request import OptimizationRequest


class Datasets():
    def __init__(self, db, data_path):
        self.db = db
        self.data_path = data_path


    def get_dataset(self, algorithm, hw):
        dataset_path = os.path.join(self.data_path, f'{algorithm}_{hw}.csv')
        dataset = pd.read_csv(dataset_path)

        # checking if data complies to configs
        self._check_dataset_consistency(dataset, algorithm, hw)

        return dataset

    def _check_dataset_consistency(self, df, algorithm, hw):
        '''Checking the columns are the expected ones and that they are numericals.'''
        hyperparams = self.db.get_hyperparams(algorithm)
        targets = self.db.get_targets(algorithm)

        if set(df.columns) != set(hyperparams + targets):
            raise AttributeError(f'Columns in the dataset for algorithm {algorithm} and hardware {hw} are not the expected ones.')
         
        #from pandas.api.types import is_numeric_dtype
        for column in df.columns:
            if not pd.api.types.is_numeric_dtype(df[column]):
                raise AttributeError(f'Column {column} in the dataset for algorithm {algorithm} and hardware {hw} is not numeric.')
        

    def extract_var_bounds(self, request: OptimizationRequest):
        '''
        Compute upper and lower bounds of each variable.
        If UB/LB specified in configs, use that instead of extracting from data.
        
        PARAMETERS
        ---------
        request [OptimizationRequest]: request for which we want to extract variable bounds

        RETURN
        ------
        var_bounds [pd.DataFrame]: a frame with lower/upper bound for each variable
        '''

        # check if both UB and LB are specified in the configs
        # otherwise add to "missing_bounds"; if any extract from data and calculate those

        # retrieving LBs/UBs from configs
        lb_per_var = self.db.get_lb_per_var(request.algorithm)
        ub_per_var = self.db.get_ub_per_var(request.algorithm)

        # handling non-specified bounds by extracting them from data
        lb_missing_vars = [var for var,lb in lb_per_var.items() if lb is None]
        ub_missing_vars = [var for var,ub in ub_per_var.items() if ub is None]
        missing_vars = set(lb_missing_vars + ub_missing_vars)

        # at least one bound to be extracted
        if missing_vars:
            # read one HW config at a time
            # extract needed mins and max
            # take overall min of minima and max of maxima
            all_mins_per_var = defaultdict(list)
            all_maxes_per_var = defaultdict(list)

            for hw in self.db.get_hws(request.algorithm):
            
                dataset = self.get_dataset(request.algorithm, hw)

                for var in lb_missing_vars:
                    all_mins_per_var[var].append(dataset[var].min())
                for var in ub_missing_vars:
                    all_maxes_per_var[var].append(dataset[var].max())

            for var in lb_missing_vars:
                lb_per_var[var] = min(all_mins_per_var[var])
            for var in ub_missing_vars:
                ub_per_var[var] = max(all_maxes_per_var[var])


            # Adding price UB and LB
            lb_per_var['price'] = min(request.hws_prices.get_prices_per_hw().values())
            ub_per_var['price'] = max(request.hws_prices.get_prices_per_hw().values())

            var_bounds = {var: {'lb':lb_per_var[var], 'ub':ub_per_var[var]}
                          for var in lb_per_var}
            return var_bounds
        

    def extract_robust_coeff(self, models, request):
        
        '''
        Compute robustness coefficients for each predictive model, according to the specified robustness factor
        
        PARAMETERS
        ---------
        models [MLModels]: object that handles ML models
        request [OptimizationRequest]: represents the user's request

        RETURN
        ------
        robust_coeff [dict]: robustness coefficient for each predictive model
        '''

        if request.robustness_fact or request.robustness_fact == 0:
            robust_coeff = {}
            for target in self.db.get_targets(request.algorithm) + ['price']: 
                for hw in self.db.get_hws(request.algorithm): 
                    # The target price is not estimated: it does not require any robustness coefficient 
                    if target == 'price': 
                        robust_coeff[(hw, "price")] = 0
                    else: 
                        dataset = self.get_dataset(request.algorithm, hw)
                        model = models.get_model(request.algorithm, hw, target)

                        dataset[f'{target}_pred'] = model.predict(dataset[[col for col in dataset.columns if 'var' in col]])
                        dataset[f'{target}_error'] = (dataset[f'{target}'] - dataset[f'{target}_pred']).abs()
                        robust_coeff[(hw, target)] = dataset[f'{target}_error'].std() * dataset[f'{target}_error'].quantile(request.robustness_fact)
            return robust_coeff
        else:
            return None 


#def extract_var_bounds_old(self, request: OptimizationRequest):
#    '''
#    Compute upper and lower bounds of each variable.
#    TODO: if UB/LB specified in configs, use that instead of extracting from data.
#    
#    PARAMETERS
#    ---------
#    request [OptimizationRequest]: request for which we want to extract variable bounds
#
#    RETURN
#    ------
#    var_bounds [pd.DataFrame]: a frame with lower/upper bound for each variable
#    '''
#
#
#    bounds_min = {}
#    bounds_max = {}
#
#    for hw in self.db.get_hws(request.algorithm):
#        
#        dataset = self.get_dataset(request.algorithm, hw)
#        bounds_min[hw] = dataset.min()
#        bounds_max[hw] = dataset.max()
#
#    var_bounds = pd.DataFrame({
#            "min" : pd.DataFrame(bounds_min).transpose().min(), 
#            "max" : pd.DataFrame(bounds_max).transpose().max()
#            })
#
#    # Why? Algo-specific I guess...
#    #for i in range(len(self.db.get_hyperparams(request.algorithm))):
#    #    var_bounds.loc["var_" + str(i), "max"] = 53
#
#    
#    # This is in the case prices are mandatory in configs
#    # in case they can be null, users can define them, logic has to be different
#    #prices = self.db.get_prices(request.algorithm)
#
#    prices = request.hws_prices.get_prices_per_hw().values()
#    var_bounds = var_bounds.append(pd.DataFrame(
#        {"min": [min(prices)], "max": [max(prices)]}, 
#        index = ["price"]))
#    return var_bounds