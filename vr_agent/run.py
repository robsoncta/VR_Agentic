from pathlib import Path
from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part
from vr_agent.agent import root_agent

if __name__ == "__main__":
    # Configuração do agente
    runner = InMemoryRunner(root_agent)
    session = runner.session_service().create_session(root_agent.name, "user").blocking_get()

    # Diretório base seguro e arquivos
    base_dir = Path("./data")  # relativo ao projeto, não root
    arquivos = {
        "ATIVOS": "ATIVOS.xlsx",
        "DESLIGADOS": "DESLIGADOS.xlsx",
        "ADMISSAO": "ADMISSÃO ABRIL.xlsx",
        "AFASTAMENTOS": "AFASTAMENTOS.xlsx",
        "APRENDIZ": "APRENDIZ.xlsx",
        "ESTAGIO": "ESTÁGIO.xlsx",
        "BASE_DIAS_UTEIS": "Base dias uteis.xlsx",
        "BASE_SINDICATO_VALOR": "Base sindicato x valor.xlsx"
    }
    saida_arquivo = "VR_VA_COMPRA_05_2025_ADK.xlsx"

    # Validação automática: checar se todos os arquivos existem
    missing_files = [f for f in arquivos.values() if not (base_dir / f).exists()]
    if missing_files:
        print("⚠️ Erro: os seguintes arquivos não foram encontrados em './data':")
        for f in missing_files:
            print(f"  - {f}")
        exit(1)  # interrompe execução

    # Prompt textual para o agente (continua via ADK)
    prompt_text = (
        "Gerar layout VR. Base dir: ./data. "
        f"Arquivos: {arquivos}. "
        f"Saída: {saida_arquivo}"
    )

    # Executa o agente
    events = runner.run_async("user", session.id(), Content.from_parts(Part.fromText(prompt_text)))
    for ev in events.blocking_iterable():
        print(ev.stringify_content())

    # Alternativa opcional: chamar a função Python diretamente (debug)
    # result = root_agent.tools[0](str(base_dir), saida_arquivo, arquivos)
    # print(result)
