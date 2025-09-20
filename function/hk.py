import geopandas as gpd

from .generalResult import generalResult
from setting import readFile, STANDER_NAME

__STANDER_COL = [
    "id",
    "location",
    "latitude", "longitude",
    "chargersCount", "types" # all, charging types list
]

__COL_MAP = {
    "level3": "location",
    "lat": "latitude",
    "lng": "longitude"
}

def hk(file: str | tuple[str, str]) -> tuple[gpd.GeoDataFrame | None, list[list]| None]: # Result, Country, Staion number, Points number
    df, fileName = readFile(file, usecols=__STANDER_COL)
    if df is None or fileName is None:
        return None, None
    
    df["level2"] = ["HKG"] * df.shape[0]

    df["dc"] = df["types"].apply(lambda x: x.count("Standard"))
    df["ac"] = df["chargersCount"] - df["dc"]

    return generalResult(
        df, fileName, "id", __COL_MAP,
        df["chargersCount"], df["dc"], df["ac"]
    ), [[
        fileName, STANDER_NAME.get(fileName.split('.')[0]), df.shape[0], df["chargersCount"].sum()
    ]]