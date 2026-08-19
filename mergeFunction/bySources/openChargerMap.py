import geopandas as gpd

from .generalResult import generalResult
from setting import readFile, points2Station, STANDER_NAME

__STANDER_COL = [
    "UUID",
    "country", "City", "StateOrProvince",
    "Latitude", "Longitude",
    "correct_NumberOfPoints" # all
]

__COL_MAP = {
    "level2": "StateOrProvince",
    "level3": "City",
    "lat": "Latitude",
    "lng": "Longitude"
}

def openChargerMap(file: str | tuple[str, str]) -> tuple[gpd.GeoDataFrame | None, list[list]| None]: # Result, Country, Staion number, Points number
    df, fileName = readFile(file, usecols=__STANDER_COL)
    if df is None or fileName is None:
        return None, None
    
    df["City"] = df["City"].replace("N/A", None)

    statistic = df.groupby("country").agg(
        station=("UUID", "nunique"),
        point=("correct_NumberOfPoints", "sum")
    )

    return generalResult(
        df, fileName, "UUID", __COL_MAP,
        df["correct_NumberOfPoints"].fillna(0).astype(int),
        specialLevel1="country"
    ), [
        [fileName, row.Index, row.station, row.point] for row in statistic.itertuples()
    ]