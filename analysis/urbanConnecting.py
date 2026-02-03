import os, gc, traceback, warnings
import osmnx as ox
import networkx as nx
import geopandas as gpd
import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from shapely.ops import linemerge, transform
from pyproj import Transformer
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed

from __init__ import LACK_POP, getUtmZone, decayFunc, eus

warnings.filterwarnings(
    "ignore", 
    category=UserWarning,
    message="Geometry is in a geographic CRS.*"
)

def urbanConnecting(resultPath: str, maxThread: int = 1) -> None:
    root = os.path.join(resultPath, "density_roads")
    files = os.listdir(root)
    evcs = gpd.read_file(os.path.join(resultPath, "merge.gpkg"), layer="evcs", encoding="utf-8")[["level1", "geometry"]]

    futurses = []
    futureDict = {}
    with ProcessPoolExecutor(max_workers=maxThread) as executor:
        for file in files:
            split = file.split('.')
            iso3 = split[0]
            if split[-1] != "gpkg" or iso3 in LACK_POP: continue

            # Cal pop threads
            if iso3 in {"USA", "CHN", "EUR_Merge"}:
                popThres = 0
            else:
                popThres = 500000

            gpkg = os.path.join(root, file)
            future = executor.submit(
                calOneCountry,
                gpkg,
                evcs.loc[
                    (evcs["level1"] == iso3) if iso3 != "EUR_Merge" else evcs["level1"].isin(eus(resultPath)[0])
                ].geometry,
                popThres
            )
            futureDict[future] = file
            futurses.append(future)
        
        processed = []
        for future in as_completed(futurses):
            country = futureDict[future]
            try:
                result = future.result()
            except Exception:
                with open(os.path.join(root, "_log.txt"), 'a') as f:
                    f.write(country + traceback.format_exc())
            else:
                processed.append([country, result]) if result else None
        pd.DataFrame(processed, columns=["iso3", "nationalRoadsDens"]).to_csv(os.path.join(root, "processed.csv"), encoding="utf-8", index=False)

    return

# def calOneCountry(gpkg: str, popThres: float = 0) -> bool | float:
#     # Skip null country:
#     if "cities" not in gpd.list_layers(gpkg)["name"].to_list(): return False

#     urbans = gpd.read_file(gpkg, layer="cities", encoding="utf-8")[["population", "city", "urbanId", "geometry"]]
#     urbans = urbans[urbans["population"] >= popThres]

#     if urbans.shape[0] > 50:
#         # get the 51st smallest population if available, otherwise fall back to the smallest (or 0 if no rows)
#         popsSorted = urbans["population"].sort_values(ascending=False).reset_index(drop=True)

#         popThres = popsSorted.iloc[50]
#         del popsSorted

#         urbans = urbans[urbans["population"] >= popThres]

#     # Skip no urban record or sinle urban record
#     elif urbans.shape[0] < 2: return False

#     urbans["centeroid"] = urbans.geometry.centroid
#     urbans.set_geometry("centeroid", inplace=True)
#     point = np.array(list(zip(urbans.geometry.x, urbans.geometry.y)))
#     urbans.drop(columns=["geometry", "centeroid"], inplace=True)

#     # hang urban area center to the mearest node
#     nodes = gpd.read_file(gpkg, layer="nodes", encoding="utf-8")
#     node = np.array(list(zip(nodes.geometry.x, nodes.geometry.y)))
#     tree = KDTree(node)
#     _, urbans["nearestNode"] = tree.query(point, k=1)

#     del point, node, tree
#     nodes = nodes.join(urbans.set_index("nearestNode"), how="outer").set_index("osmid")
#     urbanNodes = nodes[~nodes["population"].isna()].index.tolist()
#     del urbans

#     # Build graph
#     edges = gpd.read_file(gpkg, layer="edges_1000", encoding="utf-8").set_index(["u", "v", "key"])
#     edges.drop(columns=["highway"], inplace=True)
#     G = ox.graph_from_gdfs(nodes, edges)
#     crs = edges.crs
#     del edges
#     gc.collect()

#     # Simplify graph
#     total = len(urbanNodes) * (len(urbanNodes) - 1) #// 2
#     bar = tqdm(total=total, desc="Calculating urban connecting of {}".format(gpkg), unit="paths")
#     newEdges = np.empty([total], dtype=np.ndarray)
#     newEdgesDens = np.empty([total, 4], dtype=np.float64)
#     newEdgesNode = np.empty([total, 6], dtype=object)
#     j = 0
#     finalDens = 0.0
#     finalLength = 0.0
#     # for i, start in enumerate(urbanNodes[:-1]):
#     #     for end in urbanNodes[i+1:]:
#     for start in urbanNodes:
#         endNodes = urbanNodes.copy()
#         endNodes.remove(start)
#         for end in endNodes:
#             GCal = G
#             try: length, path = nx.single_source_dijkstra(GCal, start, end, weight="length")
#             except:
#                 # try:
#                 #     length, path = nx.single_source_dijkstra(GCal, end, start, weight="length")
#                 # except:
#                     GCal = G.to_undirected()
#                     try: length, path = nx.single_source_dijkstra(GCal, start, end, weight="length")
#                     except:
#                         bar.update()
#                         continue

