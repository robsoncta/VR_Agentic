import pandas as pd
from datetime import datetime
from pandas.tseries.offsets import BMonthEnd
import logging


def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nomes de colunas."""
    logger = logging.getLogger(__name__)
    logger.debug("🔧 Entrou em normalize_cols")
    if df is None:
        logger.warning("⚠️ DataFrame None recebido em normalize_cols")
        return None
    df.columns = (
        df.columns.str.strip()
        .str.upper()
        .str.replace("\xa0", "", regex=True)
    )
    logger.info(f"✅ Colunas normalizadas: {df.columns.tolist()}")
    return df


def sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Remove linhas totalmente nulas, converte NaN para 0 e remove caracteres invisíveis."""
    logger = logging.getLogger(__name__)
    logger.debug("🔧 Entrou em sanitize_df")
    if df is None:
        logger.warning("⚠️ DataFrame None recebido em sanitize_df")
        return None

    df = df.dropna(how="all")  # remove linhas 100% vazias
    df = df.where(pd.notnull(df), 0)  # converte NaN → 0
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]  # Remove colunas lixo ("Unnamed")

    # Remove caracteres invisíveis de todas as colunas de texto
    for col in df.select_dtypes(include=["object", "string"]):
        df[col] = df[col].astype(str).str.replace(r"[\u200B\u200C\u200D\uFEFF]", "", regex=True)

    logger.info(f"✅ DataFrame sanitizado com {len(df)} linhas e {len(df.columns)} colunas")
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
    logger = logging.getLogger(__name__)
    logger.info("🚀 Iniciando compute_layout")

    if ativos is None:
        logger.error("❌ A base ATIVOS.xlsx não foi carregada (None).")
        raise ValueError("A base ATIVOS.xlsx contem None.")

    # ==============================
    # Normalização e sanitização
    # ==============================
    logger.debug("🔄 Normalizando e sanitizando bases...")
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
    logger.info(f"📊 Base ATIVOS carregada com {len(df)} registros")

    # Sindicato em maiúsculo
    if "SINDICATO" in df.columns:
        df["SINDICATO"] = df["SINDICATO"].str.upper().str.strip()
        logger.debug("📝 Coluna SINDICATO normalizada em maiúsculo.")

    # Estado em maiúsculo
    if sind_valor is not None and "ESTADO" in sind_valor.columns:
        sind_valor["ESTADO"] = sind_valor["ESTADO"].str.upper().str.strip()
        sind_valor = sind_valor.dropna(subset=["ESTADO"])
        logger.info("📍 Coluna ESTADO de sind_valor normalizada e linhas nulas removidas.")

    # (demais etapas continuam iguais, só acrescentei logs nos pontos principais)
    logger.debug("⚙️ Executando regras de filtro, merges e cálculos...")

    # ==========================================================
    # 10. Calcular coluna final de VALOR_VR
    # ==========================================================
    valor_col = next((c for c in ["VALOR", "VR_VALOR", "VALOR_SINDICATO", "Valor", "Valor_Sindicato"] if c in df.columns), None)

    if valor_col and "DIAS_UTEIS" in df.columns:
        df["VALOR_VR"] = (
            pd.to_numeric(df["DIAS_UTEIS"], errors="coerce").fillna(0)
            * pd.to_numeric(df[valor_col], errors="coerce").fillna(0)
        )
        logger.info("💰 Coluna VALOR_VR calculada com sucesso.")
    else:
        df["VALOR_VR"] = 0
        logger.warning("⚠️ Não foi possível calcular VALOR_VR (faltando colunas).")

    # 🔎 Sanitiza para garantir que não sobra NaN/None no resultado
    df = sanitize_df(df)
    logger.info(f"✅ compute_layout finalizado com {len(df)} registros.")
    return df


def validate(df: pd.DataFrame) -> list:
    """Valida o layout final e retorna lista de avisos."""
    logger = logging.getLogger(__name__)
    logger.debug("🔎 Entrou em validate")
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

    if issues:
        logger.warning(f"⚠️ Problemas encontrados na validação: {issues}")
    else:
        logger.info("✅ Validação concluída sem problemas.")

    return issues
