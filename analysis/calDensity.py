import os
import rasterio as rio
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import LineString
from tqdm import tqdm
from rasterio.mask import mask
from concurrent.futures import as_completed, ThreadPoolExecutor, ProcessPoolExecutor
from threading import Lock

BOUNDART = {
    "level1": "iso3_code"
}

def decayFunc(distance, d0, func: str) -> float:
    """Gaussian decay function"""
    if func == "Gaussian":
        return np.exp(-0.5 * (distance / d0) ** 2)
    else:
        raise RuntimeError(" \
            Unexceptional decay function. Available function: \n \
            Gaussian decay function; \
        ")

def get_utm_zone(lat: float, lon: float) -> str:
    zone = int((lon + 180) // 6) + 1
    hemisphere = 'north' if lat >= 0 else 'south'
    return f"EPSG:326{zone:02d}" if hemisphere == 'north' else f"EPSG:327{zone:02d}"

class calDensity:
    __slots__ = [
        "evcs",
        "units", "unitsname",
        "boundaies", "buffer", "decay",
        "result", "densityPath",
        "maxThread", "lock"
    ]

    def __init__(
        self,
        resultPath: str, unitsname: str = "level1",
        buffer: int = 1000, decay: str = "Gaussian",
        maxThread: int = 1
    ) -> None:

        self.evcs = gpd.read_file(os.path.join(resultPath, "merge.gpkg"), layer="evcs", encoding="utf-8")[[unitsname, "geometry"]]
        self.boundaies = gpd.read_file(os.path.join(resultPath, "merge.gpkg"), layer=unitsname, encoding="utf-8") # from GAUL
        self.unitsname = unitsname
        self.units = self.evcs[unitsname].unique().tolist()
        self.densityPath = os.path.join(resultPath, "density.xlsx")
        if os.path.exists(self.densityPath):
            self.result = pd.read_excel(self.densityPath).set_index(unitsname)
        else:
            self.result = pd.DataFrame(index=self.units)

        self.maxThread = maxThread
        self.buffer = buffer
        self.decay = decay
        self.lock = Lock()

        return
    
    def saveResult(self) -> None:
        self.result.reset_index(inplace=True)
        self.result.rename(columns={"index": self.unitsname}, inplace=True)
        self.result.to_excel(self.densityPath, index=False)

        return

    def calDensity(self, path: str, calType: str | tuple[str, set[str]], additionalSave: str | None = None) -> None:
        futures = []
        futuresDict = {}
        bar = tqdm(total=len(self.units) * 2, desc="Processing")
        # Projection
        if not isinstance(calType, tuple):
            col = calType
            with rio.open(path) as src:
                if self.boundaies.crs != src.crs:
                    self.boundaies = self.boundaies.to_crs(src.crs)
                if self.evcs.crs != src.crs:
                    self.evcs = self.evcs.to_crs(src.crs)
        else: col = calType[0]

        self.result[col] = np.nan if col not in self.result.columns else None

        # Process
        excutor = ProcessPoolExecutor(max_workers=self.maxThread) if isinstance(calType, tuple) else ThreadPoolExecutor(max_workers=self.maxThread)
        for unit in self.units:
            bar.set_description("Processing {}".format(unit))
            evcsGeo = self.evcs.loc[(self.evcs[self.unitsname] == unit), ["geometry"]]
            future = excutor.submit(self.calOneUnitByRaster, path, evcsGeo, unit) if not isinstance(calType, tuple) \
                else excutor.submit(self.calOneUnitByRoad, path, evcsGeo, (self.unitsname, unit), self.buffer, self.decay, calType[1], additionalSave)
            futures.append(future)
            futuresDict[future] = unit
            bar.update(1)

        for future in as_completed(futures):
            unit = futuresDict[future]
            try:
                Rci = future.result()
            except Exception as e:
                raise RuntimeError("{}: {}".format(unit, e))
            else:
                bar.update(1)
                with self.lock:
                    self.result.at[unit, col] = Rci

        excutor.shutdown()
        bar.close()

        return
    
    def calOneUnitByRaster(self, rasterPath: str, evcsGeo: gpd.GeoDataFrame, unit: str) -> np.floating | None:
        boundary = self.boundaies.loc[self.boundaies[BOUNDART.get(self.unitsname)] == unit].geometry
        if len(boundary) == 0 or len(evcsGeo) == 0:
            return None
        
        with rio.open(rasterPath, options=["NUM_THREADS=ALL_CPUS"]) as src:            
            croppedArray: np.ndarray
            croppedArray, croppedTransform = mask(
                src,
                boundary,
                crop=True,
                all_touched=True,
                nodata=src.nodata
            )
            
            croppedArray = croppedArray[~np.isnan(croppedArray) & (croppedArray != src.nodata)]
            if np.nansum(croppedArray) == 0:
                return None
            DPhigh = np.max(croppedArray)
            DPlow = np.min(croppedArray)
            diff = DPhigh - DPlow
            
            XCoords = evcsGeo.geometry.x.to_numpy().astype(np.float32)
            YCoords = evcsGeo.geometry.y.to_numpy().astype(np.float32)
            coords = np.column_stack((XCoords, YCoords))
            values = np.array([(val[0] - DPlow) / diff if val[0] != src.nodata else 0 for val in src.sample(coords)])

        return np.nanmean(values)
    
    @staticmethod
    def calOneUnitByRoad(
        roadsPath: str,
        evcsGeo: gpd.GeoDataFrame,
        unit: tuple[str, str],
        buffers: int, decay: str,
        roadsLevel: set[str],
        savePath: str | None = None
    ) -> float | None:
        
        if unit[0] == "level1":
            roadsPath = os.path.join(roadsPath, "{}.gpkg".format(unit[1]))
            layer = "edges"
        else:
            raise RuntimeError("Only support country level (level1) at present.")
        
        roads = gpd.read_file(roadsPath, layer=layer, encoding="utf-8")
        roads = roads[["u", "v", "key", "length", "highway", "geometry"]]
        # Filter by roads level
        mask = [
            bool(set(x if isinstance(x, list) else [x]) & roadsLevel) for x in roads["highway"]
        ]
        roads = roads[mask]
        if roads.shape[0] == 0:
            return np.nan # No corresponding roads
        if roads.crs is None:
            raise RuntimeError("Roads do not have correct crs.")

        centroid = roads.union_all().centroid
        utm_zone = get_utm_zone(centroid.y, centroid.x)
        roads = roads.to_crs(utm_zone)
        # roads.to_crs(epsg=4479, inplace=True)
        roadsBuffer = roads.buffer(buffers)
        # evcsGeo.to_crs(epsg=4479, inplace=True)
        evcsGeo = evcsGeo.to_crs(utm_zone)
        evcsIdx = evcsGeo.sindex

        results = np.empty([roads.shape[0]], dtype=np.float64)
        for i, row in enumerate(roads.itertuples()):
            idx: pd.Index = getattr(row, "Index")
            geom: LineString = getattr(row, "geometry")
            buffer = roadsBuffer[idx]

            # Find evcs points
            possibleMatchesIdx = evcsIdx.intersection(buffer.bounds) # type: ignore
            possibleMatches = evcsGeo.iloc[possibleMatchesIdx]
            evcsInBuffer = possibleMatches[possibleMatches.intersects(buffer)]

            if len(evcsInBuffer) == 0 or geom.length == 0:
                result = np.nan
            else:
                x = evcsInBuffer.geometry.apply(lambda pt: decayFunc(geom.distance(pt), buffers, decay))
                result = x.sum() / geom.length

            results[i] = result

        roads["roadsDens"] = results
        roads.fillna(0, inplace=True)
        roads["roadsDens"] = roads["roadsDens"] * roads["length"]

        if savePath is not None:
            None if os.path.exists(savePath) else os.makedirs(savePath)
            roads.to_crs(epsg=4326, inplace=True)
            roads.to_file(os.path.join(savePath, "{}.gpkg".format(unit[1])), layer="edges", encoding="utf-8")

            # Add nodes
            nodes = gpd.read_file(roadsPath, layer="nodes", encoding="utf-8")
            nodes = nodes[["osmid", "x", "y", "geometry"]]
            keys = set(roads["u"]).union(set(roads["v"]))
            nodes = nodes[nodes["osmid"].isin(keys)]
            nodes.to_file(os.path.join(savePath, "{}.gpkg".format(unit[1])), layer="nodes", encoding="utf-8")

        return roads["roadsDens"].sum() / roads["length"].sum()

# Debug
if __name__ == "__main__":
    RESULT = r"_Data/Global_Country_2025" # Path where the merged EVCS data is saved
    a = calDensity(RESULT, maxThread=64)
    # a.calDensity(r"C:\\0_PolyU\\global_gdp\\gdp_2020.tif", "GDP")
    # # a.calOneUnitByRoad(
    # #     r"D:\\roadsGraph_Clean",
    # #     a.evcs.loc[(a.evcs[a.unitsname] == "USA"), ["geometry"]],
    # #     ("level1", "USA"),
    # #     a.buffer, a.decay,
    # #     {"motorway", "motorway_link", "trunk", "trunk_link"},
    # #     savePath=r"D:"
    # # )
    a.calDensity(
        r"_Data/roadsGraph_Clean", # Root path of roads data
        ("mainRoad", {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link"}),
        os.path.join(RESULT, "density_roads")
    )
    # a.calDensity(r"C:\\0_PolyU\\globalPOI_2025\\POI_1.tif", "POI_01")
    # a.calDensity(r"C:\\0_PolyU\\globalPOI_2025\\POI_2.tif", "POI_02")
    # a.calDensity(r"C:\\0_PolyU\\globalPOI_2025\\POI_3.tif", "POI_03")

    a.saveResult()
    # evcsGeo = a.evcs.loc[(a.evcs[a.unitsname] == "VCT"), ["geometry"]]
    # a.calOneUnitByRaster(r"C:\0_PolyU\globalPOI_2025\POI_2.tif", evcsGeo,"VCT")

    