#             # # Validate wheter is surrounding urban area
#             # if any(n in urbanNodesSet and n not in (start, end) for n in path): continue

#             length = sum(length.values()) if isinstance(length, dict) else length
#             resultPath = np.empty([len(path)-1], dtype=object)
#             resultPathDens = 0.0
#             k = 0
#             for u, v in zip(path[:-1], path[1:]):
#                 edge = GCal[u][v]
#                 # select the edge entry with the smallest 'length' value
#                 _, bestAttrs = min(edge.items(), key=lambda kv: kv[1].get("length", np.inf))
#                 resultPath[k] = bestAttrs.get("geometry")
#                 resultPathDens += bestAttrs.get("roadsDens") * bestAttrs.get("length")
#                 k += 1

#             newEdges[j] = linemerge(resultPath)
#             newEdgesDens[j, 0] = resultPathDens / length
#             newEdgesDens[j, 1] = length
#             newEdgesDens[j, 2] = nodes.at[start, "population"] # type: ignore
#             newEdgesDens[j, 3] = nodes.at[end, "population"] # type: ignore
#             newEdgesNode[j, 0] = start
#             newEdgesNode[j, 1] = nodes.at[start, "city"]
#             newEdgesNode[j, 2] = nodes.at[start, "urbanId"]
#             newEdgesNode[j, 3] = end
#             newEdgesNode[j, 4] = nodes.at[end, "city"]
#             newEdgesNode[j, 5] = nodes.at[end, "urbanId"]
#             j += 1
#             finalDens += resultPathDens
#             finalLength += length
#             bar.update()
    
#     # No connected path
#     if j == 0:
#         bar.close()
#         return np.nan
    
#     # Save result
#     df1 = pd.DataFrame(
#         newEdgesDens[:j],
#         columns=["roadsDens", "length", "startCityPopulation", "endCityPopulation"]
#     )
#     df2 = pd.DataFrame(
#         newEdgesNode[:j],
#         columns=["startNodeOSMid", "startCity", "startUrbanID", "endNodeOSMid", "endCity", "endUrbanID"]
#     )
#     gpd.GeoDataFrame(
#         pd.concat([df1, df2], axis=1),
#         geometry=newEdges[:j],
#         crs=crs
#     ).to_file(gpkg, layer="urbanConnecting", encoding="utf-8")

#     bar.close()

#     return finalDens / finalLength

