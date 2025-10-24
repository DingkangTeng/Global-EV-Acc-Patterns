import os
import rasterio as rio
import geopandas as gpd
import numpy as np
from rasterio import transform

class points2Raster:
    __slots__ = [
        "points",
        "crs", "transform", "shape",
    ]

    def __init__(self, rasterPath: str, pointsPath: str | tuple[str, str]) -> None:
        with rio.open(rasterPath) as src:
            self.crs = src.crs
            self.transform = src.transform
            self.shape = src.shape

        if isinstance(pointsPath, str):
            self.points = gpd.read_file(pointsPath, encoding="utf-8") if pointsPath.split('.')[-1] != "parquet" \
                else gpd.read_parquet(pointsPath)
        else:
            self.points = gpd.read_file(pointsPath[0], layer=pointsPath[1], encoding="utf-8")

        if self.points.crs != self.crs:
            self.points.to_crs(self.crs, inplace=True)

        return
    
    def process(self, savPath: str, useCatgory: int = 0) -> None:
        points = self.points[self.points["fsq_category_ids"] == useCatgory] if useCatgory > 0 else self.points

        rows, cols = transform.rowcol(self.transform, points.geometry.x, points.geometry.y)
        validMask = (rows >= 0) & (rows < self.shape[0]) & (cols >= 0) & (cols < self.shape[1])
        rows = np.array(rows)[validMask]
        cols = np.array(cols)[validMask]

        # Count number
        indices = rows * self.shape[1] + cols
        counts = np.bincount(indices, minlength=self.shape[0] * self.shape[1])
        resultRaster = counts.reshape(self.shape).astype(np.uint32)

        with rio.open(
            os.path.join(savPath, "POI_{}.tif".format(useCatgory)),
            'w',
            driver='GTiff',
            height=self.shape[0],
            width=self.shape[1],
            count=1,
            dtype=np.uint32,
            crs=self.crs,
            transform=self.transform,
            compress="lzw"
        ) as dst:
            dst.write(resultRaster, 1)

        return
        

# Debug
if __name__ == "__main__":
    a = points2Raster(r"C:\\0_PolyU\\global_gdp\\gdp_2020.tif", r"C:\\0_PolyU\\globalPOI_2015\\extract.parquet")
    # a.process(r"C:\\0_PolyU\\globalPOI_2015", 1)
    a.process(r"C:\\0_PolyU\\globalPOI_2015", 2)
    a.process(r"C:\\0_PolyU\\globalPOI_2015", 3)