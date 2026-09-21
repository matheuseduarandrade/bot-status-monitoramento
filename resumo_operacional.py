import os
import time
import requests

from datetime import datetime

from dotenv import load_dotenv

from jira import (
    buscar_agendamentos_dia,
    buscar_resumo_semanal
)

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_GRUPO = os.getenv("TELEGRAM_GRUPO_ALERTA")

ULTIMO_RESUMO_DIARIO = None
ULTIMO_RESUMO_SEMANAL = None


# =====================================================
# MENSAGENS POR DIA
# =====================================================

MENSAGENS_DIA = {
    0: (
        "💪 Segunda-feira chegou!\n\n"
        "Uma nova semana, novas oportunidades e novos desafios.\n\n"
        "Vamos manter o foco, a organização e a qualidade nos atendimentos.\n\n"
        "Boa semana para todos! 🚀"
    ),
    1: (
        "🔥 Terça-feira é dia de acelerar os resultados!\n\n"
        "Vamos manter o ritmo e entregar mais um excelente dia de trabalho."
    ),
    2: (
        "🚀 Chegamos na metade da semana!\n\n"
        "Bora manter a produtividade e seguir firme nos atendimentos."
    ),
    3: (
        "⚡ Quinta-feira é dia de consolidar resultados.\n\n"
        "Cada atendimento concluído hoje faz diferença no fechamento da semana."
    ),
    4: (
        "🎉 Sextou!\n\n"
        "Parabéns pelo empenho durante toda a semana.\n\n"
        "Vamos fechar os atendimentos com excelência para aproveitar um ótimo final de semana. 😎"
    ),
    5: (
        "☀️ Bom dia!\n\n"
        "Mesmo com equipe reduzida, seguimos garantindo a qualidade do atendimento.\n\n"
        "Excelente trabalho a todos. 🚀"
    )
}


# =====================================================
# TELEGRAM
# =====================================================

def enviar_telegram(msg):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:

        requests.post(
            url,
            json={
                "chat_id": TELEGRAM_GRUPO,
                "text": msg
            },
            timeout=15
        )

    except Exception as e:

        print("Erro Telegram:", e)


# =====================================================
# RESUMO DIÁRIO
# =====================================================

def gerar_resumo_diario():

    issues = buscar_agendamentos_dia()

    total_atendimentos = len(issues)

    tecnicos = set()
    placas = set()

    presencial = 0
    noturno = 0

    primeira_agenda = None
    ultima_agenda = None

    for issue in issues:

        fields = issue["fields"]

        tecnico = fields.get("customfield_10623")

        if tecnico:
            tecnicos.add(str(tecnico).strip())

        placas_issue = fields.get("customfield_10401") or []

        for placa in placas_issue:
            placas.add(placa)

        agendamento = fields.get("customfield_10622")

        if not agendamento:
            continue

        try:

            data_agendada = datetime.strptime(
                agendamento,
                "%Y-%m-%dT%H:%M:%S.%f%z"
            )

            data_agendada = (
                data_agendada
                .astimezone()
                .replace(tzinfo=None)
            )

        except Exception:
            continue

        hora = data_agendada.hour

        if hora < 18:
            presencial += 1
        else:
            noturno += 1

        if primeira_agenda is None or data_agendada < primeira_agenda:
            primeira_agenda = data_agendada

        if ultima_agenda is None or data_agendada > ultima_agenda:
            ultima_agenda = data_agendada

    primeira = (
        primeira_agenda.strftime("%H:%M")
        if primeira_agenda else "N/D"
    )

    ultima = (
        ultima_agenda.strftime("%H:%M")
        if ultima_agenda else "N/D"
    )

    mensagem_dia = MENSAGENS_DIA.get(
        datetime.now().weekday(),
        ""
    )

    mensagem = (
        "🌞 RESUMO DIÁRIO\n\n"

        f"📅 Hoje temos {total_atendimentos} atendimentos agendados.\n\n"

        f"👨‍🔧 Técnicos envolvidos: {len(tecnicos)}\n\n"

        f"📍 Turno Presencial (08h às 18h)\n"
        f"• {presencial} atendimentos\n\n"

        f"🌙 Turno Remoto/Noturno (18h às 00h)\n"
        f"• {noturno} atendimentos\n\n"

        f"🚗 Veículos envolvidos: {len(placas)}\n\n"

        f"📌 Primeiro agendamento: {primeira}\n"
        f"📌 Último agendamento: {ultima}\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"{mensagem_dia}"
    )

    return mensagem


