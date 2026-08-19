import geopandas as gpd

from .generalResult import generalResult
from setting import readFile

__STANDER_COL = [
    "uid",
    "latitude", "longitude",
    "country_code", "locality"
]

__COL_MAP = {
    "lat": "latitude",
    "lng": "longitude",
    "level1": "country_code",
    "level3": "locality"
}

def plugShare(file: str | tuple[str, str]) -> tuple[gpd.GeoDataFrame | None, list[list]| None]: # Result, Country, Staion number, Points number
    df, fileName = readFile(file, usecols=__STANDER_COL)
    if df is None or fileName is None:
        return None, None

    df["level2"] = [None] * df.shape[0]
    
    countryGroup = df.groupby("country_code").size().reset_index(name="num")

    return generalResult(
        df, fileName, "uid", __COL_MAP,
        specialLevel1="country_code"
    ), [
        [fileName, row.country_code, row.num, None] for row in countryGroup.itertuples()
    ]