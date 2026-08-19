import pandas as pd
import geopandas as gpd

from setting import STANDER_NAME, uuids

def generalResult(
        df: pd.DataFrame, fileName: str,
        uuidName: str | list,
        colMap: dict[str, str] = {},
        pointsNumber: pd.Series | None = None,
        DCNumber: pd.Series | None = None,
        ACNumber: pd.Series | None = None,
        specialLevel1: str | None = None
    ) -> gpd.GeoDataFrame:

    result = {}

    result["UUID"] = uuids(df, uuidName)
    result["sources"] = [fileName] * len(df)
    if specialLevel1 is not None:
        result["level1"] = df[specialLevel1].to_numpy()
    else:
        result["level1"] = [STANDER_NAME.get(fileName.split(".")[0])] * len(df)
    
    for col in ["level2", "level3", "lat", "lng"]:
        result[col] = df[colMap.get(col, col)].to_numpy()

    if pointsNumber is None:
        result["pointsNumber"] = [None] * len(df)
    else:
        result["pointsNumber"] = pointsNumber
    if DCNumber is None:
        result["DCNumber"] = [None] * len(df)
    else:
        result["DCNumber"] = DCNumber
    if ACNumber is None:
        result["ACNumber"] = [None] * len(df)
    else:    
        result["ACNumber"] = ACNumber

    return gpd.GeoDataFrame(result, geometry=gpd.points_from_xy(result["lng"], result["lat"]), crs="EPSG:4326")