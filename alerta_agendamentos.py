import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

from jira import buscar_agendamentos_hoje

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_GRUPO = os.getenv("TELEGRAM_GRUPO_ALERTA")

fila_alertas = []
alertas_enviados = set()
ultima_consulta = None


def obter_valor_campo(campo):

    if isinstance(campo, dict):

        if "displayName" in campo:
            return campo.get("displayName")

        if "value" in campo:
            return campo.get("value")

    if isinstance(campo, str):
        return campo

    return "N/D"


def atualizar_fila():

    global fila_alertas
    global ultima_consulta

    print("\nConsultando agendamentos no Jira...\n")

    issues = buscar_agendamentos_hoje()

    agrupados = {}
    nova_fila = []

    for issue in issues:

        fields = issue["fields"]

        agendamento = fields.get("customfield_10622")

        if not agendamento:
            continue

        try:
            # PARSE CORRETO COM TIMEZONE
            data_agendada = datetime.strptime(
                agendamento, "%Y-%m-%dT%H:%M:%S.%f%z"
            )

            # CONVERTE PARA HORÁRIO LOCAL (BRASIL)
            data_agendada = data_agendada.astimezone().replace(tzinfo=None)

        except:
            continue

        alerta = data_agendada - timedelta(minutes=20)

        if alerta < datetime.now():
            continue

        tecnico = obter_valor_campo(fields.get("customfield_10623"))
        auto = obter_valor_campo(fields.get("customfield_10624"))
        branch = obter_valor_campo(fields.get("customfield_15615"))

        grupo = f"{tecnico}-{auto}-{data_agendada}"

        if grupo not in agrupados:

            agrupados[grupo] = {
                "alerta": alerta,
                "tecnico": tecnico,
                "auto": auto,
                "horario": data_agendada,
                "branch": branch,
                "quantidade": 0
            }

        agrupados[grupo]["quantidade"] += 1

    for g in agrupados.values():
        nova_fila.append(g)

    fila_alertas = nova_fila
    ultima_consulta = datetime.now()

    print_fila()


def print_fila():

    print("\n============= FILA DE ALERTAS =============\n")

    if not fila_alertas:

        print("Nenhum alerta na fila\n")
        return

    for alerta in fila_alertas:

        horario = alerta["horario"].strftime("%H:%M")
        alerta_hora = alerta["alerta"].strftime("%H:%M")

        print(f"TÉCNICO: {alerta['tecnico']}")
        print(f"AUTO ELÉTRICA: {alerta['auto']}")
        print(f"ATENDIMENTO: {horario}")
        print(f"ALERTA: {alerta_hora}")
        print(f"CHAMADOS: {alerta['quantidade']}")
        print("-----------------------------------")

    print(f"\nTOTAL ALERTAS: {len(fila_alertas)}")
    print("===========================================\n")


def enviar_telegram(msg):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:

        requests.post(
            url,
            json={
                "chat_id": TELEGRAM_GRUPO,
                "text": msg
            }
        )

    except Exception as e:

        print("Erro ao enviar mensagem:", e)


def verificar_alertas():

    agora = datetime.now()

    for alerta in fila_alertas:

        horario_alerta = alerta["alerta"]

        diferenca = (agora - horario_alerta).total_seconds()

        if 0 <= diferenca <= 60:

            chave_unica = f"{alerta['tecnico']}-{horario_alerta}"

            if chave_unica in alertas_enviados:
                continue

            data_formatada = alerta["horario"].strftime("%d/%m/%Y %H:%M")

            mensagem = (
                "🚨 ATENDIMENTO EM BREVE\n\n"
                f"👨‍🔧 TÉCNICO: {alerta['tecnico']}\n"
                f"🔧 AUTO-ELÉTRICA: {alerta['auto']}\n\n"
                f"🔑 QUANTIDADE DE CHAMADOS: {alerta['quantidade']}\n"
                f"📅 AGENDAMENTO: {data_formatada}\n\n"
                f"📍 BRANCH ARGOS: {alerta['branch']}\n\n"
                "==================================="
            )

            enviar_telegram(mensagem)

            alertas_enviados.add(chave_unica)

            print(f"\nALERTA ENVIADO PARA {alerta['tecnico']}\n")


def iniciar_alerta():

    global ultima_consulta

    print("\nMonitor de agendamentos iniciado\n")

    atualizar_fila()

    while True:

        try:

            agora = datetime.now()

            if not ultima_consulta or (agora - ultima_consulta).total_seconds() >= 3600:

                atualizar_fila()

            verificar_alertas()

        except Exception as e:

            print("Erro no monitor:", e)

        time.sleep(60)