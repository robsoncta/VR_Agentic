
# Ambiente Virtual 
python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip

### Comando para instalar 
pip install -r requirements.txt

## Comando para iniciar aplicacao

### FastAPI
uvicorn app.main:app --reload  

#### Web 
Adk Web

### Observalidade 
pip install agentops
pip install langfuse google-adk -q


## Criar Arquivo .env

GOOGLE_API_KEY=key
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
GOOGLE_CLOUD_LOCATION=LOCATION
AGENTOPS_API_KEY=key
LANGFUSE_SECRET_KEY=key
LANGFUSE_PUBLIC_KEY=key
LANGFUSE_ENVIRONMENT="DEV"
