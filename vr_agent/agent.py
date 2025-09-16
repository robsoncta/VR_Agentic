### # vr_agent/agent.py
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from google.adk.agents import Agent
from .io_utils import load_first_sheet, save_layout
from .rules import compute_layout, validate   # ✅ importa do rules.py

load_dotenv()

# Configuração básica de logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )


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
            logger.warning(f"⚠️ Nenhum arquivo encontrado para base {name}")
            return None
        path = base_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Arquivo esperado não encontrado: {path}")
        logger.info(f"📂 Carregando base: {path.name}")
        return load_first_sheet(path)

    bases = {
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
    logger.info("✅ Todas as bases foram carregadas.")
    return bases


def gerar_compra_vr(base_dir: str, saida_arquivo: str, arquivos: dict) -> dict:
    """Gera layout VR/VA e salva em Excel."""
    logger.info("🚀 Iniciando gerar_compra_vr")

    bases = load_bases(base_dir, arquivos)

    if bases["ativos"] is None:
        logger.error("❌ Base ATIVOS.xlsx não carregada.")
        raise ValueError("A base ATIVOS.xlsx não foi carregada.")

    # ✅ chama regras do rules.py
    logger.info("⚙️ Executando compute_layout...")
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
    logger.info(f"📊 Layout consolidado com {len(layout)} registros.")

    # ✅ roda validação
    logger.info("🔎 Rodando validação do layout...")
    issues = validate(layout)
    if issues:
        logger.warning(f"⚠️ Validação encontrou problemas: {issues}")
    else:
        logger.info("✅ Validação concluída sem problemas.")

    # Salva saída
    base_dir = Path(base_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = save_layout(layout, base_dir / saida_arquivo)
    logger.info(f"💾 Layout salvo em: {path}")

    return {
        "status": "ok",
        "arquivo": str(path),
        "avisos": issues,
        "linhas": len(layout),
    }


def inspecionar_colunas(base_dir: str, arquivo: str) -> dict:
    """Inspeciona colunas e amostra de um arquivo Excel."""
    logger.info(f"🔍 Inspecionando colunas do arquivo: {arquivo}")
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
    instruction=( """   
    Você é o **Vr_Agent**, especialista em consolidação e cálculo de benefícios de Vale Refeição (VR).  

## Objetivo
Consolidar todas as bases fornecidas em um único arquivo **consolidado.csv**, aplicando corretamente as regras de negócio.  

## Fontes de Dados (pasta ./data)
- ATIVOS.xlsx  
- DESLIGADOS.xlsx  
- Base dias uteis.xlsx  
- Base sindicato x valor.xlsx  
- ADMISSÃO ABRIL.xlsx  
- AFASTAMENTOS.xlsx  
- APRENDIZ.xlsx  
- FÉRIAS.xlsx  
- EXTERIOR.xlsx  
- ESTÁGIO.xlsx  

---

## Regras de Consolidação

### 1. ATIVOS.xlsx  
- Base principal dos funcionários ativos.  
- **Chave primária**: `MATRICULA`.  
- Excluir sempre cargos com `TITULO DO CARGO` = *Diretores, Estagiários ou Aprendizes*.  
- Na coluna `DESC. SITUACAO`, considerar apenas registros = `"Trabalhando"`.  

### 2. FÉRIAS.xlsx  
- Adicionar ao consolidado a coluna `DIAS_DE_FERIAS` para os funcionários da base ATIVOS.  

### 3. Base dias uteis.xlsx  
- Contém a quantidade de dias úteis por sindicato.  
- Relacionar com a tabela ATIVOS pela coluna `Sindicato`.  

### 4. Base sindicato x valor.xlsx  
- Define o valor do VR por sindicato/estado.  
- Relacionar sindicato do funcionário com o valor correspondente:  
  - SITEPD PR → Paraná  
  - SINDPD RJ → Rio de Janeiro  
  - SINDPD SP → São Paulo  
  - SINDPPD RS → Rio Grande do Sul  
- Incluir essa informação no consolidado (`VR_VALOR`).  

### 5. DESLIGADOS.xlsx  
- Aplicar regras de exclusão e cálculo proporcional:  
  - Se `COMUNICADO DE DESLIGAMENTO = OK` **e** `DATA DEMISSÃO ≤ 15/05/2025`: excluir o funcionário.  
  - Se `DATA DEMISSÃO > 15/05/2025`: calcular proporcionalmente os dias úteis de VR até a data de demissão.  

### 6. EXTERIOR.xlsx  
- Funcionários fora do país não recebem VR.  
- Excluir suas `MATRICULAS` da base ATIVOS.  

### 7. ADMISSÃO ABRIL.xlsx  
- Funcionários admitidos em abril devem ser incluídos na base ATIVOS.  
- Calcular dias úteis proporcionalmente a partir da coluna `Admissao`.  
- Substituir a informação de "Base de dias úteis" pelo cálculo proporcional.  

### 8. AFASTAMENTOS.xlsx  
- Funcionários afastados devem ser removidos da base ATIVOS.  

### 9. APRENDIZ.xlsx  
- Remover aprendizes da base ATIVOS.  

---

## Saída Esperada
- Gerar um único arquivo `consolidado.csv`.  
- Salvar no diretório `./data/output`.  
- Cada linha deve representar um funcionário válido para o benefício de VR.  

### Colunas esperadas
- `MATRICULA`  
- `NOME`  
- `TITULO DO CARGO`  
- `SINDICATO`  
- `DIAS_UTEIS`  
- `DIAS_DE_FERIAS`  
- `VR_VALOR`  
- `VR_CALCULADO`  
- `DATA_ADMISSAO`  
- `DATA_DEMISSAO` *(se aplicável)*  

### Regra de cálculo  
- `VR_CALCULADO = (Dias úteis considerados – Dias de Férias) × Valor Sindicato`  
- Ajustar proporcionalmente em casos de:  
  - Admissão em abril  
  - Demissão após 15/05/2025""" ),

    tools=[gerar_compra_vr, inspecionar_colunas],
)
