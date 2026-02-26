import os
import pandas as pd

from ..setting import STANDER_NAME, FORMAT
from . import *
from ..setting.finddir import findFiles

def merge(root: str, result: str, formats: int = 0) -> None:
    count = []
    for folder in os.listdir(root):
        filePaths = findFiles(os.path.join(root, folder))

        if len(filePaths) == 0:
            continue
        
        source = folder.split("_")[0]

        for filePath in filePaths:
            country = STANDER_NAME.get(os.path.basename(filePath).split('.')[0], None)
            if country is None:
                continue
            if filePath.endswith("gdb"):
                if source == "Open Charger Map Data 2025":
                    filePath = (filePath, "OCM_Station")
                else:
                    continue

            if source == "Alternative Fuels Data Center":
                df, subcount = alternativeFuels(filePath)
            elif source == "DriveSouthAfrica":
                df, subcount = driveSouthAfrica(filePath)
            elif source == "European Commission Data 2025":
                df, subcount = europeanCommission(filePath, filters="0801")
            elif source == "HK":
                df, subcount = hk(filePath)
            elif source == "Korea":
                df, subcount = electromaps(filePath)
            elif source == "Macau":
                df, subcount = aodian(filePath)
            elif source == "New Zealand":
                df, subcount = newZealand(filePath)
            elif source == "Open Charger Map Data 2025":
                df, subcount = openChargerMap(filePath)
            elif source == "PlugShare Data 2025":
                df, subcount = plugShare(filePath)
            elif source =="tvip":
                df, subcount = tvip(filePath)
            elif source == "amap":
                df, subcount = amap(filePath)
            elif source == "GogoEV":
                df, subcount = gogoEV(filePath)
            else:
                continue
            
            if df is None or subcount is None:
                continue
                
            count.extend(subcount)
            
            df.drop_duplicates(subset=["UUID"], inplace=True)
            if formats > 10:
                df.to_csv(os.path.join(result, "{}.csv".format(country)), index=False, encoding="utf-8")
            else:
                df.to_file(os.path.join(result, "{}.{}".format(country, FORMAT.get(formats, "csv"))), index=False, encoding="utf-8")
            
    
    pd.DataFrame(count, columns=["fileName", "country", "stationNum", "pointsNum"]).to_excel(os.path.join(result, "summary.xlsx"), index=False)

    return

if __name__ == "__main__":
    ROOT = r"_Data\\Data Source 2025"
    RESULT = r"_Data\\Global_Country_2025"
    merge(ROOT, RESULT, 0)
    mergeByMaxRecord(RESULT)