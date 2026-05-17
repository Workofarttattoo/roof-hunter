from sklearn.isotonic import IsotonicRegression
import numpy as np

class ProbabilityCalibrator:
    def __init__(self):
        self.model = IsotonicRegression(out_of_bounds="clip")
        self.fitted = False

    def fit(self, preds, actuals):
        preds = np.array(preds)
        actuals = np.array(actuals)
        self.model.fit(preds, actuals)
        self.fitted = True

    def transform(self, preds):
        if not self.fitted:
            return preds
        preds = np.array(preds)
        return self.model.transform(preds)
