import geopandas as gpd

df = gpd.read_file(r"_Data/test/NLD.gpkg", layer="cities", encoding="utf-8")
print(df[df["population"]>=500000])