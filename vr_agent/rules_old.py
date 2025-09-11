from datetime import datetime
from typing import Optional, Set
import numpy as np
import pandas as pd

UF_LIST = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG",
           "PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"]

PERIOD_START = pd.Timestamp(2025, 4, 15)
PERIOD_END   = pd.Timestamp(2025, 5, 15)


def normalize_matricula(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza a coluna MATRICULA: remove .0 final, strip e preserva NaN."""
    if df is None:
        return df
    if "MATRICULA" in df.columns:
        s = df["MATRICULA"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
        # transformar strings "nan" de volta para np.nan
        s = s.replace({"nan": np.nan, "None": np.nan})
        df = df.copy()
        df["MATRICULA"] = s
    return df


def _extract_matriculas_as_str(series: pd.Series) -> Set[str]:
    """Helper: recebe uma Series e retorna set de strings normalizadas (sem NaN)."""
    if series is None:
        return set()
    s = series.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    s = s.replace({"nan": np.nan, "None": np.nan})
    s = s.dropna()
    return set(s.astype(str))


def build_exclusion_set(deslig, afast, aprendiz, estagio) -> set:
    """Cria conjunto de matrículas a serem excluídas a partir de várias fontes."""
    excl = set()
    if deslig is not None and "MATRICULA" in deslig.columns:
        excl.update(_extract_matriculas_as_str(deslig["MATRICULA"]))
    if aprendiz is not None and "MATRICULA" in aprendiz.columns:
        excl.update(_extract_matriculas_as_str(aprendiz["MATRICULA"]))
    if estagio is not None and "MATRICULA" in estagio.columns:
        excl.update(_extract_matriculas_as_str(estagio["MATRICULA"]))
    if afast is not None and {"MATRICULA", "NA COMPRA?"}.issubset(afast.columns):
        # padroniza a coluna NA COMPRA?
        mask = afast["NA COMPRA?"].astype(str).str.upper().str.strip().isin(["N", "NAO", "NÃO", "NO"])
        excl.update(_extract_matriculas_as_str(afast.loc[mask, "MATRICULA"]))
    return excl


def exclude_by_cargo(df: pd.DataFrame) -> pd.DataFrame:
    """Remove cargos como DIRETOR, ESTAGI(ário) e APRENDIZ."""
    if "TITULO DO CARGO" in df.columns:
        cargo = df["TITULO DO CARGO"].astype(str).str.upper()
        bad = cargo.str.contains("DIRETOR") | cargo.str.contains("ESTAGI") | cargo.str.contains("APRENDIZ")
        return df.loc[~bad].copy()
    return df


def map_dias_uteis(df_base: pd.DataFrame, diasuteis: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Mapeia DIAS_UTEIS por sindicato. Se diasuteis for inválido, mantém NaN."""
    if diasuteis is None:
        df_base = df_base.copy()
        df_base["DIAS_UTEIS"] = np.nan
        return df_base

    # valida quantidade de colunas do arquivo diasuteis
    if diasuteis.shape[1] < 2:
        df_base = df_base.copy()
        df_base["DIAS_UTEIS"] = np.nan
        return df_base

    du = diasuteis.rename(columns={diasuteis.columns[0]: "SINDICATO_NOME",
                                   diasuteis.columns[1]: "DIAS_UTEIS"}).copy()
    du["SINDICATO_NOME"] = du["SINDICATO_NOME"].astype(str).str.upper().str.strip()
    du["DIAS_UTEIS"] = pd.to_numeric(du["DIAS_UTEIS"], errors="coerce")
    du = du[du["DIAS_UTEIS"].notna()].copy()
    du["DIAS_UTEIS"] = du["DIAS_UTEIS"].astype(int)

    df_base = df_base.copy()
    if "SINDICATO" in df_base.columns:
        df_base["SINDICATO_NOME"] = df_base["SINDICATO"].astype(str).str.upper().str.strip()
        df_base = df_base.merge(du, on="SINDICATO_NOME", how="left")
        # se não encontrar DIAS_UTEIS no merge, ficará NaN — ok
    else:
        df_base["DIAS_UTEIS"] = np.nan
    return df_base


def infer_uf_from_sindicato(s: str) -> Optional[str]:
    t = str(s).upper().strip()
    for uf in UF_LIST:
        # checagens mais robustas para capturar variações em strings
        if f" {uf} " in f" {t} " or t.startswith(uf + " ") or t.startswith("SINDPD " + uf) or f"- {uf} " in t:
            return uf
    return None


def prorate_by_admission(base_days: int, adm_dt: Optional[pd.Timestamp]) -> int:
    """Prorrateia os dias úteis considerando a data de admissão dentro do periodo."""
    all_days = pd.bdate_range(PERIOD_START, PERIOD_END, freq="C")
    total_bdays = len(all_days)
    # se adm_dt for NaT ou None, retorna base_days
    if pd.isna(adm_dt):
        return int(base_days)
    # tentar converter caso venha string
    if not isinstance(adm_dt, pd.Timestamp):
        try:
            adm_dt = pd.to_datetime(adm_dt, errors="coerce", dayfirst=True)
        except Exception:
            return int(base_days)
    if pd.isna(adm_dt):
        return int(base_days)
    # se admissão após periodo, não ganha nada
    if adm_dt > PERIOD_END:
        return 0
    start = max(adm_dt, PERIOD_START)
    bdays = pd.bdate_range(start, PERIOD_END, freq="C")
    # evita divisão por zero por segurança (mas total_bdays não deve ser 0)
    if total_bdays <= 0:
        return int(base_days)
    prorated = int(round(base_days * (len(bdays) / total_bdays)))
    return min(base_days, prorated)


def compute_layout(ativos, deslig, adm, afast, aprendiz, estagio,
                   diasuteis, sind_valor) -> pd.DataFrame:
    """Fluxo principal para construir o layout de VR."""
    # normalização: reatribui os dfs normalizados
    ativos = normalize_matricula(ativos) if ativos is not None else None
    deslig = normalize_matricula(deslig) if deslig is not None else None
    adm = normalize_matricula(adm) if adm is not None else None
    afast = normalize_matricula(afast) if afast is not None else None
    aprendiz = normalize_matricula(aprendiz) if aprendiz is not None else None
    estagio = normalize_matricula(estagio) if estagio is not None else None

    excl = build_exclusion_set(deslig, afast, aprendiz, estagio)

    if ativos is None:
        # nada para processar
        return pd.DataFrame(columns=["MATRICULA","EMPRESA","TITULO DO CARGO","SINDICATO","UF_INFERIDA",
                                     "DIAS_UTEIS","ADMISSÃO","DIAS_COMPRAR","VR_DIA","VR_TOTAL"])

    base = ativos.copy()
    base = exclude_by_cargo(base)
    # garantir que MATRICULA está string e strip antes de isin
    if "MATRICULA" in base.columns:
        base["MATRICULA"] = base["MATRICULA"].astype(str).str.strip().replace({"nan": np.nan})
        base = base.loc[~base["MATRICULA"].isin(excl)].copy()

    # Dias úteis por sindicato
    base = map_dias_uteis(base, diasuteis)

    # Admissão: merge seguro (padroniza MATRICULA como string)
    if adm is not None and {"MATRICULA", "ADMISSÃO"}.issubset(adm.columns):
        adm2 = adm[["MATRICULA", "ADMISSÃO"]].copy()
        adm2["MATRICULA"] = adm2["MATRICULA"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip().replace({"nan": np.nan})
        adm2["ADMISSÃO"] = pd.to_datetime(adm2["ADMISSÃO"], errors="coerce", dayfirst=True)
        base = base.merge(adm2, on="MATRICULA", how="left")
    else:
        base["ADMISSÃO"] = pd.NaT

    # Prorrateio
    total_bdays = len(pd.bdate_range(PERIOD_START, PERIOD_END, freq="C"))
    base["DIAS_UTEIS"] = base["DIAS_UTEIS"].fillna(total_bdays).astype(int)
    base["DIAS_COMPRAR"] = base.apply(lambda r: prorate_by_admission(int(r["DIAS_UTEIS"]), r.get("ADMISSÃO", pd.NaT)), axis=1)

    # UF inferida
    if "SINDICATO" in base.columns:
        base["UF_INFERIDA"] = base["SINDICATO"].astype(str).apply(infer_uf_from_sindicato)
    else:
        base["UF_INFERIDA"] = None

    # VR por estado (sind_valor)
    vr_dia_fallback = 0.0
    if sind_valor is not None and {"ESTADO", "VALOR"}.issubset(sind_valor.columns):
        sv = sind_valor.rename(columns={"ESTADO": "UF", "VALOR": "VR_DIA"}).copy()
        sv["UF"] = sv["UF"].astype(str).str.upper().str.strip()
        sv["VR_DIA"] = pd.to_numeric(sv["VR_DIA"], errors="coerce")
        # pick a median only among non-null
        if sv["VR_DIA"].dropna().shape[0] > 0:
            vr_dia_fallback = sv["VR_DIA"].median()
        else:
            vr_dia_fallback = 0.0
        # merge e depois dropar a coluna UF redundante
        base = base.merge(sv, left_on="UF_INFERIDA", right_on="UF", how="left")
        if "UF" in base.columns:
            # manter UF_INFERIDA e remover UF criado pelo merge
            base = base.drop(columns=["UF"])
    else:
        base["VR_DIA"] = np.nan

    # preencher VR_DIA com fallback
    base["VR_DIA"] = base["VR_DIA"].fillna(vr_dia_fallback)
    # garantir tipos
    base["VR_TOTAL"] = base["DIAS_COMPRAR"].astype(int) * base["VR_DIA"].astype(float)

    # colunas de saída — garante presença
    for c in ["EMPRESA", "TITULO DO CARGO", "SINDICATO"]:
        if c not in base.columns:
            base[c] = np.nan

    out_cols = ["MATRICULA", "EMPRESA", "TITULO DO CARGO", "SINDICATO", "UF_INFERIDA",
                "DIAS_UTEIS", "ADMISSÃO", "DIAS_COMPRAR", "VR_DIA", "VR_TOTAL"]
    # seleciona apenas colunas existentes no DataFrame resultante; completa faltantes com NaN
    for c in out_cols:
        if c not in base.columns:
            base[c] = np.nan

    return base[out_cols].sort_values(["EMPRESA", "SINDICATO", "MATRICULA"]).reset_index(drop=True)


def validate(df: pd.DataFrame) -> list[str]:
    issues = []
    if "DIAS_COMPRAR" in df.columns and df["DIAS_COMPRAR"].lt(0).any():
        issues.append("Há colaboradores com DIAS_COMPRAR < 0.")
    if "VR_DIA" in df.columns and df["VR_DIA"].isna().any():
        issues.append("Há colaboradores sem VR_DIA mapeado (UF não inferida ou valor ausente).")
    if "DIAS_UTEIS" in df.columns and df["DIAS_UTEIS"].isna().any():
        issues.append("Há colaboradores sem DIAS_UTEIS do sindicato.")
    return issues
