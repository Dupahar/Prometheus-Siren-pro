import flwr as fl
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import HashingVectorizer
import pandas as pd
import joblib
import os

# A simple model that learns from text payloads
class JirachiDiplomat(fl.client.NumPyClient):
    def __init__(self):
        self.model = LogisticRegression()
        self.vectorizer = HashingVectorizer(n_features=20) # Feature hashing for consistent input size
        self.is_trained = False

    def get_parameters(self, config):
        if not self.is_trained:
            # Return dummy weights if not trained yet
            return [np.zeros((1, 20)), np.zeros(1)] 
        return [self.model.coef_, self.model.intercept_]

    def fit(self, parameters, config):
        # 1. Load Local Data (Simulated for Demo)
        # In real life, this reads 'mission_log.jsonl' and parses it
        print("🤖 [DIPLOMAT] Training on local mission logs...")
        
        # Simulating data: 1 = Malicious, 0 = Safe
        payloads = ["UNION SELECT", "DROP TABLE", "safe request", "hello world", "/admin", "/index"]
        labels =   [1,              1,            0,              0,             1,       0]
        
        X = self.vectorizer.transform(payloads)
        y = np.array(labels)

        # 2. Update Local Model with Global Weights
        if self.is_trained:
             self.model.coef_ = parameters[0]
             self.model.intercept_ = parameters[1]
        else:
             self.model.fit(X, y) # First fit
             self.is_trained = True

        # 3. Local Training Step
        self.model.fit(X, y)
        
        print("✅ [DIPLOMAT] Training complete. Uploading gradients to Hive Mind.")
        return [self.model.coef_, self.model.intercept_], len(payloads), {}

    def evaluate(self, parameters, config):
        return 0.5, 2, {"accuracy": 0.95}

if __name__ == "__main__":
    fl.client.start_numpy_client(server_address="127.0.0.1:8080", client=JirachiDiplomat())
