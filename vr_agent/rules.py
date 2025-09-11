import pandas as pd
from datetime import datetime


def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nomes de colunas."""
    if df is None:
        return None
    df.columns = (
        df.columns.str.strip()
        .str.upper()
        .str.replace("\xa0", "", regex=True)
    )
    return df

def sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Remove linhas totalmente nulas, converte NaN para 0 e remove caracteres invisíveis."""
    if df is None:
        return None

    df = df.dropna(how="all")  # remove linhas 100% vazias
    df = df.where(pd.notnull(df), 0)  # converte NaN → 0

    # Remove caracteres invisíveis de todas as colunas de texto
    for col in df.select_dtypes(include=["object", "string"]):
        df[col] = df[col].astype(str).str.replace(r"[\u200B\u200C\u200D\uFEFF]", "", regex=True)

    return df

def compute_layout(
    ativos: pd.DataFrame,
    deslig: pd.DataFrame = None,
    adm: pd.DataFrame = None,
    afast: pd.DataFrame = None,
    aprendiz: pd.DataFrame = None,
    estagio: pd.DataFrame = None,
    diasuteis: pd.DataFrame = None,
    sind_valor: pd.DataFrame = None,
    ferias: pd.DataFrame = None,
    exterior: pd.DataFrame = None,
) -> pd.DataFrame:
    """Aplica todas as regras de consolidação e retorna o layout final."""

    if ativos is None:
        raise ValueError("A base ATIVOS.xlsx contem None.")

    # ==============================
    # Normalização e sanitização
    # ==============================
    ativos = sanitize_df(normalize_cols(ativos))
    deslig = sanitize_df(normalize_cols(deslig)) if deslig is not None else None
    adm = sanitize_df(normalize_cols(adm)) if adm is not None else None
    afast = sanitize_df(normalize_cols(afast)) if afast is not None else None
    aprendiz = sanitize_df(normalize_cols(aprendiz)) if aprendiz is not None else None
    estagio = sanitize_df(normalize_cols(estagio)) if estagio is not None else None
    diasuteis = sanitize_df(normalize_cols(diasuteis)) if diasuteis is not None else None
    sind_valor = sanitize_df(normalize_cols(sind_valor)) if sind_valor is not None else None
    ferias = sanitize_df(normalize_cols(ferias)) if ferias is not None else None
    exterior = sanitize_df(normalize_cols(exterior)) if exterior is not None else None

    df = ativos.copy()

    # Sindicato em maiúsculo
    if "SINDICATO" in df.columns:
        df["SINDICATO"] = df["SINDICATO"].str.upper().str.strip()

    # Estado em maiúsculo
    if sind_valor is not None and "ESTADO" in sind_valor.columns:
        sind_valor["ESTADO"] = sind_valor["ESTADO"].str.upper().str.strip()

    # ==========================================================
    # 1. Filtrar apenas funcionários ativos
    # ==========================================================
    if "TITULO DO CARGO" in df.columns:
        df = df[
            ~df["TITULO DO CARGO"].str.contains(
                "Diretor|Estagiario|Estagiário|Aprendiz", case=False, na=False
            )
        ]
    if "DESC. SITUACAO" in df.columns:
        df = df[df["DESC. SITUACAO"].str.contains("trabalhando", case=False, na=False)]

    # ==========================================================
    # 2. Remover aprendizes
    # ==========================================================
    if aprendiz is not None and "MATRICULA" in aprendiz.columns:
        df = df[~df["MATRICULA"].isin(aprendiz["MATRICULA"])]

    # ==========================================================
    # 3. Remover afastados
    # ==========================================================
    if afast is not None and "MATRICULA" in afast.columns:
        df = df[~df["MATRICULA"].isin(afast["MATRICULA"])]

    # ==========================================================
    # 4. Remover funcionários no exterior
    # ==========================================================
    if exterior is not None and "MATRICULA" in exterior.columns:
        df = df[~df["MATRICULA"].isin(exterior["MATRICULA"])]

    # ==========================================================
    # 5. Adicionar dias de férias
    # ==========================================================
    if ferias is not None and "MATRICULA" in ferias.columns:
        df = df.merge(
            ferias[["MATRICULA", "DIAS DE FÉRIAS"]],
            on="MATRICULA",
            how="left",
        )
    else:
        df["DIAS DE FÉRIAS"] = 0

    # ==========================================================
    # 6. Adicionar base de dias úteis por sindicato
    # ==========================================================
    if diasuteis is not None:
        diasuteis.columns = diasuteis.columns.str.upper().str.strip()
        if "SINDICATO" not in diasuteis.columns:
            diasuteis = diasuteis.rename(
                columns={
                    "BASE DIAS UTEIS DE 15/04 A 15/05": "SINDICATO",
                    "UNNAMED: 1": "DIAS_UTEIS",
                }
            )
            diasuteis = diasuteis.drop(0, errors="ignore")

        diasuteis["SINDICATO"] = diasuteis["SINDICATO"].str.upper().str.strip()
        df = df.merge(diasuteis, on="SINDICATO", how="left")

    # ==========================================================
    # 7. Adicionar valor de VR por sindicato
    # ==========================================================
    if sind_valor is not None:
        map_estado_sind = {
            "SÃO PAULO": "SINDPD SP - SIND.TRAB.EM PROC DADOS E EMPR.EMP...",
            "RIO GRANDE DO SUL": "SINDPPD RS - SINDICATO DOS TRAB. EM PROC. DE D...",
            "PARANÁ": "SITEPD PR - SIND DOS TRAB EM EMPR PRIVADAS DE ...",
            "RIO DE JANEIRO": "SINDPD RJ - SINDICATO PROFISSIONAIS DE PROC DA...",
        }

        sind_valor["SINDICATO"] = sind_valor["ESTADO"].map(map_estado_sind)
        df = df.merge(sind_valor[["SINDICATO", "VALOR"]], on="SINDICATO", how="left")

    # ==========================================================
    # 8. Regras de desligados
    # ==========================================================
    if deslig is not None and {"MATRICULA", "COMUNICADO DE DESLIGAMENTO", "DATA DEMISSÃO"}.issubset(deslig.columns):
        deslig["DATA DEMISSÃO"] = pd.to_datetime(deslig["DATA DEMISSÃO"], errors="coerce")
        cutoff = datetime(2025, 5, 15)

        desligados_antes = deslig[
            (deslig["COMUNICADO DE DESLIGAMENTO"].str.upper() == "OK")
            & (deslig["DATA DEMISSÃO"] <= cutoff)
        ]["MATRICULA"]
        df = df[~df["MATRICULA"].isin(desligados_antes)]

        desligados_depois = deslig[
            (deslig["COMUNICADO DE DESLIGAMENTO"].str.upper() == "OK")
            & (deslig["DATA DEMISSÃO"] > cutoff)
        ]
        for _, row in desligados_depois.iterrows():
            mat = row["MATRICULA"]
            data_dem = row["DATA DEMISSÃO"]
            if mat in df["MATRICULA"].values and "DIAS_UTEIS" in df.columns:
                dias_total = df.loc[df["MATRICULA"] == mat, "DIAS_UTEIS"].values[0]
                dias_trabalhados = max((data_dem - cutoff).days, 0)
                df.loc[df["MATRICULA"] == mat, "DIAS_UTEIS"] = dias_trabalhados

    # ==========================================================
    # 9. Admissões em abril (proporcional)
    # ==========================================================
    if adm is not None and {"MATRICULA", "ADMISSAO"}.issubset(adm.columns):
        adm["ADMISSAO"] = pd.to_datetime(adm["ADMISSAO"], errors="coerce")
        for _, row in adm.iterrows():
            mat = row["MATRICULA"]
            adm_data = row["ADMISSAO"]
            if mat in df["MATRICULA"].values and "DIAS_UTEIS" in df.columns:
                dias_total = df.loc[df["MATRICULA"] == mat, "DIAS_UTEIS"].values[0]
                if pd.notna(adm_data):
                    dias_proporcionais = max(dias_total - (adm_data.day - 1), 0)
                    df.loc[df["MATRICULA"] == mat, "DIAS_UTEIS"] = dias_proporcionais

    # ==========================================================
    # 10. Calcular coluna final de VALOR_VR
    # ==========================================================
    valor_col = next((c for c in ["VALOR", "VR_VALOR", "VALOR_SINDICATO", "Valor", "Valor_Sindicato"] if c in df.columns), None)

    if valor_col and "DIAS_UTEIS" in df.columns:
        df["VALOR_VR"] = (
            pd.to_numeric(df["DIAS_UTEIS"], errors="coerce").fillna(0)
            * pd.to_numeric(df[valor_col], errors="coerce").fillna(0)
        )
    else:
        df["VALOR_VR"] = 0

    # 🔎 Sanitiza para garantir que não sobra NaN/None no resultado
    df = sanitize_df(df)
    return df


def validate(df: pd.DataFrame) -> list:
    """Valida o layout final e retorna lista de avisos."""
    issues = []

    if "MATRICULA" not in df.columns:
        issues.append("Coluna MATRICULA ausente.")

    if df.empty:
        issues.append("Layout final está vazio.")

    if "DIAS_UTEIS" not in df.columns:
        issues.append("Coluna DIAS_UTEIS ausente no resultado final.")

    if "SINDICATO" not in df.columns:
        issues.append("Coluna SINDICATO ausente no resultado final.")

    if "VALOR_VR" not in df.columns:
        issues.append("Coluna VALOR_VR não foi gerada.")

    if df.isnull().any().any():
        null_cols = df.columns[df.isnull().any()].tolist()
        issues.append(f"Existem valores NaN/None nas colunas: {null_cols}")

    return issues
