import os, gc, traceback, warnings
import osmnx as ox
import networkx as nx
import geopandas as gpd
import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from shapely.ops import linemerge
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed

from __init__ import LACK_POP

warnings.filterwarnings(
    "ignore", 
    category=UserWarning,
    message="Geometry is in a geographic CRS.*"
)

def urbanConnecting(root: str, maxThread: int = 1) -> None:
    files = os.listdir(root)

    futurses = []
    futureDict = {}
    with ProcessPoolExecutor(max_workers=maxThread) as executor:
        for file in files:
            split = file.split('.')
            if split[-1] != "gpkg" or split[0] in LACK_POP: continue

            # Cal pop threads
            if split[0] in {"USA", "CHN", "EUR_Merge"}:
                popThres = 0
            else:
                popThres = 500000

            gpkg = os.path.join(root, file)
            future = executor.submit(calOneCountry, gpkg, popThres)
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

def calOneCountry(gpkg: str, popThres: float = 0) -> bool | float:
    # Skip null country:
    if "cities" not in gpd.list_layers(gpkg)["name"].to_list(): return False

    urbans = gpd.read_file(gpkg, layer="cities", encoding="utf-8")[["population", "geometry"]]
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
    node = np.array(list(zip(nodes.geometry.x, nodes.geometry.y)))
    tree = KDTree(node)
    _, urbans["nearestNode"] = tree.query(point, k=1)

    del point, node, tree
    nodes = nodes.join(urbans.set_index("nearestNode"), how="outer").set_index("osmid")
    urbanNodes = nodes[~nodes["population"].isna()].index.tolist()
    del urbans

    # Build graph
    edges = gpd.read_file(gpkg, layer="edges", encoding="utf-8").set_index(["u", "v", "key"])
    edges.drop(columns=["highway"], inplace=True)
    G = ox.graph_from_gdfs(nodes, edges)
    crs = edges.crs
    del edges, nodes
    gc.collect()

    # Simplify graph
    total = len(urbanNodes) * (len(urbanNodes) - 1) #// 2
    bar = tqdm(total=total, desc="Calculating urban connecting of {}".format(gpkg), unit="paths")
    newEdges = np.empty([total], dtype=np.ndarray)
    newEdgesDens = np.empty([total, 2], dtype=np.float64)
    newEdgesNode = np.empty([total, 2], dtype=object)
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
            resultPathDens = 0.0
            k = 0
            for u, v in zip(path[:-1], path[1:]):
                edge = GCal[u][v]
                # select the edge entry with the smallest 'length' value
                _, best_attrs = min(edge.items(), key=lambda kv: kv[1].get("length", np.inf))
                resultPath[k] = best_attrs.get("geometry")
                resultPathDens += best_attrs.get("roadsDens") * best_attrs.get("length")
                k += 1

            newEdges[j] = linemerge(resultPath)
            newEdgesDens[j, 0] = resultPathDens / length
            newEdgesDens[j, 1] = length
            newEdgesNode[j, 0] = start
            newEdgesNode[j, 1] = end
            j += 1
            finalDens += resultPathDens
            finalLength += length
            bar.update()
    
    # No connected path
    if j == 0:
        bar.close()
        return np.nan
    
    # Save result
    df1 = pd.DataFrame(newEdgesDens[:j], columns=["roadsDens", "length"])
    df2 = pd.DataFrame(newEdgesNode[:j ], columns=["startNodeOSMid", "endNodeOSMid"])
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

    urbanConnecting(ROOT, maxThread=64)