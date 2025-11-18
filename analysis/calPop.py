import os
import geopandas as gpd
import pandas as pd
import numpy as np
import rasterio as rio
from shapely.geometry.base import BaseGeometry
from rasterio.mask import mask
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm

def calPop(countries: set[str], urbans: gpd.GeoDataFrame, pops: str, savePath: str, maxThread: int = 1) -> None:
    if urbans.crs is None:
        raise RuntimeError("GeoDataFrame has no CRS.")
    
    bar = tqdm(total=len(countries), desc="Calculating", unit="country")
    futures = []
    futuresDict = {}
    with ProcessPoolExecutor(max_workers=maxThread) as executor:
        for country in countries:
            urban = urbans.loc[urbans["GID_0"] == country]
            rasterPath = os.path.join(pops, "{}_allGender_allAge_merge.tif".format(country))
            with rio.open(rasterPath) as src:
                crs = src.crs.to_epsg()
            
            urban = urban.to_crs(epsg=crs) if urban.crs.to_epsg() != crs else urban # type: ignore
            future = executor.submit(oneCountryPop, urban, rasterPath)
            futuresDict[future] = country
            futures.append(future)
        
        for future in as_completed(futures):
            country = futuresDict[future]
            try:
                countryCity: gpd.GeoDataFrame = future.result()
            except Exception as e:
                raise RuntimeError("{}: {}".format(country, e))
            else:
                countryCity.to_file(os.path.join(savePath, "{}.gpkg".format(country)), layer="cities", encoding="utf-8")
                bar.update()

    bar.close()

    return

def oneCountryPop(urban: gpd.GeoDataFrame, pop: str) -> gpd.GeoDataFrame:
    bar = tqdm(total=urban.shape[0], desc="Calculating urban area", unit="cities")
    urban["population"] = 0.0

    with rio.open(pop, options=["NUM_THREADS=ALL_CPUS"]) as src:
        for row in urban.itertuples():
            idx: int = getattr(row, "Index")
            geom = getattr(row, "geometry")

            outImage, _ = mask(src, [geom], crop=True, all_touched=True, nodata=src.nodata)
            outImage[outImage == src.nodata] = 0

            urban.at[idx, "population"] += np.nansum(outImage)
            bar.update()
    
    urban.drop_duplicates(subset=["geometry"], inplace=True)
    bar.close()
    return urban     

if __name__ == "__main__":
    # Urban area file path
    urban = gpd.read_file(r"C:\0_PolyU\data-global-ev-2025\_Data\urbanArea\urban_countries.geojson", encoding="utf-8")
    urban = urban[["GID_0", "GID_2", "NAME_1", "NAME_2", "geometry"]]

    # Country list
    countries = pd.read_excel(r"C:\0_PolyU\data-global-ev-2025\_Data\Global_Country_2025\density.xlsx")
    countries = set(countries["level1"].unique().tolist())

    # Population raster root path
    pops = r"D:\Population_Related\population_All"

    # Root path of saved roads data with density col (save path//density_roads)
    savePath = r"C:\0_PolyU\data-global-ev-2025\_Data\Global_Country_2025\test"

    calPop(countries, urban, pops, savePath, 16)