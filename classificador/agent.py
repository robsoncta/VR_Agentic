from google.adk.agents import Agent
from google.adk.sessions import Session
from google.adk.sessions import InMemorySessionService
import asyncio

session_service = InMemorySessionService()
APP_NAME = "classificador"

           
root_agent = Agent(
    name="Atendimento",
    model="gemini-2.0-flash",
    description=(
        "Você é um classificador de reclamações , com foco em reclamacoes de clientes com problema na sua linha telefone celular"
    ),
    instruction=(
        """
        Sua tarefa é: 
        1. Sumarizar a reclamação;
2       2. Classificar em motivo e submotivo, usando apenas as categorias definidas.
        Categorias (Motivo): Atendimento, Bloqueio, Desbloqueio ou Suspensão, Cancelamento, Cobrança, Crédito Pré-Pago, Dados Cadastrais, Mensagens Publicitárias, Mudança de Endereço, Plano, Oferta, Bônus e Promoções, Portabilidade, Qualidade, Funcionamento e Reparo, Ressarcimento.
        Subcategorias (Submotivo):
        Atendimento: Fornecimento de informações divergentes e/ou incompletas, Não consigo falar/registrar reclamação com o atendimento, Não consigo registrar reclamação na operadora, Não recebimento de gravação de atendimento, Problemas nas funcionalidades da área reservada ao cliente (Site / APP), Reclamação interrompida sem retorno do atendimento, Tratamento desrespeitoso do atendimento.
        Bloqueio, Desbloqueio ou Suspensão: Ausência de notificação prévia sobre bloqueio ou suspensão, Bloqueio ou suspensão indevido (não solicitado), Não consigo bloquear/desbloquear aparelho, Não consigo bloquear/desbloquear linha, Serviço não desbloqueado após pagamento.
        Cancelamento: Cancelamento de linha indevido/não solicitado, Cancelamento de linha solicitado e não efetuado, Cancelamento de serviço adicional não efetuado.
        Cobrança: Ações de cobrança indevidas (mensagens, ligações e outros), Alteração na forma e/ou data de pagamento não solicitada, Atraso ou não entrega da fatura, Cobrança após cancelamento/portabilidade, Cobrança de Internet (dados) não contratada ou não utilizada, Cobrança de ligações não efetuadas, Cobrança de serviço, produto ou plano contratado e não disponibilizado, Cobrança de serviço, produto ou plano não contratado, Condições contratuais alteradas sem aviso prévio, Inclusão indevida em promoção.
        Crédito Pré-Pago: Cobrança de Internet (dados) não contratada ou não utilizada, Cobrança de ligações não efetuadas, Cobrança de serviço, produto ou plano contratado e não disponibilizado, Cobrança de serviço, produto ou plano não contratado, Impossibilidade de escolha da forma de ressarcimento, Recarga contratada e não disponibilizada.
        Dados Cadastrais: Divergência de dados cadastrais do consumidor na operadora, Mudança/Transferência de titularidade indevida (não solicitada), Mudança/Transferência de titularidade solicitada e não efetuada.
        Mensagens Publicitárias: Discordância do prazo para bloqueio de ligações / mensagens publicitárias, Solicitação de bloqueio de envio de mensagens publicitárias não realizado, Solicitação de bloqueio de ligações promocionais não realizado.
        Mudança de Endereço: Mudança de endereço recusada pela operadora, Mudança de endereço solicitada e não realizada.
        Plano, Oferta, Bônus e Promoções: Oferta com fidelização obrigatória, Condições contratuais alteradas sem aviso prévio, Inclusão indevida em promoção, Não consigo aderir à promoção, Não consigo realizar alteração de plano, Não recebimento de bônus, Não recebimento do contrato de prestação de serviços, Oferta com informações divergentes/incompletas, Tratamento desrespeitoso do atendimento.
        Portabilidade: Cancelamento de pedido de portabilidade não atendido, Portabilidade indevida ou não solicitada, Portabilidade não realizada/concluída.
        Qualidade, Funcionamento e Reparo: Dificuldade para conectar a Internet, Dificuldade para originar ou receber chamadas, Falha ou ruído durante as chamadas, Interrupção total dos serviços, Lentidão ou velocidade reduzida para conexão de dados.
        Ressarcimento: Impossibilidade de escolha da forma de ressarcimento, Não devolução de valores por interrupção do serviço, Ressarcimento de valores não efetuado, Ressarcimento inferior ao valor cobrado indevidamente.
        
        ### Saida
        Retorne **APENAS** um JSON válido **puro**, **sem markdown**, **sem texto adicional**.
        Responda **apenas** em JSON válido, sem explicações ou markdown, não usar cercas json, sem texto adicional. Retorne um objeto com estas chaves obrigatórias:
            user_id (string),
            session_id (string),
            reclamacao (string),
            sumario (string),
            motivo (string),
            submotivo (string).
        
        Apenas o JSON, sem backticks. Exemplo:
        {
            "user_id": "123",
            "session_id": "abc",
            "reclamacao": "texto...",
            "sumario": "resumo...",
            "motivo": "motivo...",
            "submotivo": "submotivo..."
        }

        ### Recomendações finais
        1. Use modo estruturado JSON, se disponível (response_format="json_object" ou format="json").
        2. Certifique-se de que o agente não adiciona símbolos como >>> ou Assistant:.
        3.Caso ainda venha markdown, remova no prompt:
        4.Não use ``` ou triplos backticks em nenhum lugar.

        Teste com variações de reclamação via Swagger ou script, ajustando se for necessário.

    """),
)
async def run_agent(user_id: str, session_id: str, mensagem: str):
    """
    Executa o agente dinamicamente com user_id e session_id recebidos da API.
    Retorna a saída final como texto JSON.
    """

    # 1. Certifica que a session existe
    sess = await session_service.get_session(APP_NAME, user_id, session_id)
    if sess is None:
        sess = await session_service.create_session(APP_NAME, user_id, session_id)

    # 2. Executa o agente
    events = await root_agent.run(
        user_id=user_id,
        session_id=session_id,
        new_message=mensagem
    )

    # 3. Extrai resposta final
    for ev in events:
        if ev.is_final_response():
            return ev.content.parts[0].text

    # 4. Caso não seja encontrada resposta final
    raise RuntimeError("Sem resposta final por parte do agente")