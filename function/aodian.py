import geopandas as gpd

from .generalResult import generalResult
from setting import readFile, STANDER_NAME

__STANDER_COL = [
    "stationid",
    "stationdistrict", "stationsubdistrict",
    "connectortype",
    "stationlongitude", "stationlatitude"
]

__COL_MAP = {
    "level2": "stationdistrict",
    "level3": "stationsubdistrict",
    "lat": "stationlongitude",
    "lng": "stationlatitude"
}

def aodian(file: str | tuple[str, str]) -> tuple[gpd.GeoDataFrame | None, list[list]| None]: # Result, Country, Staion number, Points number
    df, fileName = readFile(file, usecols=__STANDER_COL)
    if df is None or fileName is None:
        return None, None
    
    df["connectortyp"] = df["connectortype"].str.extract("(Quick|Slow|Medium)")
    df["quick"] = df.groupby("stationid")["connectortyp"].transform(
        lambda x: (x == "Quick").sum()
    )
    df["slow"] = df.groupby("stationid")["connectortyp"].transform(
        lambda x: ((x == "Slow") | (x == "Medium")).sum()
    )
    df["counts"] = df["quick"] + df["slow"]

    return generalResult(
        df, fileName, "stationid", __COL_MAP,
        df["counts"], df["quick"], df["slow"]
    ), [[
        fileName, STANDER_NAME.get(fileName.split('.')[0]), df.drop_duplicates(subset="stationid").shape[0], df.shape[0]
    ]]