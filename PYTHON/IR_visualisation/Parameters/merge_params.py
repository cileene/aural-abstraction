import os
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)

pca = pd.read_csv(os.path.join(parent_dir, "PCA_and_visual.csv"))
params = pd.read_csv(os.path.join(script_dir, "combined.csv"))

pca["Sound"] = pca["file"].str.extract(r"^(\d+)_")[0].str.zfill(2)
params["Sound"] = params["Sound"].astype(str).str.zfill(2)

merged = pca.merge(params, on="Sound", how="left")
merged = merged.sort_values("Sound").reset_index(drop=True)
merged = merged.drop(columns="Sound")

output_path = os.path.join(parent_dir, "PCA_with_params.csv")
merged.to_csv(output_path, index=False)
print(f"Merged {len(merged)} rows → PCA_with_params.csv")
