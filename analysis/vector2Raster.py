import os
import rasterio as rio
import geopandas as gpd
import numpy as np
# try:
#     import cupy as np
# except Exception as e:
#     print(e, "Use CPU instead.")
from shapely.geometry import Polygon
from tqdm import tqdm
from typing import Any
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from threading import Lock

class vector2Raster:
    __slots__ = [
        "rasterPath",
        "width", "height", "crs", "transform", "nan",
        "resultRaster"
    ]

    def __init__(self, rasterPath: str) -> None:
        self.rasterPath = rasterPath
        with rio.open(rasterPath) as src:
            self.crs = src.crs
            self.transform = src.transform
            self.width = src.width
            self.height = src.height
            self.nan = src.nodata
        
        self.resultRaster = np.zeros((self.height, self.width), dtype=np.float32)

        return
    
    def processOneCountry(self, path: str | tuple[str, str]) -> None:
        if isinstance(path, str):
            vector = gpd.read_file(path, encoding="utf-8", usecols=["geometry"])
        else:
            vector = gpd.read_file(path[0], layer=path[1], encoding="utf-8")

        if vector.crs != self.crs:
            vector.to_crs(self.crs, inplace=True)
        
        pass
        

# Debug
if __name__ == "__main__":
    a = vector2Raster(r"C:\\0_PolyU\\global_gdp\\gdp_2020.tif")
    a.processOneCountry((r"C:\0_PolyU\test\JPN.gpkg", "edges"))