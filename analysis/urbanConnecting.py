import os, gc
import osmnx as ox
import networkx as nx
import geopandas as gpd
import pandas as pd
import numpy as np
from scipy.spatial import KDTree
from shapely.ops import linemerge
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed

def urbanConnecting(root: str, popThres: int, maxThread: int = 1) -> None:
    files = os.listdir(root)

    futurses = []
    futureDict = {}
    with ProcessPoolExecutor(max_workers=maxThread) as executor:
        for file in files:
            if file.split('.')[-1] != "gpkg": continue
            gpkg = os.path.join(root, file)
            future = executor.submit(calOneCountry, gpkg, popThres)
            futureDict[future] = file
            futurses.append(future)
        
        for future in as_completed(futurses):
            country = futureDict[future]
            try:
                future.result()
            except Exception as e:
                raise RuntimeError("{}: {}".format(country, e))

    return

def calOneCountry(gpkg: str, popThres: int) -> None:
    urbans = gpd.read_file(gpkg, layer="cities", encoding="utf-8")[["GID_2", "population", "geometry"]]
    urbans = urbans[urbans["population"] >= popThres]

    if urbans.shape[0] == 0: return

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
    urbanNodes = nodes[~nodes["GID_2"].isna()].index.tolist()
    urbanNodesSet = set(urbanNodes)
    del urbans

    # Build graph
    edges = gpd.read_file(gpkg, layer="edges", encoding="utf-8").set_index(["u", "v", "key"])
    edgesLen = edges.shape[0]
    edges.drop(columns=["highway"], inplace=True)
    G = ox.graph_from_gdfs(nodes, edges)
    crs = edges.crs
    del edges
    gc.collect()

    # Simplify graph
    total = len(urbanNodes) * (len(urbanNodes) - 1) // 2
    bar = tqdm(total=total, desc="Calculating urban connecting", unit="paths")
    newEdges = np.empty([total], dtype=np.ndarray)
    newEdgesDens = np.empty([total, 2], dtype=np.float64)
    newEdgesNode = np.empty([total, 2], dtype=object)
    j = 0
    for i, start in enumerate(urbanNodes[:-1]):
        for end in urbanNodes[i+1:]:
            try: length, path = nx.single_source_dijkstra(G, start, end, weight="length", cutoff=edgesLen//2)
            except: continue

            # Validate wheter is surrounding urban area
            if any(n in urbanNodesSet and n not in (start, end) for n in path): continue

            length = sum(length.values()) if isinstance(length, dict) else length
            resultPath = np.empty([len(path)-1], dtype=object)
            resultPathDens = 0.0
            k = 0
            for u, v in zip(path[:-1], path[1:]):
                edge = G[u][v]
                # select the edge entry with the smallest 'length' value
                _, best_attrs = min(edge.items(), key=lambda kv: kv[1].get("length", np.inf))
                resultPath[k] = best_attrs.get("geometry")
                resultPathDens += best_attrs.get("roadsDens") * best_attrs.get("length")
                k += 1

            newEdges[j] = linemerge(resultPath)
            newEdgesDens[j, 0] = resultPathDens / length
            newEdgesDens[j, 1] = length
            newEdgesNode[j, 0] = nodes.at[start, "GID_2"]
            newEdgesNode[j, 1] = nodes.at[end, "GID_2"]
            j += 1
            bar.update()

            if j > 1: break
        if j > 1: break

    # Save results
    df1 = pd.DataFrame(newEdgesDens[:j], columns=["roadsDens", "length"])
    df2 = pd.DataFrame(newEdgesNode[:j ], columns=["start", "end"])
    gpd.GeoDataFrame(
        pd.concat([df1, df2], axis=1),
        geometry=newEdges[:j],
        crs=crs
    ).to_file(gpkg, layer="urbanConnecting", encoding="utf-8")

    return

if __name__ == "__main__":
    # Root path of saved roads data with density col (save path//density_roads)
    ROOT = r"C:\0_PolyU\data-global-ev-2025\_Data\Global_Country_2025\test" 

    urbanConnecting(ROOT, 500000, maxThread=16)