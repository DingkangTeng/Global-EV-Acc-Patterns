import geopandas as gpd

from .generalResult import generalResult
from setting import readFile, STANDER_NAME

__STANDER_COL = [
    "_id",
    "lat", "lng",
    "connectorNum", "current" # all, charger
]

def tvip(file: str | tuple[str, str]) -> tuple[gpd.GeoDataFrame | None, list[list]| None]: # Result, Country, Staion number, Points number
    df, fileName = readFile(file, usecols=__STANDER_COL)
    if df is None or fileName is None:
        return None, None
    
    df["level2"] = [None] * df.shape[0]
    df["level3"] = [None] * df.shape[0]

    df["dc"] = df["connectorNum"].where(df["current"] == "DC")
    df["ac"] = df["connectorNum"].where(df["courrent"] == "AC")

    return generalResult(
        df, fileName, "_id",
        pointsNumber=df["connectorNum"], 
        DCNumber=df["dc"],
        ACNumber=df["ac"]
    ), [[
        fileName, STANDER_NAME.get(fileName.split('.')[0]), df.shape[0], df["connectorNum"].sum()
    ]]