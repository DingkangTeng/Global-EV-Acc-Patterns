import geopandas as gpd

# df = gpd.read_file(r"_Data/Global_Country_2025/density_roads/allCaledCities.gpkg", encoding="utf-8")
# print(df.columns)


import sys, os, json, os, sys, gc, copy
from typing import Iterator, Any
from tqdm import tqdm
import numpy as np
from osmnx import utils
from shapely.geometry import MultiLineString, LineString, Point, MultiPoint
from shapely.strtree import STRtree
from shapely.ops import split
import osmnx as ox
import networkx as nx

# data structure method
## list
class newList(list):
    def set(self):
        return set(self)

# Folder operation function
## Make a floder
def mkdir(savePath: str) -> None:
    if not os.path.exists(savePath):
        os.mkdir(savePath)

    return

class readFiles:
    __slots__ = ["path", "fileFilter", "typeFilter", "files"]

    def __init__(self, path: str = "", fileFilter: list[str] = [], typeFilter: list[str] = []):
        self.path = path
        self.files = os.listdir(path)
        typeFilter += ["py"]
        for i in range(len(self.files) - 1, -1, -1):
            file = self.files[i]
            if file.split(".")[-1] in typeFilter or file in fileFilter:
                self.files.pop(i)
    
    def allFolder(self) -> list[str]:
        return [x for x in self.files if len(x.split(".")) == 1]
    
    def specificFloder(self, contains: list[str] = []) -> list[str]:
        allFolder = self.allFolder()
        result = set(allFolder)
        if contains != []:
            for contain in contains:
                result = result & set(x for x in allFolder if contain in x)
    
        return newList(result)
    
    def specificFile(self, suffix: list[str] = [], contains: list[str] = []) -> list[str]:
        files = set(self.files)
        if suffix != []:
            files = files & set(x for x in files if x.split(".")[-1] in suffix)
        if contains != []:
            for contain in contains:
                files = files & set(x for x in files if contain in x)
                
        return newList(files)
    
