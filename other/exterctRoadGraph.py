import os
import geopandas as gpd
from tqdm import tqdm

def mergeData(roadsPath: str, savePath: str) -> None:
    countries = os.listdir(roadsPath)
    n = len(countries)

    country: str
    bar = tqdm(total=n * 2, desc="Merging data", unit="country")
    for country in countries:
        # Skip file which is not geo dataset
        if country[-4:] != "gpkg":
            bar.update(2)
            continue

        bar.set_description("Merging {}".format(country))
        path = os.path.join(roadsPath, country)

        nodes = gpd.read_file(path, layer="nodes", encoding="utf-8").set_index("osmid")
        R = []
        A = []
        P = []
        for col in nodes.columns:
            R.append(col) if col[0:2] == "R_" \
                else A.append(col)  if col[0:2] == "A_" \
                else P.append(col) if col[0:10] == "population" \
                else None
        evcs = ["EVCSNum", "EVCSFids", "EVCSNum_After",  "EVCSFids_After"] if "EVCSNum" in nodes.columns else []

        nodes.drop(columns=evcs + R + A + P, inplace=True)
        gpd.GeoDataFrame(nodes, crs=nodes.crs).to_file(
            os.path.join(savePath, country),
            layer="nodes",
            encoding="utf-8"
        )
        del nodes
        bar.update()

        edges = gpd.read_file(path, layer="edges", encoding="utf-8").set_index('u')
        DFO = []
        for col in edges.columns:
            DFO.append(col) if col[0:4] == "DFO_" else None
        incident = ["affected", "affectedIncident"] if "affected" in edges.columns else []

        edges.drop(columns=incident + DFO, inplace=True)
        gpd.GeoDataFrame(edges, crs=edges.crs).to_file(
            os.path.join(savePath, country),
            layer="edges",
            encoding="utf-8"
        )

        del edges
        bar.update()

    return

if __name__ == "__main__":
    a = mergeData("C:\\0_PolyU\\roadsGraph", "D:\\roadsGraph_Clean")