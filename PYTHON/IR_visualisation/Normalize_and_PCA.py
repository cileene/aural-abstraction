import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import joblib

df = pd.read_csv("IR_Extraction_results.csv")

file_name = df["file"]
X = df.drop(columns=["file"])

scaler = StandardScaler() #normalize
X_scaled = scaler.fit_transform(X)

# Reduce dimensions using PCA
pca = PCA(n_components=0.95, svd_solver="full")
pca.fit(X_scaled)
X_pca = pca.fit_transform(X_scaled)
print(X_pca)

# save the scaling and pca to be used for predicting with the model
joblib.dump(scaler, "scaler.pkl")
joblib.dump(pca, "pca.pkl")

#Create csv file to be used for training
pca_columns = [f"PC{i+1}"for i in range(X_pca.shape[1])]
df_pca = pd.DataFrame(X_pca, columns=pca_columns)
df_pca.insert(0, "file", file_name)
df_pca.to_csv("PCA_and_visual.csv", index=False)
