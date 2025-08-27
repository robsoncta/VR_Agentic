import os
from pathlib import Path
from dotenv import load_dotenv
from google.adk.agents import Agent
from .io_utils import load_first_sheet, save_layout
from .rules import compute_layout, validate

load_dotenv()

def load_bases(base_dir: str, arquivos: dict) -> dict:
    """Carrega planilhas a partir do diretório base (relativo ou seguro)."""
    
    # força base_dir como Path relativo seguro
    base_dir = Path(base_dir).resolve()  # caminho absoluto do projeto
    base_dir.mkdir(parents=True, exist_ok=True)  # garante que a pasta exista

    def maybe(name):
        filename = arquivos.get(name, "")
        if not filename:
            return None
        path = base_dir / filename
        return load_first_sheet(path)

    return {
        "ativos": maybe("ATIVOS"),
        "deslig": maybe("DESLIGADOS"),
        "adm": maybe("ADMISSAO"),
        "afast": maybe("AFASTAMENTOS"),
        "aprendiz": maybe("APRENDIZ"),
        "estagio": maybe("ESTAGIO"),
        "diasuteis": maybe("BASE_DIAS_UTEIS"),
        "sind_valor": maybe("BASE_SINDICATO_VALOR"),
        "ferias": maybe("FERIAS"),
        "exterior": maybe("EXTERIOR"),
    }

def gerar_compra_vr(base_dir: str, saida_arquivo: str, arquivos: dict) -> dict:
    """Gera layout VR/VA e salva em Excel."""
    bases = load_bases(base_dir, arquivos)
    layout = compute_layout(
        ativos=bases["ativos"],
        deslig=bases["deslig"],
        adm=bases["adm"],
        afast=bases["afast"],
        aprendiz=bases["aprendiz"],
        estagio=bases["estagio"],
        diasuteis=bases["diasuteis"],
        sind_valor=bases["sind_valor"]
    )
    issues = validate(layout)

    # Salva saída em caminho seguro
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)  # garante que a pasta exista
    path = save_layout(layout, base_dir / saida_arquivo)

    return {"status": "ok", "arquivo": str(path), "avisos": issues, "linhas": len(layout)}

def inspecionar_colunas(base_dir: str, arquivo: str) -> dict:
    df = load_first_sheet(Path(base_dir) / arquivo)
    return {"arquivo": arquivo, "colunas": list(df.columns), "amostra": df.head(5).to_dict(orient="records")}

# Agente raiz
root_agent = Agent(
    name="vr_compra_agent",
    model="gemini-2.5-pro",
    description="Agente que consolida bases e gera layout de compra VR/VA.",
    instruction=(
        """
        Você é o Vr_Agent, responsável por consolidar e calcular corretamente a planilha de compra de Vale Refeição (VR).  
        Leia e processe os arquivos da pasta ./data (documentação) e siga as regras de cálculo.
        """
    ),
    tools=[gerar_compra_vr, inspecionar_colunas],
)
