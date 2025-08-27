from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part
from vr_agent.agent import root_agent

if __name__ == "__main__":
    runner = InMemoryRunner(root_agent)
    session = runner.session_service().create_session(root_agent.name, "user").blocking_get()

    # Exemplo: gerar o layout
    prompt = (
        "Gerar layout VR. Base dir: /data. "
        "Arquivos: {"
        '"ATIVOS":"ATIVOS.xlsx",'
        '"DESLIGADOS":"DESLIGADOS.xlsx",'
        '"ADMISSAO":"ADMISSÃO ABRIL.xlsx",'
        '"AFASTAMENTOS":"AFASTAMENTOS.xlsx",'
        '"APRENDIZ":"APRENDIZ.xlsx",'
        '"ESTAGIO":"ESTÁGIO.xlsx",'
        '"BASE_DIAS_UTEIS":"Base dias uteis.xlsx",'
        '"BASE_SINDICATO_VALOR":"Base sindicato x valor.xlsx"'
        "}. "
        "Saída: VR_VA_COMPRA_05_2025_ADK.xlsx"
    )
    events = runner.run_async("user", session.id(), Content.from_parts(Part.fromText(prompt)))
    for ev in events.blocking_iterable():
        print(ev.stringify_content())
