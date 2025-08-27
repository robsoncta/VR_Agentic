from pathlib import Path
import pandas as pd

def load_first_sheet(path: str) -> pd.DataFrame:
    """Carrega a primeira aba de um Excel e padroniza os nomes das colunas."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    df = pd.read_excel(p, sheet_name=0)
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df


def save_layout(df: pd.DataFrame, path: str, sheet_name: str = "COMPRA") -> str:
    """Salva DataFrame em Excel, criando pastas se necessário."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)  # cria diretório se não existir
    with pd.ExcelWriter(p, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return str(p)
