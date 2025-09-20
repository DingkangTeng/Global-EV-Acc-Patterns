import re
import geopandas as gpd

from .generalResult import generalResult
from setting import readFile, STANDER_NAME, NZL_PROVINCE

__STANDER_COL = [
    "GlobalID",
    "Address",
    "x", "y",
    "Number Of Connectors", "Connectors List" # all, charger list
]

__COL_MAP = {
    "level3": "Address",
    "lat": "y",
    "lng": "x"
}

def newZealand(file: str | tuple[str, str]) -> tuple[gpd.GeoDataFrame | None, list[list]| None]: # Result, Country, Staion number, Points number
    df, fileName = readFile(file, usecols=__STANDER_COL)
    if df is None or fileName is None:
        return None, None
    
    df["address_set"] = df["Address"].str.split(", ").map(set)
    df["level2"] = df["address_set"].apply(
        lambda x: list(x & NZL_PROVINCE) if x & NZL_PROVINCE else None
    )

    df["dc"] = 0
    df["ac"] = 0
    for idx, row in df.iterrows():
        ac = 0
        dc = 0
        chargers = re.findall(r'\{([^}]+)\}', row["Connectors List"])
        for charger in chargers:
            if charger.startswith("AC"):
                # 提取Count数值
                count = re.search(r'Count:(\d+)', charger)
                if count:
                    ac += int(count.group(1))
            elif charger.startswith("DC"):
                count = re.search(r'Count:(\d+)', charger)
                if count:
                    dc += int(count.group(1))
        # 更新当前行的AC和DC计数
        df.at[idx, "ac"] = ac
        df.at[idx, "dc"] = dc

    DCNumber = df["dc"].fillna(0)
    ACNumber = df["ac"].fillna(0)

    return generalResult(
        df, fileName, "GlobalID", __COL_MAP,
        df["Number Of Connectors"], DCNumber, ACNumber
    ), [[
        fileName, STANDER_NAME.get(fileName.split('.')[0]), df.shape[0], df["Number Of Connectors"].sum()
    ]]