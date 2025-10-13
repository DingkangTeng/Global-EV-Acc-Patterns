import os
import pandas as pd
import geopandas as gpd
from iso3166 import countries as countryDict

from setting import STANDER_NAME

def __convertISO2(id: str) -> str:
    if id == "EL": # EU use only
        return "GRC"
    elif '/' in id:
        cs = [countryDict.get(x).alpha3 for x in id.split('/')]
        return '/'.join(cs)
    else:
        return countryDict.get(id).alpha3

def mergeByMaxRecord(path: str) -> None:
    f = "summary.xlsx"
    for f in os.listdir(path):
        if f[-4:] == "xlsx": break
    record = pd.read_excel(os.path.join(path, f))
    record = record[record["country"] != "Test"]
    record.loc[:, "country"] = record["country"].fillna("NA") # one country code is NA and is recorgized as nan
    # get iso3
    record["country_std"] = record["country"].apply(lambda x: __convertISO2(x))
    countryMap = dict(zip(record["country"], record["country_std"]))
    # find the max record
    record = record.sort_values(["stationNum", "pointsNum"], ascending=False).drop_duplicates(subset="country_std")
    # stander file name
    record["fileName"] = record["fileName"].str.split('.').str[0].map(STANDER_NAME)
    
    # merge file
    dfs = []
    for file in record["fileName"].unique():
        df = gpd.read_file(os.path.join(path, "{}.geojson".format(file)), encoding="utf-8")
        # convert to iso3
        df["level1"] = df["level1"].map(countryMap)
        # filter country
        countries = record[record["fileName"] == file]["country_std"]
        df = df[df["level1"].isin(countries)]
        dfs.append(df)

    df = gpd.GeoDataFrame(gpd.pd.concat(dfs))
    df.to_file(os.path.join(path, "merge.gpkg"), driver="GPKG", layer="evcs", encoding="utf-8")

    return