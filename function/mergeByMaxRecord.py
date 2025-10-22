import os
import pandas as pd
import geopandas as gpd
import numpy as np
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
    record = pd.read_excel(os.path.join(path, "summary.xlsx"))
    record = record[record["country"] != "Test"]
    record.loc[:, "country"] = record["country"].fillna("NA") # one country code is NA and is recorgized as nan
    # get iso3
    record["country_std"] = record["country"].apply(lambda x: __convertISO2(x))
    countryMap = dict(zip(record["country"], record["country_std"]))
    # find the max record
    unoffical = record["fileName"].isin(["all_charger_data_combined.csv", "EVCharger.gdb"])
    recordOffical = record[~unoffical]
    recordUnoffical = record[unoffical]
    recordUnoffical = recordUnoffical.sort_values(["stationNum", "pointsNum"], ascending=False)
    record = pd.concat([recordOffical, recordUnoffical]).drop_duplicates(subset="country_std")
    # stander file name
    record["fileName"] = record["fileName"].str.split('.').str[0].map(STANDER_NAME)
    record.to_csv(os.path.join(path, "merge_log.csv"), encoding="utf-8", index=False)
    
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

    df = gpd.pd.concat(dfs)
    # Split disputed areas
    newDis =[]
    dis = record[record["country_std"].str.len() > 3]
    for row in dis.itertuples():
        country: str = getattr(row, "country_std")
        file = getattr(row, "fileName")
        countryList = country.split('/')
        for c in countryList:
            fileExist = record[record["country_std"] == c]["fileName"].to_list()
            if len(fileExist) == 0:
                fileExist = file
            else:
                fileExist = fileExist[0]
            if fileExist == file:
                addDis = df[df["level1"] == country].copy()
                addDis["level1"] = c
                newDis.append(addDis)
    
    df = df[df["level1"].str.len() < 4]
    df = gpd.GeoDataFrame(pd.concat([df] + newDis))
    
    df.to_file(os.path.join(path, "merge.gpkg"), driver="GPKG", layer="evcs", encoding="utf-8")

    return