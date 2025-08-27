from pathlib import Path
import pandas as pd

def load_first_sheet(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    xls = pd.ExcelFile(p)
    df = pd.read_excel(xls, xls.sheet_names[0])
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df

def save_layout(df: pd.DataFrame, path: str, sheet_name: str = "COMPRA") -> str:
    p = Path(path)
    with pd.ExcelWriter(p, engine="xlsxwriter") as w:
        df.to_excel(w, index=False, sheet_name=sheet_name)
    return str(p)