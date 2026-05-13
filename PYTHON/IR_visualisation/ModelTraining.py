import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

df = pd.read_csv("Model_Input/PCA_with_params/PCA_with_params.csv", sep=None, engine="python")

target_cols = ["Color", "Spatiality", "Composition", "Shape", "Material"]
pc_cols = [col for col in df.columns if col.startswith("PC")]
X = df[pc_cols].values
y = df[target_cols].values

model = Ridge(alpha=1.0)

loo = LeaveOneOut()
y_pred_loo = cross_val_predict(model, X, y, cv=loo)

print("=== LOO-CV Results ===")
for i, col in enumerate(target_cols):
    mae = mean_absolute_error(y[:, i], y_pred_loo[:, i])
    r2 = r2_score(y[:, i], y_pred_loo[:, i])
    print(f"{col:15s}  MAE: {mae:.3f}  R²: {r2:.3f}")

model.fit(X, y)
joblib.dump(model, "model.pkl")
print("\nModel trained on full dataset and saved to model.pkl")