def calOneCountry(gpkg: str, evcs: gpd.GeoSeries, popThres: float = 0) -> bool | float:
    # Skip null country:
    if "cities" not in gpd.list_layers(gpkg)["name"].to_list(): return False

    urbans = gpd.read_file(gpkg, layer="cities", encoding="utf-8")[["population", "city", "urbanId", "geometry"]]
    urbans = urbans[urbans["population"] >= popThres]

    if urbans.shape[0] > 50:
        # get the 51st smallest population if available, otherwise fall back to the smallest (or 0 if no rows)
        popsSorted = urbans["population"].sort_values(ascending=False).reset_index(drop=True)

        popThres = popsSorted.iloc[50]
        del popsSorted

        urbans = urbans[urbans["population"] >= popThres]

    # Skip no urban record or sinle urban record
    elif urbans.shape[0] < 2: return False

    urbans["centeroid"] = urbans.geometry.centroid
    urbans.set_geometry("centeroid", inplace=True)
    point = np.array(list(zip(urbans.geometry.x, urbans.geometry.y)))
    urbans.drop(columns=["geometry", "centeroid"], inplace=True)

    # hang urban area center to the mearest node
    nodes = gpd.read_file(gpkg, layer="nodes", encoding="utf-8")
    ## Get utmZone by nodes centroid and change evcs crs
    centroid = nodes.union_all().centroid
    utmZone = getUtmZone(centroid.y, centroid.x)
    evcs = evcs.to_crs(utmZone)
    evcsIdx = evcs.sindex
    ## Build node tree
    node = np.array(list(zip(nodes.geometry.x, nodes.geometry.y)))
    tree = KDTree(node)
    _, urbans["nearestNode"] = tree.query(point, k=1)

    del point, node, tree
    nodes = nodes.join(urbans.set_index("nearestNode"), how="outer").set_index("osmid")
    urbanNodes = nodes[~nodes["population"].isna()].index.tolist()
    del urbans

    # Build graph
    edges = gpd.read_file(gpkg, layer="edges_1000", encoding="utf-8").set_index(["u", "v", "key"])
    edges.drop(columns=["highway"], inplace=True)
    G = ox.graph_from_gdfs(nodes, edges)
    crs = edges.crs
    transformer = Transformer.from_crs(crs, utmZone, always_xy=True)
    del edges
    gc.collect()

    # Simplify graph
    total = len(urbanNodes) * (len(urbanNodes) - 1) #// 2
    bar = tqdm(total=total, desc="Calculating urban connecting of {}".format(gpkg), unit="paths")
    newEdges = np.empty([total], dtype=np.ndarray)
    newEdgesDens = np.empty([total, 4], dtype=np.float64)
    newEdgesNode = np.empty([total, 6], dtype=object)
    j = 0
    finalDens = 0.0
    finalLength = 0.0
    # for i, start in enumerate(urbanNodes[:-1]):
    #     for end in urbanNodes[i+1:]:
    for start in urbanNodes:
        endNodes = urbanNodes.copy()
        endNodes.remove(start)
        for end in endNodes:
            GCal = G
            try: length, path = nx.single_source_dijkstra(GCal, start, end, weight="length")
            except:
                # try:
                #     length, path = nx.single_source_dijkstra(GCal, end, start, weight="length")
                # except:
                    GCal = G.to_undirected()
                    try: length, path = nx.single_source_dijkstra(GCal, start, end, weight="length")
                    except:
                        bar.update()
                        continue

            # # Validate wheter is surrounding urban area
            # if any(n in urbanNodesSet and n not in (start, end) for n in path): continue

            length = sum(length.values()) if isinstance(length, dict) else length
            resultPath = np.empty([len(path)-1], dtype=object)
            k = 0
            for u, v in zip(path[:-1], path[1:]):
                edge = GCal[u][v]
                # select the edge entry with the smallest 'length' value
                _, bestAttrs = min(edge.items(), key=lambda kv: kv[1].get("length", np.inf))
                resultPath[k] = bestAttrs.get("geometry")
                k += 1

            # Merge lines
            lines = linemerge(resultPath)
            newEdges[j] = lines

            # Calculate road dens
            BUFFER = 1000
            linesTrans = transform(transformer.transform, lines)
            linesBuffer = linesTrans.buffer(BUFFER)
            ## Find evcs points
            possibleMatchesIdx = evcsIdx.intersection(linesBuffer.bounds)
            possibleMatches: gpd.GeoSeries = evcs.iloc[possibleMatchesIdx] # type: ignore
            evcsInBuffer = possibleMatches[possibleMatches.intersects(linesBuffer)]
            if len(evcsInBuffer) == 0 or lines.length == 0: resultPathDens = 0.0
            else:
                x = evcsInBuffer.apply(lambda pt: decayFunc(linesTrans.distance(pt), BUFFER, "Gaussian"))
                resultPathDens = x.sum() / length * 1000 # count per km

            newEdgesDens[j, 0] = resultPathDens
            newEdgesDens[j, 1] = length
            newEdgesDens[j, 2] = nodes.at[start, "population"] # type: ignore
            newEdgesDens[j, 3] = nodes.at[end, "population"] # type: ignore
            newEdgesNode[j, 0] = start
            newEdgesNode[j, 1] = nodes.at[start, "city"]
            newEdgesNode[j, 2] = nodes.at[start, "urbanId"]
            newEdgesNode[j, 3] = end
            newEdgesNode[j, 4] = nodes.at[end, "city"]
            newEdgesNode[j, 5] = nodes.at[end, "urbanId"]
            j += 1
            finalDens += resultPathDens
            finalLength += length
            bar.update()
    
    # No connected path
    if j == 0:
        bar.close()
        return np.nan
    
    # Save result
    df1 = pd.DataFrame(
        newEdgesDens[:j],
        columns=["roadsDens", "length", "startCityPopulation", "endCityPopulation"]
    )
    df2 = pd.DataFrame(
        newEdgesNode[:j],
        columns=["startNodeOSMid", "startCity", "startUrbanID", "endNodeOSMid", "endCity", "endUrbanID"]
    )
    gpd.GeoDataFrame(
        pd.concat([df1, df2], axis=1),
        geometry=newEdges[:j],
        crs=crs
    ).to_file(gpkg, layer="urbanConnecting", encoding="utf-8")

    bar.close()

    return finalDens / finalLength

if __name__ == "__main__":
    # Root path of saved roads data with density col (save path//density_roads)
    ROOT = r"_Data/Global_Country_2025/density_roads"
    RESULT = r"_Data/Global_Country_2025"

    urbanConnecting(RESULT, maxThread=64)