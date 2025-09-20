import geopandas as gpd

from .generalResult import generalResult
from setting import readFile, geoTransform, points2Station

__STANDER_COL = [
    "location_unique_id",
    "geometry_x", "geometry_y",
    "location_country", "location_city",
    "connector_powertype"
]

__COL_MAP = {
    "level3": "location_city"
}

def europeanCommission(
    file: str | tuple[str, str], filters: str | None = None
) -> tuple[gpd.GeoDataFrame | None, list[list]| None]: # Result, Country, Staion number, Points number
    
    df, fileName = readFile(file, usecols=__STANDER_COL, filters=filters, encoding="ISO-8859-1")
    if df is None or fileName is None:
        return None, None
    
    df = geoTransform(df, "geometry_x", "geometry_x", fromCRS=3857)

    df["level2"] = None
    df["connector_powertype"] = df["connector_powertype"].str.split('_').str[0]

    df, countryList = points2Station(df, "location_country", "location_unique_id", "connector_powertype")

    pointsNumber = df["pointsNumber"].fillna(0).astype(int)
    DCNumber = df["DC"].fillna(0).astype(int)
    ACNumber = df["AC"].fillna(0).astype(int)

    return generalResult(
        df, fileName, "location_unique_id", __COL_MAP,
        pointsNumber, DCNumber, ACNumber,
        "location_country"
    ), [
        [fileName, country, station, point] for country, station, point in zip(countryList[0], countryList[1], countryList[2])
    ]