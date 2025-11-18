import geopandas as gpd
from iso3166 import countries

layer = "UB_2018"
df = gpd.read_file("_Data/built_up_area/GHUB2018.gpkg", layer=layer)
# ['UE_2018', 'UB_2018', 'UC_2018', 'EB_2018', 'UrbanOpenspace_2018', 'UrbanWater_2018']

StandardNames = {
    "South Korea": "Korea, Republic of",
    "North Korea": "Korea, Democratic People's Republic of",
    "United Kingdom": "United Kingdom of Great Britain and Northern Ireland",
    "Republic of Serbia": "Serbia",
    "Moldova": "Moldova, Republic of",
    "Macedonia": "North Macedonia",
    "Bolivia": "Bolivia, Plurinational State of",
    "The Bahamas": "Bahamas",
    "Venezuela": "Venezuela, Bolivarian Republic of",
    "Russia": "Russian Federation",
    "Iran": "Iran, Islamic Republic of",
    "Brunei": "Brunei Darussalam",
    "East Timor": "Timor-Leste",
    "Vietnam": "Viet Nam",
    "Laos": "Lao People's Democratic Republic",
    "Ivory Coast": "Côte d'Ivoire",
    "United Republic of Tanzania": "Tanzania, United Republic of",
    "Somaliland": "Somalia",
    "Democratic Republic of the Congo": "Congo, Democratic Republic of the",
    "Republic of the Congo": "Congo",
    "Cyprus No Mans Area": "Cyprus",
    "Northern Cyprus": "Cyprus",
    "Turkey": "Türkiye",
    "Syria": "Syrian Arab Republic"
}

df["Country"] = df["Country"].apply(lambda x: StandardNames.get(x, x))
df["iso3"] = df["Country"].apply(lambda x: countries.get(x).alpha3)

df.to_file("_Data/built_up_area/{}.shp".format(layer), index=False)