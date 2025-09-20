import geopandas as gpd

from .generalResult import generalResult
from setting import readFile, STANDER_NAME
from setting.constant import ZAF_CITIES, ZAF_PROVINCE

__STANDER_COL = [
    "name", "address",
    "type2TotalBays", "typeCCSTotalBays", # AC, DC
    "lat", "lng"
]

def driveSouthAfrica(file: str | tuple[str, str]) -> tuple[gpd.GeoDataFrame | None, list[list]| None]: # Result, Country, Staion number, Points number
    df, fileName = readFile(file, usecols=__STANDER_COL)
    if df is None or fileName is None:
        return None, None

    # df["level2"], df["level3"] = geocoding(df["address"])
    df["address_set"] = df["address"].str.split(", ").map(set)
    df["level2"] = df["address_set"].apply(
        lambda x: list(x & ZAF_PROVINCE) if x & ZAF_PROVINCE else None
    )
    cities = ZAF_CITIES.values()
    cities = set().union(*cities)
    df["level3"] = df["address_set"].apply(
        lambda x: list(x & cities) if x & cities else None
    )

    DCNumber = df["typeCCSTotalBays"].str.split(' ').str[0].fillna(0).astype(int)
    ACNumber = df["type2TotalBays"].str.split(' ').str[0].fillna(0).astype(int)

    return generalResult(
        df, fileName, ["name", "address"],
        pointsNumber=DCNumber + ACNumber, DCNumber=DCNumber, ACNumber=ACNumber
    ), [[
        fileName, STANDER_NAME.get(fileName.split('.')[0]), df.shape[0], DCNumber.sum() + ACNumber.sum()
    ]]