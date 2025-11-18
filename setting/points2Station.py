import pandas as pd
import geopandas as gpd
import numpy as np

def points2Station(
    df: pd.DataFrame | gpd.GeoDataFrame, level1: str, idCol: str, typeCol: str
) -> tuple[pd.DataFrame | gpd.GeoDataFrame, tuple[np.ndarray, np.ndarray, np.ndarray]]: # Result, Country based Staion number, Points number
    
    stations = df.groupby([level1])[idCol].nunique()

    powerCounts = (
        df
        .groupby([idCol, typeCol])
        .size()
        .unstack(fill_value=0)
    )

    df = df.drop_duplicates(subset=idCol).set_index(idCol)
    df = df.join(powerCounts, how='left').reset_index()
    df["pointsNumber"] = df["AC"]+ df["DC"]

    stations2 = df.groupby(level1)["pointsNumber"].sum().reindex(stations.index).fillna(0)
    
    return df, (stations.index.to_numpy(), stations.to_numpy(), stations2.to_numpy())