# Automação da compra de VR/VA

[![Version](https://img.shields.io/badge/version-4.0-blue.svg)]() [![Python](https://img.shields.io/badge/python-3.10+-green.svg)]() [![Google ADK](https://img.shields.io/badge/Google_ADK-1.12-red.svg)]()

>Automatizar o processo mensal de compra de VR (Vale Refeição), garantindo que cada colaborador receba o valor correto, considerando ausências, férias e datas de admissão ou desligamento e calendário de feriados.

---
## 🔖 Descrição do problema 

Hoje, o cálculo da quantidade de dias para compra de benefícios é feito manualmente a partir de planilhas. Esse processo envolve:
• Conferência de datas de início e fim do contrato no mês.

• Exclusão de colaboradores em férias (parcial ou integral por regra de
sindicato).

• Ajustes para datas quebradas (ex.: admissões no meio do mês e
desligamentos).

• Cálculo do número exato de dias a serem comprados para cada pessoa.

• Geração de um layout de compra a ser enviado para o fornecedor.

• Considerar as regras vigentes decorrentes dos acordos coletivos de cada um dos sindicatos.

## 🔖 Entrega AI Agent

• Base única consolidada: Reunir e consolidar informações de 5 bases
separadas em uma única base final para (Ativos, Férias, desligados, Base
cadastral (admitidos do mês), Base sindicato x valor e Dias úteis por
colaborador.

• Tratamento de exclusões: Remover da base final, todos os profissionais
com cargo de diretores, estagiários e aprendizes, afastados em geral (ex.:
licença maternidade), profissionais que atuam no exterior. Para isto, se
guiar pela matrícula nas planilhas.

• Validar e corrigir: datas inconsistentes ou "quebradas", campos faltantes, férias mal preenchidas, feriados estaduais e municipais corretamente aplicados

#### Cálculo automatizado do benefício: Com base na planilha calcular automaticamente:

- Quantidade de dias úteis por colaborador (considerando os dias úteis de cada sindicato, férias, afastamentos e data de desligamento)

- Regra de desligamento: Para desligamento se estiver como OK o comunicado de desligamento até dia 15, não considerar para pagamento. Se for informado depois do dia 15, a compra deve ser proporcional. Verificar se pela matricula se é elegível ao benefício (vide base de tratamento de exclusões)

  

---
## 📚 Sumário
1. Visão Geral
2. Pipeline Arquitetural
3. Principais Capacidades
4. Stack & Dependências
5. Estrutura de Pastas
6. Instalação
7. Configuração / Variáveis de Ambiente
8. Uso Rápido (CLI & Web / ADK)

---
## 1. Visão Geral
O agente transforma arquivos xlsx informações organizadas para que o agente faça os calculos
---
## 2. Pipeline Arquitetural
```
Dados ─▶ Normalização ─▶ Raciocinio ▶ Geração de Calculos ▶ Relatório
```
---
## 3. Principais Capacidades
- Normalização dados
- Calculos
- Geracao de Planilha

---
## 4. Stack & Dependências
| Categoria | Tecnologia |
|-----------|------------|
| Linguagem | Python 3.10+ |
| LLM / Agente | Google ADK   |

---
## 5. Estrutura de Pastas (resumida)
```
vr_agent
  app/
    agent.py                 # Entry do agente
    .env
    init
```
---
## 6. Instalação
pip install -r requirements.txt
 

---
## 7. Configuração / Variáveis de Ambiente
Crie `.env` (opcional) na raiz de `agents/diagramador`.

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| GOOGLE_CLOUD_PROJECT | Projeto GCP para logging/tracing | |
| LLM_MODEL | Modelo preferencial | `gemini-2.5-flash` |


---
## 8. Uso Rápido
### ADK Web

adk web --port 8000
```
Acesse: http://localhost:8000