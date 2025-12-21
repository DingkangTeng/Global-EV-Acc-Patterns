# Skip Kosovo, Åland, Guernsey, Gibraltar, Svalbard and Jan Mayen, Jersey (No population data)
LACK_POP = {"XKX", "ALA", "GGY", "GIB", "SJM", "JEY"}

# EU country
def eus(resultPath: str) -> tuple[list[str], list[str]]:
    from pandas import read_csv
    from os.path import join
    countrylist = read_csv(join(resultPath, "merge_log.csv"), encoding="utf-8")[["fileName", "country_std"]]
    eu = countrylist[countrylist["fileName"] == "EUCommission"]["country_std"].tolist()
    # Special case
    eu.remove("UKR") # Not offically
    eu.remove("MDA") # Not offically
    eu.remove("IRL") # Island
    eu.remove("MLT") # Island
    eu.remove("CYP") # Island

    notEu = countrylist[countrylist["fileName"] != "EUCommission"]["country_std"].tolist()
    notEu = [x for x in notEu if len(x) < 4]
    notEu += ["IRL", "MLT", "CYP", "UKR", "MDA"]

    return eu, notEu