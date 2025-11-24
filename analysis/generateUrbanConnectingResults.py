import os, gc
import geopandas as gpd
import pandas as pd
import numpy as np
from tqdm import tqdm
from scipy.spatial import KDTree

def generate(path: str, cities: gpd.GeoDataFrame) -> None:
    files = pd.read_csv(os.path.join(path, "processed.csv"), encoding="utf-8")
    files.dropna(inplace=True)
    finalResult: list[gpd.GeoDataFrame] = []
    bar = tqdm(total=files.shape[0], desc="Merging all countries", unit="country")
    
    for row in files.itertuples():
        file: str = getattr(row, "iso3")
        gpkg = os.path.join(path, file)

        # Check wheter the layer exists
        if "urbanConnecting" not in gpd.list_layers(gpkg)["name"].to_list(): continue
        # Check the record
        df = gpd.read_file(gpkg, layer="urbanConnecting", encoding="utf-8")
        if df.shape[0] == 0: continue

        country = file.split('.')[0]
        bar.set_description("Merging {}".format(country))
        df["startNodeOSMid"] = df["startNodeOSMid"].astype(int)
        df["endNodeOSMid"] = df["endNodeOSMid"].astype(int)
        
        nodes = gpd.read_file(gpkg, layer="nodes", encoding="utf-8")[["osmid", "geometry"]]
        pathNodes = set(df["startNodeOSMid"].tolist() + df["endNodeOSMid"].tolist())
        nodes = nodes[nodes["osmid"].isin(pathNodes)]
        nodesIdx = nodes.index.to_numpy()

        # Get city name
        boundary: gpd.GeoDataFrame = cities.loc[cities["iso3_code"] == country][["disp_en", "geometry"]]
        ## No boundary
        if boundary.shape[0] == 0: continue
        ## Change crs
        if boundary.crs != nodes.crs and nodes.crs is not None:
            boundary.to_crs(nodes.crs, inplace=True)
        ## Spatial Join with city
        city = nodes.sjoin(boundary)
        osmid2Disp = dict(zip(city["osmid"], city["disp_en"]))
        ### Special case
        if country == "CHN" and 1488403 not in osmid2Disp.keys(): osmid2Disp[1488403] = "Hangzhou, Zhejiang Province, China"
        elif country =="IND" and 336034 not in osmid2Disp.keys(): osmid2Disp[336034] = "Jammu And Kashmir"
        del city, boundary
        gc.collect()

        # Get population
        urbanArea = gpd.read_file(gpkg, layer="cities", encoding="utf-8")
        ## No urban area
        if urbanArea.shape[0] == 0: continue
        ## Change crs
        if urbanArea.crs != nodes.crs and nodes.crs is not None:
            urbanArea.to_crs(nodes.crs, inplace=True)
        ## Spatial join with urban area
        urban = nodes.sjoin(urbanArea)
        osmid2Id = dict(zip(urban["osmid"], urban["urbanId"]))
        osmid2Pop = dict(zip(urban["osmid"], urban["population"]))
        del urban
        gc.collect()

        # Add data
        df["cityName1"] = df["startNodeOSMid"].map(osmid2Disp)
        df["cityPop1"] = np.nan
        df["built-upId1"] = np.nan
        df["cityname2"] = df["endNodeOSMid"].map(osmid2Disp)
        df["cityPop2"] = np.nan
        df["built-upId2"] = np.nan
        df["countryLevelDens"] = getattr(row, "nationalRoadsDens")
        df["iso3"] = country

        # Check null data
        if len(osmid2Id) != len(pathNodes):
            urbanArea["centeroid"] = urbanArea.geometry.centroid
            urbanArea.set_geometry("centeroid", inplace=True)
            point = np.array(list(zip(urbanArea.geometry.x, urbanArea.geometry.y)))
            tree = KDTree(point)

            node = np.array(list(zip(nodes.geometry.x, nodes.geometry.y)))
            _, nearCity = tree.query(node, k=1)

            # Ensure nearCity is always iterable (query can return a scalar for a single point)
            for i, near in enumerate(np.atleast_1d(nearCity)):
                potentialResult = urbanArea.iloc[near]
                osmid = nodes.loc[nodesIdx[i], "osmid"]
                if osmid not in osmid2Id.keys():
                    osmid2Id[osmid] = potentialResult["urbanId"]
                    osmid2Pop[osmid] = potentialResult["population"]

        df["cityPop1"] = df["startNodeOSMid"].map(osmid2Pop)
        df["built-upId1"] = df["startNodeOSMid"].map(osmid2Id)
        df["cityPop2"] = df["endNodeOSMid"].map(osmid2Pop)
        df["built-upId2"] = df["endNodeOSMid"].map(osmid2Id)

        # Save
        df.to_file(gpkg, layer="urbanConnecting", encoding="utf-8")
        finalResult.append(df)
        bar.update()
    
    df = pd.concat(finalResult)
    gpd.GeoDataFrame(
        df.drop(columns="geometry"),
        geometry=df["geometry"],
        crs=finalResult[0].crs if len(finalResult) != 0 else 4326
    ).to_file(
        os.path.join(path, "allCaledCities.gpkg"),
        encoding="utf-8"
    )
    bar.close()

    return

if __name__ == "__main__":
    ROOT = r"_Data/Global_Country_2025/density_roads"
    cities = gpd.read_file(r"_Data/boundary/GAUL_2024_L2.gpkg", layer="GAUL_2024_L2", encoding="utf-8")
    cities = cities[["iso3_code", "disp_en", "geometry"]]

    generate(ROOT, cities)