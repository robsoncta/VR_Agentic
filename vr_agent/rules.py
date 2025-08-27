from datetime import datetime
from typing import Optional
import numpy as np
import pandas as pd

UF_LIST = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG",
           "PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"]

PERIOD_START = pd.Timestamp(2025, 4, 15)
PERIOD_END   = pd.Timestamp(2025, 5, 15)

def normalize_matricula(df: pd.DataFrame) -> pd.DataFrame:
    if "MATRICULA" in df.columns:
        df["MATRICULA"] = (df["MATRICULA"].astype(str)
                           .str.replace(r"\.0$", "", regex=True).str.strip())
    return df

def build_exclusion_set(deslig, afast, aprendiz, estagio) -> set:
    excl = set()
    if deslig is not None and "MATRICULA" in deslig.columns:
        excl.update(deslig["MATRICULA"].astype(str).str.replace(r"\.0$","",regex=True).str.strip())
    if aprendiz is not None and "MATRICULA" in aprendiz.columns:
        excl.update(aprendiz["MATRICULA"])
    if estagio is not None and "MATRICULA" in estagio.columns:
        excl.update(estagio["MATRICULA"])
    if afast is not None and {"MATRICULA","NA COMPRA?"}.issubset(afast.columns):
        mask = afast["NA COMPRA?"].astype(str).str.upper().str.strip().isin(["N","NAO","NÃO","NO"])
        excl.update(afast.loc[mask,"MATRICULA"])
    return excl

def exclude_by_cargo(df: pd.DataFrame) -> pd.DataFrame:
    if "TITULO DO CARGO" in df.columns:
        cargo = df["TITULO DO CARGO"].astype(str).str.upper()
        bad = cargo.str.contains("DIRETOR") | cargo.str.contains("ESTAGI") | cargo.str.contains("APRENDIZ")
        return df.loc[~bad].copy()
    return df

def map_dias_uteis(df_base: pd.DataFrame, diasuteis: Optional[pd.DataFrame]) -> pd.DataFrame:
    if diasuteis is None:
        df_base["DIAS_UTEIS"] = np.nan
        return df_base
    du = diasuteis.rename(columns={diasuteis.columns[0]:"SINDICATO_NOME",
                                   diasuteis.columns[1]:"DIAS_UTEIS"}).copy()
    du["SINDICATO_NOME"] = du["SINDICATO_NOME"].astype(str).str.upper().str.strip()
    du = du[pd.to_numeric(du["DIAS_UTEIS"], errors="coerce").notna()].copy()
    du["DIAS_UTEIS"] = du["DIAS_UTEIS"].astype(int)

    if "SINDICATO" in df_base.columns:
        df_base["SINDICATO_NOME"] = df_base["SINDICATO"].astype(str).str.upper().str.strip()
        df_base = df_base.merge(du, on="SINDICATO_NOME", how="left")
    else:
        df_base["DIAS_UTEIS"] = np.nan
    return df_base

def infer_uf_from_sindicato(s: str) -> Optional[str]:
    t = str(s).upper().strip()
    for uf in UF_LIST:
        if f" {uf} " in f" {t} " or t.startswith(uf+" ") or t.startswith("SINDPD "+uf) or f"- {uf} " in t:
            return uf
    return None

def prorate_by_admission(base_days: int, adm_dt: Optional[pd.Timestamp]) -> int:
    all_days = pd.bdate_range(PERIOD_START, PERIOD_END, freq="C")
    total_bdays = len(all_days)
    if pd.isna(adm_dt):
        return base_days
    if adm_dt > PERIOD_END:
        return 0
    start = max(adm_dt, PERIOD_START)
    bdays = pd.bdate_range(start, PERIOD_END, freq="C")
    return min(base_days, int(round(base_days * (len(bdays)/total_bdays))))

def compute_layout(ativos, deslig, adm, afast, aprendiz, estagio,
                   diasuteis, sind_valor) -> pd.DataFrame:
    # normalização
    for df in [ativos, deslig, adm, afast, aprendiz, estagio]:
        if df is not None:
            normalize_matricula(df)

    excl = build_exclusion_set(deslig, afast, aprendiz, estagio)

    base = ativos.copy()
    base = exclude_by_cargo(base)
    base = base.loc[~base["MATRICULA"].isin(excl)].copy()

    # Dias úteis por sindicato
    base = map_dias_uteis(base, diasuteis)
    # Admissão
    if adm is not None and {"MATRICULA","ADMISSÃO"}.issubset(adm.columns):
        adm2 = adm[["MATRICULA","ADMISSÃO"]].copy()
        adm2["ADMISSÃO"] = pd.to_datetime(adm2["ADMISSÃO"], errors="coerce", dayfirst=True)
        base = base.merge(adm2, on="MATRICULA", how="left")
    else:
        base["ADMISSÃO"] = pd.NaT

    # Prorrateio
    total_bdays = len(pd.bdate_range(PERIOD_START, PERIOD_END, freq="C"))
    base["DIAS_UTEIS"] = base["DIAS_UTEIS"].fillna(total_bdays).astype(int)
    base["DIAS_COMPRAR"] = base.apply(lambda r: prorate_by_admission(r["DIAS_UTEIS"], r["ADMISSÃO"]), axis=1)

    # UF e valor
    base["UF_INFERIDA"] = base.get("SINDICATO","").apply(infer_uf_from_sindicato)
    vr_dia = 0.0
    if sind_valor is not None and {"ESTADO","VALOR"}.issubset(sind_valor.columns):
        sv = sind_valor.rename(columns={"ESTADO":"UF","VALOR":"VR_DIA"}).copy()
        sv["UF"] = sv["UF"].astype(str).upper().str.strip()
        sv["VR_DIA"] = pd.to_numeric(sv["VR_DIA"], errors="coerce")
        vr_dia = sv["VR_DIA"].median()
        base = base.merge(sv, left_on="UF_INFERIDA", right_on="UF", how="left")
    else:
        base["VR_DIA"] = np.nan

    base["VR_DIA"] = base["VR_DIA"].fillna(vr_dia)
    base["VR_TOTAL"] = base["DIAS_COMPRAR"].astype(int) * base["VR_DIA"].astype(float)

    # colunas de saída
    for c in ["EMPRESA","TITULO DO CARGO","SINDICATO"]:
        if c not in base.columns:
            base[c] = np.nan
    out_cols = ["MATRICULA","EMPRESA","TITULO DO CARGO","SINDICATO","UF_INFERIDA",
                "DIAS_UTEIS","ADMISSÃO","DIAS_COMPRAR","VR_DIA","VR_TOTAL"]
    return base[out_cols].sort_values(["EMPRESA","SINDICATO","MATRICULA"]).reset_index(drop=True)

def validate(df: pd.DataFrame) -> list[str]:
    issues = []
    if df["DIAS_COMPRAR"].lt(0).any():
        issues.append("Há colaboradores com DIAS_COMPRAR < 0.")
    if df["VR_DIA"].isna().any():
        issues.append("Há colaboradores sem VR_DIA mapeado (UF não inferida ou valor ausente).")
    if df["DIAS_UTEIS"].isna().any():
        issues.append("Há colaboradores sem DIAS_UTEIS do sindicato.")
    return issues
