import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import joblib

df = pd.read_csv("IR_Extraction_results.csv")

X = df.drop(columns=["file"])

scaler = StandardScaler() #nor
X_scaled = scaler.fit_transform(X)


# Reduce dimensions
pca = PCA(n_components=0.99)
X_pca = pca.fit_transform(X_scaled)
print(X_pca)

# save the scaling and pca
joblib.dump(scaler, "scaler.pkl")
joblib.dump(pca, "pca.pkl")