import pandas as pd

def uuids(df: pd.DataFrame, col: str | list[str]) -> pd.Series:
    if isinstance(col, str):
        return df[col]
    
    else:
        result = df[col[1]]
        for c in col[1:]:
            result = result + "-" + df[c]
        return result