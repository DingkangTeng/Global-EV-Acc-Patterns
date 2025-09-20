import geopandas as gpd

from .generalResult import generalResult
from setting import readFile, STANDER_NAME

__STANDER_COL = [
    "stationid",
    "stationdistrict", "stationsubdistrict",
    "stationlongitude", "stationlatitude",
    "pilenum" # All chargers
]

__COL_MAP = {
    "level2": "stationdistrict",
    "level3": "stationsubdistrict",
    "lat": "stationlatitude",
    "lng": "stationlongitude"
}

def aodian(file: str | tuple[str, str]) -> tuple[gpd.GeoDataFrame | None, list[list]| None]: # Result, Country, Staion number, Points number
    df, fileName = readFile(file, usecols=__STANDER_COL)
    if df is None or fileName is None:
        return None, None

    return generalResult(
        df, fileName, "stationid", __COL_MAP,
        pointsNumber=df["pilenum"]
    ), [[
        fileName, STANDER_NAME.get(fileName.split('.')[0]), df.shape[0], df["pilenum"].sum()
    ]]