import os
import pandas as pd
from typing import Optional
from dotenv import load_dotenv
from google.adk.agents import Agent  # ADK Python
from .io_utils import load_first_sheet, save_layout
from .rules import compute_layout, validate

load_dotenv()

def load_bases(
    base_dir: str,
    arquivos: dict
) -> dict:
    """Carrega as planilhas necessárias (primeira aba) a partir de caminhos."""
    def maybe(name): 
        path = os.path.join(base_dir, arquivos.get(name,""))
        return load_first_sheet(path) if arquivos.get(name) else None

    return {
        "ativos"     : maybe("ATIVOS"),
        "deslig"     : maybe("DESLIGADOS"),
        "adm"        : maybe("ADMISSAO"),
        "afast"      : maybe("AFASTAMENTOS"),
        "aprendiz"   : maybe("APRENDIZ"),
        "estagio"    : maybe("ESTAGIO"),
        "diasuteis"  : maybe("BASE_DIAS_UTEIS"),
        "sind_valor" : maybe("BASE_SINDICATO_VALOR"),
        "ferias"     : maybe("FERIAS"),
        "exterior"   : maybe("EXTERIOR"),
    }

def gerar_compra_vr(
    base_dir: str,
    saida_arquivo: str,
    arquivos: dict,
) -> dict:
    """Gera o layout de compra VR/VA e salva em Excel."""
    bases = load_bases(base_dir, arquivos)
    # TODO: quando FERIAS e EXTERIOR forem fornecidos, aplicar mais exclusões por MATRÍCULA
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
    path = save_layout(layout, os.path.join(base_dir, saida_arquivo))
    return {"status":"ok","arquivo":path,"avisos":issues, "linhas":len(layout)}

# Opcional: tool de “inspeção” de colunas para ajudar mapeamentos
def inspecionar_colunas(base_dir: str, arquivo: str) -> dict:
    df = load_first_sheet(os.path.join(base_dir, arquivo))
    return {"arquivo": arquivo, "colunas": list(df.columns), "amostra": df.head(5).to_dict(orient="records")}

# Agente raiz (pode rodar localmente ou no Dev UI do ADK)
root_agent = Agent(
    name="vr_compra_agent",
    model="gemini-2.5-pro",   # ajuste conforme preferência/limite
    description="Agente que consolida bases e gera o layout de compra de VR/VA.",
    instruction=(
        "Você é um agente especialista em benefícios. "
        "Quando solicitado, chame as ferramentas para inspecionar arquivos ou gerar o layout."
    ),
    tools=[gerar_compra_vr, inspecionar_colunas],
)
