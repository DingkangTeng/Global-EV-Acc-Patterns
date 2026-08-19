import geopandas as gpd

from .generalResult import generalResult
from setting import readFile, STANDER_NAME

__STANDER_COL = [
    "id",
    "city",
    "latitude", "longitude"
]

__COL_MAP = {
    "level3": "city",
    "lat": "latitude",
    "lng": "longitude"
}

def electromaps(file: str | tuple[str, str]) -> tuple[gpd.GeoDataFrame | None, list[list]| None]: # Result, Country, Staion number, Points number
    df, fileName = readFile(file, usecols=__STANDER_COL)
    if df is None or fileName is None:
        return None, None
    
    df["level2"] = [None] * df.shape[0]

    return generalResult(
        df, fileName, "id", __COL_MAP
    ), [[
        fileName, STANDER_NAME.get(fileName.split('.')[0]), df.shape[0], None
    ]]