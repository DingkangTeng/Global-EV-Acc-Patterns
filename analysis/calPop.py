import os
import geopandas as gpd
import pandas as pd
import numpy as np
import rasterio as rio
from shapely.geometry.base import BaseGeometry
from shapely.geometry import box
from shapely import make_valid
from rasterio.mask import mask
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm

from .__setting import LACK_POP, eus

def calPop(
    countries: set[str],
    urbansTuple: tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, str] | tuple[gpd.GeoDataFrame, str],
    pops: str,
    savePath: str, maxThread: int = 1
) -> None:
    # Urban datasate has not been aggrated to city level
    if len(urbansTuple) == 3:
        urbans, cities, col = urbansTuple
        if urbans.crs is None or cities.crs is None:
            raise RuntimeError("GeoDataFrame has no CRS.")
        
        # Add cities name to urban
        urbansCentroid = urbans.copy()
        urbansCentroid["geometry"] = urbansCentroid["geometry"].centroid
        urbanName = gpd.sjoin(
            urbansCentroid,
            cities,
            how="left",
            predicate="within"
        )
        for row in urbanName.loc[urbanName["city"].isna()].itertuples():
            idx = getattr(row, "Index")
            geometry: BaseGeometry = getattr(row, "geometry")
            urbanPoint = geometry.centroid
            nearestCityIndex = cities.distance(urbanPoint).idxmin()
            urbanName.at[idx, "city"] = cities.at[nearestCityIndex, "city"]
        urbans["city"] = urbanName["city"]
        urbans["urbanId"] = urbans["urbanId"].astype(str)
        # Fixing geometry
        tqdm.write("Fixing geometry...")
        invalid_mask = ~urbans.geometry.is_valid
        urbans.loc[invalid_mask, "geometry"] = urbans.loc[invalid_mask, "geometry"].apply(make_valid)
        # Disslove same city
        tqdm.write("Dissolving geometry...")
        urbans = urbans.dissolve(
            by="city",
            aggfunc={
                "iso3": "first",
                "urbanId": lambda x: ','.join(x)
            }
        ).reset_index()

    # Aggregiated urban area
    else:
        urbans, col = urbansTuple
    
    bar = tqdm(total=len(countries), desc="Calculating", unit="country")
    futures = []
    futuresDict = {}
    with ProcessPoolExecutor(max_workers=maxThread) as executor:
        for country in countries:
            # Skip Kosovo, Åland, Guernsey, Gibraltar, Svalbard and Jan Mayen, Jersey (No population data)
            if country in LACK_POP:
                bar.update()
                continue
            # Urban area: USA contains PRI
            if country == "PRI":
                urban = urbans.loc[urbans[col] == "USA"]
            elif country == "EUR_Merge":
                eu, _ = eus(savePath)
                urban = urbans.loc[urbans[col].isin(eu)]
            else:
                urban = urbans.loc[urbans[col] == country]
            rasterPath = os.path.join(pops, "{}_allGender_allAge_merge.tif".format(country))
            with rio.open(rasterPath) as src:
                crs = src.crs.to_epsg()
            
            urban = urban.to_crs(epsg=crs) if urban.crs.to_epsg() != crs else urban # type: ignore
            future = executor.submit(oneCountryPop, urban, rasterPath, True)
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

def oneCountryPop(urban: gpd.GeoDataFrame, pop: str, subprocess: bool = False) -> gpd.GeoDataFrame:
    if not subprocess:
        bar = tqdm(total=urban.shape[0], desc="Calculating urban area", unit="cities")
    urban["population"] = 0.0

    with rio.open(pop, options=["NUM_THREADS=ALL_CPUS"]) as src:
        for row in urban.itertuples():
            idx: int = getattr(row, "Index")
            geom: BaseGeometry = getattr(row, "geometry")

            # Urban area: USA contains PRI
            if not geom.intersects(box(*src.bounds)):
                if not subprocess: bar.update() # type: ignore
                continue

            outImage, _ = mask(src, [geom], crop=True, all_touched=True, nodata=src.nodata)
            outImage[outImage == src.nodata] = 0

            urban.at[idx, "population"] += np.nansum(outImage)
            if not subprocess: bar.update()  # type: ignore
    
    urban.drop_duplicates(subset=["geometry"], inplace=True)
    urban.drop(urban[urban["population"] == 0.0].index, inplace=True)
    if not subprocess: bar.close() # type: ignore

    return urban     

if __name__ == "__main__":
    # # Urban area file path
    # urban = gpd.read_file(r"_Data/built_up_area/UB_2018.gpkg", encoding="utf-8")
    # urban = urban[["iso3", "geometry"]]
    # urban["urbanId"] = urban.index
    # cities = gpd.read_file(r"_Data/boundary/GAUL_2024_L2.gpkg", layer="GAUL_2024_L2", encoding="utf-8")
    # cities = cities[["disp_en", "geometry"]]
    # cities.columns = ["city", "geometry"]
    urban = gpd.read_file(r"_Data/built_up_area/builtUpArea_fixGeom.gpkg", encoding="utf-8")

    # Country list
    countries = pd.read_excel(r"_Data/Global_Country_2025/density.xlsx")
    countries.dropna(subset="mainRoad", inplace=True)
    countries = set(countries["level1"].unique().tolist())
    countries = {"EUR_Merge"}

    # Population raster root path
    pops = r"_Data/population_All"

    # Root path of saved roads data with density col (save path//density_roads)
    RESULT = r"_Data/Global_Country_2025/density_roads"

    calPop(countries, (urban, "iso3"), pops, RESULT, 32)
    # # Test
    # oneCountryPop(urban.loc[urban["iso3"] == "USA"], r"_Data/population_All/USA_allGender_allAge_merge.tif")