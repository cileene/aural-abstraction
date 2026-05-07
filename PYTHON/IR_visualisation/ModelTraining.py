import pandas as pd
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

df = pd.read_csv("Model_Input/PCA_with_params/PCA_with_params.csv", sep=None, engine="python")

pc_cols = [col for col in df.columns if col.startswith("PC")]
X_input = df[pc_cols]
Y_output = df[["Color","Spatiality","Composition","Shape","Material"]]

X_train, X_test, y_train, y_test = train_test_split(
    X_input,
    Y_output,
    test_size=0.1,
    random_state=42
)

model = MLPRegressor(
    hidden_layer_sizes=(16, 8),
    activation="relu",
    max_iter=50000,
    random_state=42
)

model.fit(X_train, y_train)
joblib.dump(model, "model.pkl")

y_pred = model.predict(X_test)

print(y_test)
print(y_pred)

mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("MAE:", mae)
print("MSE:", mse)
print("R2:", r2)
