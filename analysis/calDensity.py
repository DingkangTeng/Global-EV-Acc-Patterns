import os
import rasterio as rio
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import LineString
from shapely.geometry.base import BaseGeometry
from tqdm import tqdm
from rasterio.mask import mask
from rasterio.transform import rowcol
from concurrent.futures import as_completed, ThreadPoolExecutor, ProcessPoolExecutor

from .__setting import eus, getUtmZone, decayFunc

BOUNDART = {
    "level1": "iso3_code"
}

FILE_DICT = {
    "POI_01.tif": "POI_01",
    "POI_02.tif": "POI_02",
    "POI_03.tif": "POI_03",
    "POI_ALL.tif": "POI_ALL",
    "global_pop_2025_CN_1km_R2025A_UA_v1.tif": "POP",
    "gdp_2020.tif": "GDP"
}

class calDensity:
    __slots__ = [
        "evcs", "roadsPath",
        "units", "unitsname", "eu", "countryList",
        "boundaies", "buffer", "decay",
        "result", "densityPath",
        "maxThread"
    ]

    def __init__(
        self,
        resultPath: str, roadsPath: str = "",
        unitsname: str = "level1",
        buffer: int = 1000, decay: str = "Gaussian",
        mergeEU: bool = True, maxThread: int = 1
    ) -> None:

        self.evcs = gpd.read_file(os.path.join(resultPath, "merge.gpkg"), layer="evcs", encoding="utf-8")[[unitsname, "geometry"]]
        self.boundaies = gpd.read_file(os.path.join(resultPath, "merge.gpkg"), layer=unitsname, encoding="utf-8") # from GAUL
        self.unitsname = unitsname
        self.roadsPath = roadsPath
        self.countryList = set()

        # Countries
        self.eu, nonEu = eus(resultPath)
        self.units = ["EUR_Merge"] + nonEu if mergeEU else self.eu + nonEu
        self.densityPath = os.path.join(resultPath, "density.xlsx")
        if os.path.exists(self.densityPath):
            self.result = pd.read_excel(self.densityPath).set_index(unitsname)
        else:
            self.result = pd.DataFrame(index=self.units)

        self.maxThread = maxThread
        self.buffer = buffer
        self.decay = decay

        return
    
    def saveResult(self) -> None:
        self.result.reset_index(inplace=True)
        self.result.rename(columns={"index": self.unitsname}, inplace=True)
        self.result.to_excel(self.densityPath, index=False)
        pd.DataFrame({"eligableCountry": list(self.countryList)}).to_csv(
            os.path.join(os.path.dirname(self.densityPath), "eligableCountries.csv"),
            encoding="utf-8",
            index=False
        )

        return

    def calDensity(self, path: str, calType: str | tuple[str, set[str]], additionalSave: str | None = None) -> None:
        futures = []
        futuresDict = {}
        bar = tqdm(
            total=len(self.units) * 2,
            desc="Processing {}".format(calType if not isinstance(calType, tuple) else calType[0]),
            unit="country"
        )
        # Projection
        if not isinstance(calType, tuple):
            col = calType
            with rio.open(path) as src:
                if self.boundaies.crs != src.crs:
                    self.boundaies = self.boundaies.to_crs(src.crs)
                if self.evcs.crs != src.crs:
                    self.evcs = self.evcs.to_crs(src.crs)
        else: col = calType[0]

        # Initialize result column
        if col not in self.result.columns: self.result[col] = np.nan

        # Initialize gini column
        gini = "{}_Gini".format(col)
        if not isinstance(calType, tuple) and gini not in self.result.columns:
            self.result[gini] = np.nan

        # Process
        excutor = ProcessPoolExecutor(max_workers=self.maxThread) if isinstance(calType, tuple) else ThreadPoolExecutor(max_workers=self.maxThread)
        for unit in self.units:
            bar.set_description(f"Reading file {unit} for {col}")
            evcsGeo = self.evcs.loc[(self.evcs[self.unitsname] == unit), ["geometry"]] if unit != "EUR_Merge" \
                else self.evcs.loc[(self.evcs[self.unitsname].isin(self.eu)), ["geometry"]]
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
                bar.set_description(f"Process {unit} for {col} finished")
                bar.update(1)
                # Calculate units by roads
                if isinstance(calType, tuple):
                    self.result.at[unit, col] = Rci
                # Calcualte units by rasters
                else:
                    self.result.at[unit, col] = Rci[0]
                    self.result.at[unit, gini] = Rci[1]
                    if Rci[2]: self.countryList.add(unit)

        excutor.shutdown()
        bar.close()

        return
        
    def calOneUnitByRaster(
        self,
        rasterPath: str,
        evcsGeo: gpd.GeoDataFrame | pd.Series,
        unit: str
    ) -> tuple[np.floating | None, np.floating | None, bool]:
        EVCSOver10 = False
        
        # Get built-up area
        roadsPath = os.path.join(self.roadsPath, "{}.gpkg".format(unit))
        if "cities" not in gpd.list_layers(roadsPath)["name"].tolist():
            return None, None, EVCSOver10
        
        boundaries = gpd.read_file(roadsPath, layer="cities", encoding="utf-8")[["geometry", "population", "city", "urbanId"]].set_index("city")
        if len(boundaries) == 0 or len(evcsGeo) == 0:
            return None, None, EVCSOver10
        
        # Calcuate the density by built-up area
        n = boundaries.shape[0]
        countryResults = np.empty([n, 2], dtype=np.float64)
        EVCSNum = np.empty(n, dtype=np.uint16)
        with rio.open(rasterPath, options=["NUM_THREADS=ALL_CPUS"]) as src:
            for i, row in enumerate(boundaries.itertuples()):
                boundary: BaseGeometry = getattr(row, "geometry")

                # Get evcs points
                possibleMAtch = np.array(evcsGeo.sindex.intersection(boundary.bounds), dtype=np.int64)
                evcsGeoSub = evcsGeo.iloc[possibleMAtch]
                evcsGeoSub = evcsGeoSub[evcsGeoSub.intersects(boundary)]

                # Check validation
                EVCSNum[i] = evcsGeoSub.shape[0]
                if EVCSNum[i] > 10: EVCSOver10 = True
                        
                croppedArray: np.ndarray
                croppedArray, _ = mask(
                    src,
                    [boundary],
                    crop=True,
                    all_touched=True,
                    nodata=src.nodata
                )
                
                croppedArray = croppedArray[~np.isnan(croppedArray) & (croppedArray != src.nodata)]
                # No corresponding raster data in the boundary
                if np.nansum(croppedArray) == 0:
                    countryResults[i, 0] = np.nan
                    countryResults[i, 1] = np.nan
                    continue

                DPhigh = np.max(croppedArray)
                DPlow = np.min(croppedArray)
                diff = DPhigh - DPlow
                
                XCoords = evcsGeoSub.geometry.x.to_numpy().astype(np.float32)
                YCoords = evcsGeoSub.geometry.y.to_numpy().astype(np.float32)
                coords = np.column_stack((XCoords, YCoords))
                values = np.array([(val[0] - DPlow) / diff if val[0] != src.nodata else 0 for val in src.sample(coords)])

                # Get raster results
                ## Get corresponding row and col index
                rows, cols = rowcol(src.transform, XCoords, YCoords)
                idxs = np.ravel_multi_index((rows, cols), src.shape)
                raster = pd.DataFrame({"values": values, "idxs": idxs}).dropna()
                raster = raster.groupby(by="idxs").agg(
                    evcs=("idxs", "count"),
                    value=("values", "first")
                )

                countryResults[i, 0] = np.nanmean(values) if len(values) > 0 else np.nan
                countryResults[i, 1] = self.gini(raster["value"].to_numpy(), raster["evcs"].to_numpy())

        # Save gini result for each city
        savePath = os.path.join(os.path.dirname(self.densityPath), "giniResult")
        if not os.path.exists(savePath): os.mkdir(savePath)
        file = os.path.basename(rasterPath)
        df = pd.DataFrame(
            {
                "density": countryResults[:, 0],
                "gini": countryResults[:, 1],
                "population": boundaries["population"],
                "urbanId": boundaries["urbanId"]
            },
            index=boundaries.index
        )
        # Save results
        df.to_csv(
            os.path.join(savePath, f"{unit}_{FILE_DICT.get(file, file)}.csv"), encoding="utf-8"
        )

        return np.nanmean(countryResults[:, 0]), np.nanmedian(df.dropna()["gini"].to_numpy()), EVCSOver10
    
    @staticmethod
    def calOneUnitByRoad(
        roadsPath: str,
        evcsGeo: gpd.GeoDataFrame | pd.Series,
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
        utmZone = getUtmZone(centroid.y, centroid.x)
        roads = roads.to_crs(utmZone)
        roadsBuffer = roads.buffer(buffers)
        evcsGeo = evcsGeo.to_crs(utmZone)
        evcsIdx = evcsGeo.sindex

        results = np.empty([roads.shape[0]], dtype=np.float64)
        for i, row in enumerate(roads.itertuples()):
            idx: pd.Index = getattr(row, "Index")
            geom: LineString = getattr(row, "geometry")
            buffer = roadsBuffer[idx]

            # Find evcs points
            possibleMatchesIdx = evcsIdx.intersection(buffer.bounds) # type: ignore
            possibleMatches = evcsGeo.iloc[possibleMatchesIdx]
            evcsInBuffer = possibleMatches[possibleMatches.intersects(buffer)] # type: ignore

            if len(evcsInBuffer) == 0 or geom.length == 0:
                result = np.nan
            else:
                x = evcsInBuffer.geometry.apply(lambda pt: decayFunc(geom.distance(pt), buffers, decay))
                result = x.sum() / geom.length * 1000 # cout pre km

            results[i] = result

        roads["roadsDens"] = results.copy()
        roads.fillna(0, inplace=True)
        results = results * roads["length"]

        if savePath is not None:
            None if os.path.exists(savePath) else os.makedirs(savePath)
            roads.to_crs(epsg=4326, inplace=True)
            roads.to_file(os.path.join(savePath, "{}.gpkg".format(unit[1])), layer="edges_{}".format(buffers), encoding="utf-8")

            # Add nodes
            nodes = gpd.read_file(roadsPath, layer="nodes", encoding="utf-8")
            nodes = nodes[["osmid", "x", "y", "geometry"]]
            keys = set(roads["u"]).union(set(roads["v"]))
            nodes = nodes[nodes["osmid"].isin(keys)]
            nodes.to_file(os.path.join(savePath, "{}.gpkg".format(unit[1])), layer="nodes", encoding="utf-8")

        return results.sum() / roads["length"].sum()
    
    @staticmethod
    def gini(indicator: np.ndarray, evcs:np.ndarray) -> np.floating:
        # Special case: if only one grid cell has nonzero indicatior
        # Return nan if total count less than 10, because no significant meaning for gini
        if np.count_nonzero(evcs) < 10: return np.nan

        # Sort values by EVCS
        conditions = [
            indicator == 0,
            (indicator != 0) & (evcs == 0),
            (indicator != 0) & (evcs != 0)
        ]
        choices = [
            0,
            np.inf,
            indicator / evcs
        ]
        preCap = np.select(conditions, choices, default=np.nan)
        sortedIndices = np.argsort(-preCap)
        sortedIndicator = indicator[sortedIndices]
        sortedEVCS = evcs[sortedIndices]

        # Compute cumulative EVCS and cumulative indicatior
        totalIndicator = sortedIndicator.sum()
        if totalIndicator == 0: return np.float64(0)
        totalEVCS = sortedEVCS.sum()

        # Normalize cumulative EVCS and indicatior (range 0–1)
        cumInidcator = np.cumsum(sortedIndicator) / totalIndicator
        cumEVCS = np.cumsum(sortedEVCS) / totalEVCS
        ## Add 0
        lack0 = cumInidcator[0] != 0 or cumEVCS[0] != 0
        cumInidcator = np.insert(cumInidcator, 0, 0) if lack0 else cumInidcator 
        cumEVCS = np.insert(cumEVCS, 0, 0) if lack0 else cumEVCS # Add 0

        # Compute the Gini coefficient using the trapezoidal rule (Lorenz curve area)
        return np.float64(1 - 2 * np.trapezoid(cumEVCS, cumInidcator))

# Debug
if __name__ == "__main__":
    # RESULT = r"__Data/Global_Country_2025" # Path where the merged EVCS data is saved
    # ROADS_RESULT = os.path.join(RESULT, "density_roads")
    # POI = r"__Data/POI"
    # POP = r"__Data/global_pop_2025_CN_1km_R2025A_UA_v1.tif"
    # GDP = r"__Data/gdp_2020.tif"
    RESULT = r"C:\0_PolyU\data-global-ev-2025\__Data\Global_Country_2025" # Path where the merged EVCS data is saved
    ROADS_RESULT = os.path.join(RESULT, "density_roads")
    POI = r"D:\globalPOI_2025"
    POP = r"D:\Population_Related\global_pop_2025_CN_1km_R2025A_UA_v1.tif"
    GDP = r"D:\global_gdp\gdp_2020.tif"
    # for buffer in [1000, 3000, 5000]:
    #     a = calDensity(RESULT, maxThread=64, buffer=buffer)
    #     a.calDensity(
    #         r"_Data/roadsGraph_Clean", # Root path of roads data
    #         ("mainRoad_{}".format(buffer), {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link"}),
    #         ROADS_RESULT
    #     )
    #     a.saveResult()
    
    a = calDensity(RESULT, roadsPath=ROADS_RESULT, mergeEU=False, maxThread=32)
    a.calDensity(os.path.join(POI, "POI_1.tif"), "POI_01")
    a.calDensity(os.path.join(POI, "POI_2.tif"), "POI_02")
    a.calDensity(os.path.join(POI, "POI_3.tif"), "POI_03")
    a.calDensity(os.path.join(POI, "POI_ALL.tif"), "POI_ALL")
    a.calDensity(POP, "POP")
    a.calDensity(GDP, "GDP")
    a.saveResult()

    # evcsGeo = a.evcs.loc[(a.evcs[a.unitsname] == "ETH"), ["geometry"]]
    # print(a.calOneUnitByRaster(os.path.join(POI, "POI_1.tif"), evcsGeo,"ETH"))

    