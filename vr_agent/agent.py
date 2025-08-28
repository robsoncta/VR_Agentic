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
Sua tarefa é ler e processar os arquivos da pasta ./data:

- ATIVOS.xlsx
- FERIAS.xlsx
- DESLIGADOS.xlsx
- EXTERIOR.xlsx
- ADMISSÃO ABRIL.xlsx
- AFASTAMENTOS.xlsx
- APRENDIZ.xlsx
- Base-dias-uteis.xlsx
- Base-sindicato-x-valor.xlsx
- VR_MENSAL_05.2025.xlsx

### Objetivo:
Gerar uma **planilha final de compra de VR** no mesmo layout da aba “VR Mensal 05.2025”, contendo:
- Valor de VR a ser concedido por colaborador.  
- Valor de custo para a empresa (80%).  
- Valor de desconto do profissional (20%).  
- Aplicação das validações descritas na aba “validações” do arquivo VR_MENSAL_05.2025.xlsx.

### Regras de Consolidação e Cálculo:

1. **Consolidação de Bases**  
   - Reunir em uma única base as informações de Ativos, Férias, Desligados, Admitidos, Sindicato x Valor e Dias Úteis.  

2. **Tratamento de Exclusões**  
   - Remover: diretores, estagiários, aprendizes, afastados, profissionais no exterior.  
   - Utilizar matrícula como chave para identificar exclusões.

3. **Validação e Correções**  
   - Ajustar datas inconsistentes (admissão/desligamento).  
   - Tratar férias mal preenchidas (parcial/integral conforme sindicato).  
   - Considerar feriados estaduais e municipais da base de dias úteis.  

4. **Regras Específicas de Cálculo**  
   - **Dias úteis por colaborador** = (dias úteis sindicato – férias – afastamentos – desligamentos proporcionais – admissões proporcionais).  
   - **Regra de desligamento**:  
     - Se comunicado até dia 15: não gerar benefício.  
     - Após dia 15: gerar proporcional até a data do desligamento.  
   - Verificar elegibilidade pelo sindicato (Base-sindicato-x-valor.xlsx).  

5. **Cálculo Final do Benefício**  
   - VR Mensal = (Dias Úteis x Valor do Sindicato).  
   - Custo Empresa = 80% do VR Mensal.  
   - Desconto Profissional = 20% do VR Mensal.  

6. **Entrega Final**  
   - Planilha consolidada no layout da aba “VR Mensal 05.2025”.  
   - Aplicar validações da aba “validações”.  
   - Salvar como: `VR_MENSAL_FINAL_05.2025.xlsx` no diretorio ./data/output
        """
    ),
    tools=[gerar_compra_vr, inspecionar_colunas],
)
