from dotenv import load_dotenv
import os
import re
import json
from langfuse import Langfuse, get_client, observe
from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel, Field
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from classificador.agent import root_agent
from google.genai import types  # para Content / Part
from contextlib import asynccontextmanager  # CHANGED: import para lifespan
from classificador.agent import root_agent as classificador_agent
from atendimento.agent import root_agent as atendimento_agent

load_dotenv()  

if not os.getenv("GOOGLE_API_KEY"):
    raise RuntimeError(
        "GOOGLE_API_KEY não encontrada. "
        "Defina-a no .env ou como variável de ambiente."
    )

LANGFUSE_SECRET = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_PUBLIC = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST")
LANGFUSE_ENVIRONMENT = os.getenv ("LANGFUSE_ENVIRONMENT")

if not (LANGFUSE_SECRET and LANGFUSE_PUBLIC):
    raise RuntimeError("Langfuse keys não definidas no .env!")

# Inicializa Langfuse com tracing habilitado
langfuse = Langfuse(
    secret_key=LANGFUSE_SECRET,
    public_key=LANGFUSE_PUBLIC,
    host=LANGFUSE_HOST,
    environment=LANGFUSE_ENVIRONMENT,
   )

# -------- infraestrutura ADK --------
session_service = InMemorySessionService()

runner_classificador = Runner(
    app_name="classificador",
    agent=classificador_agent,
    session_service=session_service
)

runner_atendimento = Runner(
    app_name="atendimento",
    agent=atendimento_agent,
    session_service=session_service
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup logic (se necessário)…
    yield
    # shutdown logic: flush do Langfuse
    get_client().flush()

# -------- FastAPI --------
app = FastAPI(
    title="Central de Serviços Inteligente",
    version="1.1.0",
    description="Servicos de API com Agentes de IA para Classificação e Atendimento",
    lifespan=lifespan
)

router = APIRouter()

class ClassifyRequest(BaseModel):
    user_id: str 
    session_id: str
    reclamacao: str

# ---------- Rota Service ----------
@router.post("/service")
@observe() 
async def service(req: ClassifyRequest):
    client = get_client()
    client.update_current_trace(
        session_id=req.session_id,
        user_id=req.user_id,
        input=req.reclamacao,
        metadata={"environment": LANGFUSE_ENVIRONMENT,"tag": "atendimento"},
        version=app.version, 
    )

    sess = await session_service.get_session(
        app_name="atendimento",
        user_id=req.user_id,
        session_id=req.session_id
    )
    if sess is None:
        sess = await session_service.create_session(
            app_name="atendimento",
            user_id=req.user_id,
            session_id=req.session_id
        )

    user_content = types.Content(
        role="user",
        parts=[types.Part(text=req.reclamacao)]
    )

    events = []
    for event in runner_atendimento.run(
        user_id=req.user_id,
        session_id=req.session_id,
        new_message=user_content
    ):
        events.append(event)

    final_text = None
    for ev in events:
        if ev.is_final_response():
            final_text = ev.content.parts[0].text
            break

    if final_text is None:
        raise HTTPException(500, "Sem resposta do agente")
    
    cleaned = final_text.replace("```json", "").replace("```", "").strip()
    
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(500, detail=f"JSON inválido: {exc}")
    
    payload["user_id"] = req.user_id
    payload["session_id"] = req.session_id

    client.update_current_trace(
        output=payload,
        tags=["concluído"]
    )
    
    return payload

# ---------- Rota classify ----------
@router.post("/classify")
@observe() 
async def classify(req: ClassifyRequest):
    client = get_client()
    client.update_current_trace(
        session_id=req.session_id,
        user_id=req.user_id,
        input=req.reclamacao,
        metadata={"environment": LANGFUSE_ENVIRONMENT, "tag": "classificação"},
        version=app.version,
    )

    sess = await session_service.get_session(
        app_name="classificador",
        user_id=req.user_id,
        session_id=req.session_id
    )
    if sess is None:
        sess = await session_service.create_session(
            app_name="classificador",
            user_id=req.user_id,
            session_id=req.session_id
        )

    user_content = types.Content(
        role="user",
        parts=[types.Part(text=req.reclamacao)]
    )

    events = []
    for event in runner_classificador.run(
        user_id=req.user_id,
        session_id=req.session_id,
        new_message=user_content
    ):
        events.append(event)

    final_text = None
    for ev in events:
        if ev.is_final_response():
            final_text = ev.content.parts[0].text
            break

    if final_text is None:
        raise HTTPException(500, "Sem resposta do agente")
    
    cleaned = final_text.replace("```json", "").replace("```", "").strip()
    
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(500, detail=f"JSON inválido: {exc}")
    
    payload["user_id"] = req.user_id
    payload["session_id"] = req.session_id

    client.update_current_trace(
        output=payload,
        tags=["concluído"]
    )
    
    return payload

app.include_router(router)

# ---------- Execução direta com auto‑reload ----------
if __name__ == "__main__":
    import os
    import uvicorn
    
    # Configurações para Render.com
    host = "0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1"
    port = int(os.environ.get("PORT", 8000))  # Usa $PORT no Render, senão 8000 local
    reload = not bool(os.environ.get("RENDER"))  # Desativa reload no Render

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload
    )