class getSimpleRoad:
    __slots__ = ["subThreadSize", "__maxThread"]

    def __init__(self, subThreadSize: int = 1024) -> None:
        """
        Initialize the getSimpleRoad class
        """
        CPUCount = os.cpu_count()
        if CPUCount is None:
            CPUCount = 1
        self.__maxThread = 36
        return

    def getOneCountryFromFile(
        self,
        filePath: tuple[str, str],
        country: str,
        savePath: str,
        customFilter: list | None = None
    ) -> None | list:
        
        tqdm.write("Processing country: {} \nExtracting data from file...".format(country))

        gdfOrigional = gpd.read_file(filePath[0], layer=filePath[1], engine="pyogrio", use_arrow=True)
        if customFilter is not None:
            gdf = gdfOrigional[gdfOrigional["highway"].isin(customFilter)].copy()
            del gdfOrigional
            gc.collect()
        else:
            gdf = gdfOrigional
        
        if gdf.shape[0] == 0:
            tqdm.write("No data.")
            return
        
        gdf.drop(columns=["waterway", "aerialway", "barrier", "man_made", "railway", "z_order"], inplace=True)
        gdf["oneway"] = gdf["other_tags"].str.extract(r"\"oneway\"=>\"([^\"]*)\"")
        gdf["oneway"] = np.where(gdf["oneway"] == "yes", True, False)
        gdf["lanes"] = gdf["other_tags"].str.extract(r"\"lanes\"=>\"([^\"]*)\"")

        bar = tqdm(total=gdf.shape[0] + 410, desc=country)
        if gdf.crs is not None:
            espg = gdf.crs.to_epsg()
        else:
            espg = 4326
        
        metadata = {
            "created_date": utils.ts(),
            "created_with": f"osm.pbf from geofabrik.de",
            "crs": "epsg:{}".format(espg),
        }

        bar.set_description("Building origional Graph for {}".format(country))
        nodes: dict[Point, int] = {}
        edges = []
        nodeIDs: list[int] = [0]

        for _, row in gdf.iterrows():
            lines = row["geometry"]
            attrs = row.drop("geometry").to_dict()
            if isinstance(lines, MultiLineString):
                for line in lines.geoms:
                    edges.extend(self.processLine(line, attrs, nodes, nodeIDs))
            else:
                edges.extend(self.processLine(lines, attrs, nodes, nodeIDs))
            bar.update(1)

        # Check middle point and split edges
        bar.set_description("Check the middle point")
        points = list(nodes.keys())
        tree = STRtree(points)

        newEdges = self.splitEdges(edges, points, tree, nodes) # Split for multi processing later
        bar.update(1)
        del edges, points, tree
        gc.collect()
        bar.update(100)

        # Transform nodes to graph
        bar.set_description("Building graph...")
        G = nx.MultiDiGraph(None, None, **metadata)
        for coord, node_id in nodes.items():
            G.add_node(node_id, x=coord.x, y=coord.y)
        for u, v, attrs in newEdges:
            G.add_edge(u, v, **attrs)
        bar.update(100)
        del nodes, newEdges, nodeIDs
        gc.collect()

        if str(espg) != "4326":
            bar.set_description("Projecting {}".format(country))
            GProj = ox.project_graph(G, to_latlong=True)
            bar.update(10)
        else:
            GProj = G
            bar.update(10)

        #Merge juncted intersections
        bar.set_description("Merging juncted intersections of {}".format(country))
        G2 = ox.consolidate_intersections(GProj, rebuild_graph=True, tolerance=0.0001, dead_ends=True)
        G2 = nx.MultiDiGraph(G2, network_type="drive")
        bar.update(100)

        bar.set_description("Saving result of {}".format(country))
        ox.save_graph_geopackage(
            G2,
            filepath=os.path.join(savePath, "{}.gpkg".format(country)),
            directed=True,
            encoding="utf-8"
        )
        bar.update(100)

        bar.close()

        return
    
    @staticmethod
    def processLine(line: LineString, attributes: dict, nodes: dict, nodeIDs: list[int]) ->list[tuple[int, int, dict]]:
        segments = []
        coords = list(line.coords)
        attributes["geometry"] = line

        for coordxy in [coords[0], coords[-1]]:
            coord = Point(coordxy[0], coordxy[1])
            if coord not in nodes:
                nodes[coord] = nodeIDs[0]
                nodeIDs[0] += 1
        u = nodes[Point(coords[0])]
        v = nodes[Point(coords[-1])]
        segments.append((u, v, attributes))
        if not attributes["oneway"]:
            verseAttr = copy.deepcopy(attributes)
            verseAttr["geometry"] = LineString(coords[::-1]) # Reverse line
            segments.append((v, u, verseAttr))

        return segments

    @staticmethod
    def splitEdges(edges: list[tuple[int, int, dict]], points: list[Point], tree: STRtree, nodes: dict[Point, int]) -> list[tuple[int, int, dict]]:
        newEdges = []
        for u, v, attr in edges:
            linestring: LineString = attr["geometry"]
            # Using STRtree find nearby points
            candidates = tree.query(linestring.buffer(1e-8))
            candidates = [points[i] for i in candidates]
            midNodes = []
            for pt in candidates:
                nodeId = nodes[pt]
                if nodeId in (u, v):
                    continue
                if linestring.distance(pt) < 1e-8:
                    proj = linestring.project(pt) # The distance of the curve from the starting point of linestring to the projection point
                    if 0 < proj < linestring.length:
                        midNodes.append((proj, nodeId, pt))
            if midNodes != []:
                midNodes.sort()
                cutPoints = MultiPoint([node[2] for node in midNodes])
                nodeIds = [u] + [node[1] for node in midNodes] + [v]
                segments = split(linestring, cutPoints).geoms
                for i in range(len(segments)):
                    newAttr = copy.deepcopy(attr)
                    newAttr["geometry"] = segments[i]
                    newEdges.append((nodeIds[i], nodeIds[i+1], newAttr))
            else:
                newEdges.append((u, v, attr))
            
        return newEdges
    
customFilter = [
    "motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link"
]
getSimpleRoad().getOneCountryFromFile((r"_Data/europe-latest.osm.pbf", "lines"), "EUR_Merge", "_Data", customFilter=customFilter)