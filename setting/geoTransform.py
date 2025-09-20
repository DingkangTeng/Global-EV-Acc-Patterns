import pandas as pd
import geopandas as gpd

def geoTransform(
    df: pd.DataFrame | gpd.GeoDataFrame,
    lng: str = "", lat: str = "",
    fromCRS: int = 4326, toCRS: int = 4326
) -> gpd.GeoDataFrame:
    
    if isinstance(df, gpd.GeoDataFrame):
        gdf = df.to_crs(epsg=toCRS)
    else:
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lng], df[lat]), crs="EPSG:{}".format(fromCRS))
        if toCRS != fromCRS:
            gdf = gdf.to_crs(epsg=toCRS)
    
    gdf["lng"] = gdf.geometry.x
    gdf["lat"] = gdf.geometry.y
    
    return gdf