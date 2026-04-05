import pandas as pd
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

df = pd.read_csv("PCA_and_visual.csv", sep=None, engine="python")

pc_cols = [col for col in df.columns if col.startswith("PC")]
X_input = df[pc_cols]
Y_output = df[["Size","Texture","Temp"]]

X_train, X_test, y_train, y_test = train_test_split(
    X_input,
    Y_output,
    test_size=0.1,
    random_state=42
)

model = MLPRegressor(
    hidden_layer_sizes=(32, 16),
    activation="relu",
    alpha=0.3,           # increase alpha vs before, more input dims = more overfit risk
    learning_rate="adaptive",
    max_iter=1000,
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
