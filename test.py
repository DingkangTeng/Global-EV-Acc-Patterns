import pandas as pd
import numpy as np
import os
from tqdm import tqdm

cols = ["POI_01", "POI_02", "POI_03", "POI_ALL", "POP", "GDP"]
special = {"POI_01", "POI_02", "POI_03"}
result = pd.read_excel(r"__Data/Global_Country_2025/density.xlsx")

for col in cols:
    gini = f"{col}_gini"
    if gini not in result.columns:
        result[gini] = np.nan

bar = tqdm(total=result.shape[0] * 6)

for row in result.itertuples():
    idx = getattr(row, "Index")
    iso3 = getattr(row, "level1")
    for col in cols:
        if getattr(row, col) is None:
            bar.update()
            continue
        
        fileName = f"{col}.tif" if col in special else col
        gini = pd.read_csv(
            os.path.join(r"__Data/Global_Country_2025/giniResult", f"{iso3}_{fileName}.csv"),
            usecols=["gini"]
        )["gini"].to_numpy()
        result.at[idx, f"{col}_gini"] = np.nanmedian(gini)

        bar.update()

bar.close()