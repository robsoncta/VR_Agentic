# vr_agent/agent.py
import os
from pathlib import Path
from dotenv import load_dotenv
from google.adk.agents import Agent
from .io_utils import load_first_sheet, save_layout
from .rules import compute_layout, validate   # ✅ importa do rules.py

load_dotenv()


def load_bases(base_dir: str, arquivos: dict) -> dict:
    """Carrega planilhas a partir do diretório ./data"""
    base_dir = Path(base_dir).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    def maybe(name):
        filename = (
            arquivos.get(name)
            or arquivos.get(f"{name}.xlsx")
            or arquivos.get(f"{name}.xls")
        )
        if not filename:
            return None
        path = base_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Arquivo esperado não encontrado: {path}")
        return load_first_sheet(path)

    return {
        "ativos": maybe("ATIVOS"),
        "deslig": maybe("DESLIGADOS"),
        "adm": maybe("ADMISSÃO ABRIL"),
        "afast": maybe("AFASTAMENTOS"),
        "aprendiz": maybe("APRENDIZ"),
        "estagio": maybe("ESTÁGIO"),
        "diasuteis": maybe("BASE_DIAS_UTEIS"),
        "sind_valor": maybe("BASE_SINDICATO_VALOR"),
        "ferias": maybe("FÉRIAS"),
        "exterior": maybe("EXTERIOR"),
    }


def gerar_compra_vr(base_dir: str, saida_arquivo: str, arquivos: dict) -> dict:
    """Gera layout VR/VA e salva em Excel."""
    bases = load_bases(base_dir, arquivos)

    if bases["ativos"] is None:
        raise ValueError("A base ATIVOS.xlsx não foi carregada.")

    # ✅ chama regras do rules.py
    layout = compute_layout(
        ativos=bases["ativos"],
        deslig=bases["deslig"],
        adm=bases["adm"],
        afast=bases["afast"],
        aprendiz=bases["aprendiz"],
        estagio=bases["estagio"],
        diasuteis=bases["diasuteis"],
        sind_valor=bases["sind_valor"],
        ferias=bases["ferias"],
        exterior=bases["exterior"],
    )

    # ✅ roda validação
    issues = validate(layout)

    # Salva saída
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = save_layout(layout, base_dir / saida_arquivo)

    return {
        "status": "ok",
        "arquivo": str(path),
        "avisos": issues,
        "linhas": len(layout),
    }


def inspecionar_colunas(base_dir: str, arquivo: str) -> dict:
    """Inspeciona colunas e amostra de um arquivo Excel."""
    df = load_first_sheet(Path(base_dir) / arquivo)
    return {
        "arquivo": arquivo,
        "colunas": list(df.columns),
        "amostra": df.head(5).to_dict(orient="records"),
    }


# Agente raiz
root_agent = Agent(
    name="vr_compra_agent",
    model="gemini-2.5-pro",
    description="Agente que consolida bases e gera layout de compra VR/VA.",
    instruction=(
        """
        Você é o Vr_Agent, especialista em consolidação e cálculo de benefícios de Vale Refeição (VR). Seu objetivo consolidar todas as bases fornecidas em um único arquivo consolidado.csv.
 Sua tarefa é ler e processar os arquivos da pasta ./data 
        ATIVOS.xlsx
        DESLIGADOS.xlsx
        Base dias uteis.xlsx
        Base sindicato x valor.xlsx
        ADMISSÃO ABRIL.xlsx
        AFASTAMENTOS.xlsx
        APRENDIZ.xlsx
        FÉRIAS.xlsx
        EXTERIOR.xlsx
        ESTÁGIO.xlsx

        Aplicando corretamente todas as regras abaixo:

### Bases e Regras de Consolidação
ATIVOS.xlsx
Base principal dos funcionários ativos.
Chave primária: MATRICULA.
Desconsiderar sempre cargos com TITULO DO CARGO = Diretores, Estagiários ou Aprendizes.
Na coluna DESC. SITUACAO, considerar apenas registros = "Trabalhando".


FÉRIAS.xlsx
Adicionar ao consolidado a coluna DIAS DE FÉRIAS para os funcionários da base ATIVOS.


Base dias uteis.xlsx
Traz a quantidade de dias úteis por sindicato.
Adicionar essa informação à tabela ATIVOS pela relação da coluna Sindicato.


Base sindicato x valor.xlsx
Define o valor do VR por sindicato/estado.
Relacionar o sindicato do funcionário com o valor correspondente:
SITEPD PR → Paraná
SINDPD RJ → Rio de Janeiro
SINDPD SP → São Paulo
SINDPPD RS → Rio Grande do Sul


Incluir essa coluna no consolidado.


DESLIGADOS.xlsx
Regras de exclusão e cálculo proporcional:
Se COMUNICADO DE DESLIGAMENTO = OK e DATA DEMISSÃO ≤ 15/05/2025, não considerar o funcionário.
Se DATA DEMISSÃO > 15/05/2025, calcular proporcionalmente os dias úteis de VR até a data de demissão.


EXTERIOR.xlsx
Funcionários fora do país não recebem VR.
Excluir suas MATRICULAS da base ATIVOS.


ADMISSÃO ABRIL.xlsx
Funcionários admitidos em abril devem ser incluídos na base ATIVOS.
Calcular dias úteis proporcionalmente a partir da coluna Admissao.
Substituir a informação de "Base de dias úteis" pelo cálculo proporcional.


AFASTAMENTOS.xlsx
Funcionários afastados devem ser removidos da base ATIVOS.


APRENDIZ.xlsx
Remover aprendizes da base ATIVOS.
### Saída esperada
Gerar um único arquivo consolidado.csv e Salvar diretorio ./data/output
Cada linha deve representar um funcionário válido para o benefício de VR.
Colunas esperadas:
 MATRICULA, NOME, TITULO DO CARGO, SINDICATO, DIAS_UTEIS, DIAS_DE_FERIAS, VR_VALOR, VR_CALCULADO, DATA_ADMISSAO, DATA_DEMISSAO (se aplicável)
O campo VR_CALCULADO deve ser o resultado: (Dias úteis considerados - Dias de Férias) × Valor Sindicato
Ajustado proporcionalmente nos casos de admissão em abril ou demissão após 15/05/2025.

        """
    ),
    tools=[gerar_compra_vr, inspecionar_colunas],
)
