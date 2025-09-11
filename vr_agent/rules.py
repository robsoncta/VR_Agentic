import pandas as pd
from datetime import datetime


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
        raise ValueError("A base ATIVOS.xlsx não foi carregada.")

    df = ativos.copy()

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
    if diasuteis is not None and "Sindicato" in diasuteis.columns:
        df = df.merge(diasuteis, on="Sindicato", how="left")

    # ==========================================================
    # 7. Adicionar valor de VR por sindicato
    # ==========================================================
    if sind_valor is not None and "Sindicato" in sind_valor.columns:
        df = df.merge(sind_valor, on="Sindicato", how="left")

    # ==========================================================
    # 8. Regras de desligados
    # ==========================================================
    if deslig is not None and {"MATRICULA", "COMUNICADO DE DESLIGAMENTO", "DATA DEMISSÃO"}.issubset(deslig.columns):
        deslig["DATA DEMISSÃO"] = pd.to_datetime(deslig["DATA DEMISSÃO"], errors="coerce")
        cutoff = datetime(2025, 5, 15)

        # Marca quem sai antes do corte
        desligados_antes = deslig[
            (deslig["COMUNICADO DE DESLIGAMENTO"].str.upper() == "OK")
            & (deslig["DATA DEMISSÃO"] <= cutoff)
        ]["MATRICULA"]

        df = df[~df["MATRICULA"].isin(desligados_antes)]

        # Quem sai depois do corte → cálculo proporcional
        desligados_depois = deslig[
            (deslig["COMUNICADO DE DESLIGAMENTO"].str.upper() == "OK")
            & (deslig["DATA DEMISSÃO"] > cutoff)
        ]
        for _, row in desligados_depois.iterrows():
            mat = row["MATRICULA"]
            data_dem = row["DATA DEMISSÃO"]
            if mat in df["MATRICULA"].values and "Dias_Uteis" in df.columns:
                dias_total = df.loc[df["MATRICULA"] == mat, "Dias_Uteis"].values[0]
                dias_trabalhados = max((data_dem - cutoff).days, 0)
                df.loc[df["MATRICULA"] == mat, "Dias_Uteis"] = dias_trabalhados

    # ==========================================================
    # 9. Admissões em abril (calcular proporcional)
    # ==========================================================
    if adm is not None and {"MATRICULA", "Admissao"}.issubset(adm.columns):
        adm["Admissao"] = pd.to_datetime(adm["Admissao"], errors="coerce")
        for _, row in adm.iterrows():
            mat = row["MATRICULA"]
            adm_data = row["Admissao"]
            if mat in df["MATRICULA"].values and "Dias_Uteis" in df.columns:
                dias_total = df.loc[df["MATRICULA"] == mat, "Dias_Uteis"].values[0]
                if pd.notna(adm_data):
                    dias_proporcionais = max(dias_total - (adm_data.day - 1), 0)
                    df.loc[df["MATRICULA"] == mat, "Dias_Uteis"] = dias_proporcionais

    # ==========================================================
    # 10. Calcular coluna final de Valor_VR
    # ==========================================================
    if "Dias_Uteis" in df.columns:
        valor_col = None
        for col in ["Valor", "VR_Valor", "VALOR", "Valor_Sindicato"]:
            if col in df.columns:
                valor_col = col
                break
        if valor_col:
            df["Valor_VR"] = df["Dias_Uteis"].fillna(0) * df[valor_col].fillna(0)
        else:
            df["Valor_VR"] = 0
    else:
        df["Valor_VR"] = 0

    return df


def validate(df: pd.DataFrame) -> list:
    """Valida o layout final e retorna lista de avisos."""
    issues = []

    if "MATRICULA" not in df.columns:
        issues.append("Coluna MATRICULA ausente.")

    if df.empty:
        issues.append("Layout final está vazio.")

    if "Dias_Uteis" not in df.columns:
        issues.append("Coluna Dias_Uteis ausente no resultado final.")

    if "Sindicato" not in df.columns:
        issues.append("Coluna Sindicato ausente no resultado final.")

    if "Valor_VR" not in df.columns:
        issues.append("Coluna Valor_VR não foi gerada.")

    return issues