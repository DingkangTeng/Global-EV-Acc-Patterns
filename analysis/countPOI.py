import os
import geopandas as gpd
import numpy as np
import rasterio as rio
from shapely.geometry.base import BaseGeometry
from rasterio.mask import mask

def countPOI(resultPath: str, poiPath: str, places: list[tuple[str, str]]) -> None:
    savePath = os.path.join(resultPath, "countPOI")
    os.makedirs(savePath, exist_ok=True)

    evcs = gpd.read_file(
        os.path.join(resultPath, "merge.gpkg"),
        layer="evcs",
        encoding="utf-8"
    )[["level1", "geometry"]]

    for iso3, city in places:
        df = gpd.read_file(
            os.path.join(resultPath, "density_roads", "{}.gpkg".format(iso3)),
            layer="cities"
        )
        geom = df[df["city"] == city].geometry.union_all()
        subEVCS = evcs[evcs["level1"] == iso3].geometry
        __calByCountry(
            geom, poiPath, subEVCS,
            os.path.join(savePath, "{}_{}.csv".format(iso3, city.replace(", ", "_").replace(" ", "_")))
        )

    return

def __calByCountry(geom: BaseGeometry, poiPath: str, evcs: gpd.GeoSeries, savePath: str) -> None:
    if geom is None or geom.is_empty:
        print(f"警告: 几何为空，跳过 {savePath}")
        return
    
    with (
        rio.open(poiPath) as src,
        rio.Env(NUM_THREADS="ALL_CPUS")
    ):
        outImage, _ = mask(
            src, [geom],
            crop=True, filled=False, all_touched=True, nodata=0
        )
        values, counts = np.unique(outImage.compressed(), return_counts=True)
        df = gpd.pd.DataFrame({"poi_counts": values, "counts": counts})

        subEVCS = evcs[evcs.intersects(geom)]
        if not subEVCS.empty:
            coords = [(point.x, point.y) for point in subEVCS.geometry] # type: ignore
            sampledVals = []
            for xy in coords:
                for val in src.sample([xy], 1):   # Band 1
                    sampledVals.append(val[0])
                    break
            sampledVals = np.array(sampledVals)
            valid = sampledVals != 0
            valuesEVCS, countsEVCS = np.unique(sampledVals[valid], return_counts=True)
        else:
            valuesEVCS = countsEVCS = np.array([], dtype=values.dtype)
        dfEVCS = gpd.pd.DataFrame({"poi_counts": valuesEVCS, "counts_with_EVCS": countsEVCS})

        gpd.pd.merge(df, dfEVCS, how="outer", on="poi_counts").fillna(0).sort_values(
            by="poi_counts", ignore_index=True
        ).to_csv(savePath, index=False, encoding="utf-8")

    return

if __name__ == "__main__":
    RESULT = r"C:\0_PolyU\data-global-ev-2025\__Data\Global_Country_2025" # Path where the merged EVCS data is saved
    POI = r"D:\globalPOI_2025"

    places = [
        # ("HKG", "China, Hong Kong SAR"),
        # ("SGP", "Central Singapore, Singapore"),
        # ("USA", "Los Angeles, California, United States of America"),
        # ("SWE", "Stockholm, Stockholm, Sweden"),
        # ("BRA", "São Paulo, São Paulo, Brazil"),
        # ("AUS", "North Adelaide, South Australia, Australia"),
        # ("USA", "Dallas, Texas, United States of America"),
        ("TWN", "Taipei, Taiwan Province of China"),
        ("JPN", "Suginami-Ku, Tokyo, Japan"),
        # ("AUS", "Lambton - New Lambton, New South Wales, Australia"),
        # ("CHN", "Beijing Municipality, Beijing Municipality, China")
    ]

    countPOI(RESULT, os.path.join(POI, "POI_ALL.tif"), places)
