import geopandas as gpd

# df = gpd.read_file(r"_Data/Global_Country_2025/density_roads/allCaledCities.gpkg", encoding="utf-8")
# print(df.columns)
from analysis import eus
import os
import rasterio as rio
from rasterio.merge import merge
es, neu = eus(r"_Data/Global_Country_2025")
pops = r"_Data/population_All"

rasters = []
for country in es:
    rasters.append(os.path.join(pops, "{}_allGender_allAge_merge.tif".format(country)))

src_files = [rio.open(fp, options=["NUM_THREADS=ALL_CPUS"]) for fp in rasters]
mosaic, out_trans = merge(src_files)

out_meta = src_files[0].meta.copy()
out_meta.update({
    "driver": "GTiff",
    "height": mosaic.shape[1],
    "width": mosaic.shape[2],
    "transform": out_trans,
    "crs": src_files[0].crs  # 使用第一个文件的坐标系
})

with rio.open('output_mosaic.tif', 'w', **out_meta, options=["NUM_THREADS=ALL_CPUS"]) as dest:
    dest.write(mosaic)

for src in src_files:
    src.close()