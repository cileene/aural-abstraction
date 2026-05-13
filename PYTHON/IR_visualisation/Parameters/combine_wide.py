import os
import pandas as pd

data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

dfs = []
for file in os.listdir(data_dir):
    if file.endswith(".csv"):
        dfs.append(pd.read_csv(os.path.join(data_dir, file)))

combined = pd.concat(dfs, ignore_index=True)
combined["Sound"] = combined["Sound"].astype(str).str.zfill(2)

combined["_n"] = combined.groupby("Sound").cumcount() + 1

value_cols = [c for c in combined.columns if c not in ("Sound", "_n")]
wide = combined.set_index(["Sound", "_n"])[value_cols].unstack("_n")

# Flatten multi-level columns: (col, 1) → col_1
wide.columns = [f"{col}_{n}" for col, n in wide.columns]
result = wide.reset_index().sort_values("Sound").reset_index(drop=True)

output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "combined_wide.csv")
result.to_csv(output_path, index=False)
print(f"Combined {len(dfs)} files into {len(result)} unique sounds, {len(wide.columns)} value columns → combined_wide.csv")