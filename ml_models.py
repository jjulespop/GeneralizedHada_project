'''
TEMP: maybe not needed.
Class that handles operations that have to be carried out on the ML models.
Alternative: make it model_utils.py and use functions instead of class!!!
'''
import os
import pickle

class MLModels():
    def __init__(self, db, models_path) -> None:
        self.db = db
        self.models_path = models_path

    def get_model(self, algorithm, hw, target):
        
        model_path = os.path.join(self.models_path, f'{algorithm}_{hw}_{target}_DecisionTree_10')

        if not os.path.exists(model_path):
            # TODO triggering training here?
            # TODO triggering training here?
            # TODO triggering training here?
            raise FileNotFoundError(f'Model for ({algorithm}, {hw}, {target}) does not exist.')

        model = pickle.load(open(model_path, 'rb'))
        return model

    def train(self, algorithm, hw, target):
        pass
