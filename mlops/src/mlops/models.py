import numpy as np

class ForecastModel():
    def __init__(self,parameters):
        self.parameters=parameters
    
    def fit(self):
        pass
    def train(self):
        pass
    def predict(self,input_data):
        pass


class HeuristicModel(ForecastModel):
    def __init__(self):
        pass
    
    
    def predict(self,input_data:np.ndarray)->np.ndarray:
        
        x = input_data[14]
        prediction = np.ndarray(15*[round(8.4*x ,0)])
        return np.concatenate((input_data[:14],prediction))