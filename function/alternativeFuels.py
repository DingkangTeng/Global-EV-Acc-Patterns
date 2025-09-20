import geopandas as gpd

from .generalResult import generalResult
from setting import readFile, STANDER_NAME

__STANDER_COL = [
    "Station Name", "ZIP",
    "City", "State",
    "Latitude", "Longitude",
    "EV Level1 EVSE Num", "EV Level2 EVSE Num", "EV DC Fast Count" # AC, AC, DC
]

__COL_MAP = {
    "level2": "State",
    "level3": "City",
    "lat": "Latitude",
    "lng": "Longitude"
}

def alternativeFuels(file: str | tuple[str, str]) -> tuple[gpd.GeoDataFrame | None, list[list]| None]: # Result, Country, Staion number, Points number
    df, fileName = readFile(file, usecols=__STANDER_COL)
    if df is None or fileName is None:
        return None, None

    DCNumber = df["EV DC Fast Count"].fillna(0)
    ACNumber = df["EV Level1 EVSE Num"].fillna(0) + df["EV Level2 EVSE Num"].fillna(0)

    return generalResult(
        df, fileName, ["ZIP", "Station Name"], __COL_MAP,
        DCNumber + ACNumber, DCNumber, ACNumber
    ), [[
        fileName, STANDER_NAME.get(fileName.split('.')[0]), df.shape[0], DCNumber.sum() + ACNumber.sum()
    ]]