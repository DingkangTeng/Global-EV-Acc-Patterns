import geopandas as gpd

from .generalResult import generalResult
from setting import readFile, STANDER_NAME

__STANDER_COL = [
    "name",
    "lon_wgs84", "lat_wgs84",
    "pname", "cityname"
]

__COL_MAP = {
    "level2": "pname",
    "level3": "cityname",
    "lat": "lat_wgs84", "lng": "lon_wgs84"
}

def amap(
    file: str | tuple[str, str], filters: str | None = None
) -> tuple[gpd.GeoDataFrame | None, list[list]| None]: # Result, Country, Staion number, Points number
    
    df, fileName = readFile(file, usecols=__STANDER_COL, filters=filters, encoding="utf-8")
    if df is None or fileName is None:
        return None, None

    return generalResult(
        df, fileName, "name", __COL_MAP
    ), [[
        fileName, STANDER_NAME.get(fileName.split('.')[0]), df.shape[0], None
    ]]