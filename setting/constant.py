# Standard settings
FORMAT = {
    0: "geojson",
    11: "csv"
}

# Input
STANDER_NAME = {
    "Canada_alt_fuel_stations (Sep 1 2025)": "CAN",
    "USA_alt_fuel_stations (Sep 1 2025)": "USA",
    "driveSouthAfrica": "ZAF",
    "charging_points_EU_0801_read": "EUCommission",
    "goGoEV": "JPN",
    u"香港島_停车场": "HKG",
    "Macau Chargers": "MAC",
    "KOR": "KOR",
    "Macau_ev_stations_2025": "MAC",
    "EV_Roam_charging_stations_8533884045861215045": "NZL",
    "EVCharger": "OCM",
    "charger_shp": "PlugShare",
    "all_charger_data_combined": "PlugShare",
    "chn2025": "CHN"
}

# Output
OUTPUT_COL = ["UUID", "sources", "level1", "level2", "level3", "lat", "lng", "pointsNumber", "DCNumber", "ACNumber"]
# UUID, Sources file name, Country, Province/State, City/County, Latitude, Longitude, Charging Points Number, DC Number, AC Number

# Geo
ZAF_PROVINCE = set([
    "Eastern Cape", "Free State", "Gauteng", "KwaZulu-Natal", "Limpopo", "Mpumalanga", "North West", "Northern Cape", "Western Cape"
])

ZAF_CITIES = {
    "Eastern Cape": set([
        "Butterworth", "Dikeni", "East London", "Gqeberha", "Graaff-Reinet", "Kariega", "Komani", "Makhanda", "Mthatha", "Qonce", "Zwelitsha"
    ]),
    "Free State": set([
        "Bethlehem", "Bloemfontein", "Jagersfontein", "Kroonstad", "Odendaalsrus", "Parys", "Phuthaditjhaba", "Sasolburg", "Virginia", "Welkom"
    ]),
    "Gauteng": set([
        "Benoni", "Boksburg", "Brakpan", "Carletonville", "Germiston", "Johannesburg", "Krugersdorp", "Pretoria", "Randburg", "Randfontein",
        "Roodepoort", "Soweto", "Springs", "Vanderbijlpark", "Vereeniging"
    ]),
    "KwaZulu-Natal": set([
        "Durban", "Empangeni", "Newcastle", "Pietermaritzburg", "Pinetown", "Ulundi", "Umlazi", "uMnambithi"
    ]),
    "Limpopo": set([
        "Giyani", "Lebowakgomo", "Musina", "Phalaborwa", "Polokwane", "Seshego", "Sibasa", "Thabazimbi"
    ]),
    "Mpumalanga": set([
        "Emalahleni", "Mbombela", "Secunda"
    ]),
    "North West": set([
        "Klerksdorp", "Mahikeng", "Mmabatho", "Potchefstroom", "Rustenburg"
    ]),
    "Northern Cape": set([
        "Kimberley", "Kuruman", "Port Nolloth"
    ]),
    "Western Cape": set([
        "Bellville", "Cape Town", "Constantia", "George", "Hopefield", "Oudtshoorn", "Paarl", "Simon’s Town", "Stellenbosch",
        "Swellendam", "Worcester"
    ])
}

NZL_PROVINCE = set([
    "Auckland", "Bay of Plenty", "Canterbury", "Gisborne", "Hawke's Bay", "Manawatu-Wanganui", "Marlborough", "Nelson", "Northland",
    "Otago", "Southland", "Taranaki", "Tasman", "Waikato", "Wellington", "West Coast", "Chatham Islands"
])