# =====================================================
# RESUMO SEMANAL
# =====================================================

def gerar_resumo_semanal():

    issues = buscar_resumo_semanal()

    total = len(issues)

    tecnicos = set()
    placas = set()
    filiais = set()

    sem_reagendamento = 0
    com_reagendamento = 0

    pendente_encerramento = 0
    em_aberto = 0

    for issue in issues:

        fields = issue["fields"]

        status = fields["status"]["name"]

        tecnico = fields.get("customfield_10623")

        if tecnico:
            tecnicos.add(str(tecnico).strip())

        filial = fields.get("customfield_15615")

        if filial:
            filiais.add(str(filial).strip())

        placas_issue = fields.get("customfield_10401") or []

        for placa in placas_issue:
            placas.add(placa)

        # concluídos

        if status == "Sem reagendamento":
            sem_reagendamento += 1

        elif status == "Com reagendamento":
            com_reagendamento += 1

        # pendentes encerramento

        elif status in (
            "Aguardando assinatura da OS",
            "Monitoramento - fazendo",
            "Selected for Development"
        ):
            pendente_encerramento += 1

        # em aberto

        elif status in (
            "A fazer - Monitoramento Projetos",
            "Monitoramento - A fazer"
        ):
            em_aberto += 1

    taxa = 0

    if total > 0:

        taxa = round(
            (com_reagendamento / total) * 100,
            1
        )

    mensagem = (
        "📈 RESUMO DA SEMANA\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"📅 Total de atendimentos programados: {total}\n\n"

        f"👨‍🔧 Técnicos envolvidos: {len(tecnicos)}\n\n"

        f"🚗 Veículos envolvidos: {len(placas)}\n\n"

        f"🏢 Filiais envolvidas: {len(filiais)}\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        f"✅ Sem reagendamento: {sem_reagendamento}\n\n"

        f"🔄 Com reagendamento: {com_reagendamento}\n\n"

        f"📋 Pendentes de encerramento: {pendente_encerramento}\n\n"

        f"⏳ Ainda em aberto: {em_aberto}\n\n"

        f"📊 Taxa de reagendamento: {taxa}%\n\n"

        "━━━━━━━━━━━━━━━━━━━━\n\n"

        "⭐ Obrigado pelo empenho de todos durante esta semana!\n\n"
        "Bom descanso e um excelente final de semana! 🚀"
    )

    return mensagem


# =====================================================
# LOOP PRINCIPAL
# =====================================================

def iniciar_resumo_operacional():

    global ULTIMO_RESUMO_DIARIO
    global ULTIMO_RESUMO_SEMANAL

    print("Resumo operacional iniciado")

    while True:

        try:

            agora = datetime.now()

            # 07:00 diário

            chave_diaria = agora.strftime("%Y-%m-%d")

            if (
                agora.hour == 7
                and agora.minute == 0
                and ULTIMO_RESUMO_DIARIO != chave_diaria
            ):

                enviar_telegram(
                    gerar_resumo_diario()
                )

                ULTIMO_RESUMO_DIARIO = chave_diaria

                print("Resumo diário enviado")

            # Sexta 17:00

            chave_semanal = agora.strftime("%Y-%W")

            if (
                agora.weekday() == 4
                and agora.hour == 17
                and agora.minute == 0
                and ULTIMO_RESUMO_SEMANAL != chave_semanal
            ):

                enviar_telegram(
                    gerar_resumo_semanal()
                )

                ULTIMO_RESUMO_SEMANAL = chave_semanal

                print("Resumo semanal enviado")

        except Exception as e:

            print("Erro resumo operacional:", e)

        time.sleep(30)