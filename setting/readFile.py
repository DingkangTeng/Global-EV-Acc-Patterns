import os
import pandas as pd
import geopandas as gpd

def readFile(
    file: str | tuple[str, str], usecols: list[str],
    filters: str | None = None,
    encoding: str = "utf-8"
) -> tuple[gpd.GeoDataFrame | pd.DataFrame | None, str | None]:
    
    if filters is not None:
        if isinstance(file, str) and filters not in file:
            return None, None
        elif isinstance(file, tuple) and filters not in file[0]:
            return None, None
    
    if isinstance(file, str):
        if file.endswith(".shp") or file.endswith(".geojson"):
            gdf = gpd.read_file(file, encoding=encoding)
            return gdf[usecols].copy(), os.path.basename(file)
        elif file.endswith(".csv"):
            return pd.read_csv(file, usecols=usecols, encoding=encoding), os.path.basename(file)
        elif file.endswith(".xlsx") or file.endswith(".xls"):
            return pd.read_excel(file, usecols=usecols), os.path.basename(file)
    else:
        gdf = gpd.read_file(file[0], layer=file[1], encoding=encoding)
        return gdf[usecols].copy(), os.path.basename(file[0])
    
    raise ValueError("Unsupported file type or invalid input for 'file' argument.")
    