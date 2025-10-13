import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from pyproj import Transformer

def geoTransform(
    df: pd.DataFrame | gpd.GeoDataFrame,
    lng: str = "", lat: str = "",
    fromCRS: int = 4326, toCRS: int = 4326
) -> gpd.GeoDataFrame:
    
    # transformer = Transformer.from_crs(f"EPSG:{fromCRS}", f"EPSG:{toCRS}")
    # geometry = [Point(xy) for xy in zip(df[lng], df[lat])]
    # gdf = gpd.GeoDataFrame(df, geometry=geometry)
    # gdf['lat'], gdf['lng'] = zip(*[transformer.transform(x, y) for x, y in zip(gdf.geometry.x, gdf.geometry.y)])
    # gdf.geometry = gpd.GeoSeries([Point(xy) for xy in zip(gdf['lng'], gdf['lat'])])
    # gdf.set_crs(epsg=toCRS, inplace=True)
    
    if isinstance(df, gpd.GeoDataFrame):
        gdf = df.to_crs(epsg=toCRS)
    else:
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lng], df[lat]), crs="EPSG:{}".format(fromCRS))
        if toCRS != fromCRS:
            gdf = gdf.to_crs(epsg=toCRS)
    
    gdf["lng"] = gdf.geometry.x
    gdf["lat"] = gdf.geometry.y
    
    return gdf