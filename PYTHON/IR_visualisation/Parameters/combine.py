import os
import pandas as pd

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

dfs = []
for file in os.listdir(data_dir):
    if file.endswith(".csv"):
        dfs.append(pd.read_csv(os.path.join(data_dir, file)))

combined = pd.concat(dfs)
combined["Sound"] = combined["Sound"].astype(str).str.zfill(2)
result = combined.groupby("Sound").mean().reset_index()
result = result.sort_values("Sound").reset_index(drop=True)

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "combined.csv")
result.to_csv(output_path, index=False)
print(f"Combined {len(dfs)} files into {len(result)} unique sounds → combined.csv")
