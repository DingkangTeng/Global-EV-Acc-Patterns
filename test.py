import pandas as pd
import geopandas as gpd
import numpy as np
import os
from tqdm import tqdm

# cols = ["POI_01", "POI_02", "POI_03", "POI_ALL", "POP", "GDP"]
# special = {"POI_01", "POI_02", "POI_03"}
# result = pd.read_excel(r"__Data/Global_Country_2025/density.xlsx")

# for col in cols:
#     gini = f"{col}_gini"
#     if gini not in result.columns:
#         result[gini] = np.nan

# bar = tqdm(total=result.shape[0] * 6)

# for row in result.itertuples():
#     idx = getattr(row, "Index")
#     iso3 = getattr(row, "level1")
#     for col in cols:
#         if np.isnan(getattr(row, col)):
#             bar.update()
#             continue
        
#         fileName = f"POI_{int(col.split('_')[1])}.tif" if col in special else col
#         gini = pd.read_csv(
#             os.path.join(r"__Data/Global_Country_2025/giniResult", f"{iso3}_{fileName}.csv")
#         ).dropna()["gini"].to_numpy()
#         result.at[idx, f"{col}_gini"] = np.nanmedian(gini)

#         bar.update()

# result.to_excel(r"__Data/Global_Country_2025/density.xlsx", index=False)

# bar.close()

###########
gdf = gpd.read_file(r"__Data/Global_Country_2025/merge.gpkg")

print(gdf.columns)