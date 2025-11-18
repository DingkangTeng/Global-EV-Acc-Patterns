import geopandas as gpd
import sys

print(sys.path)

df = gpd.read_file("_Data/built_up_area/GHUB2018.gpkg")

print(df)


print(sys.executable)