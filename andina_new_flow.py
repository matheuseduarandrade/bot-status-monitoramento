from datetime import datetime, timedelta
import os
import time
import telebot
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
GRUPO_ID = int(os.getenv("GRUPO_ID"))

bot = telebot.TeleBot(TOKEN)

 ALERTAS_ENVIADOS = set()

AGENDA_ANDINA = [
    {
        "cliente": "ANDINA CARIACICA",
        "tecnico": "Irving Simões Pereira",
        "dia_semana": 0,   # segunda
        "inicio": "08:00",
    },
    {
        "cliente": "ANDINA NOVA IGUAÇU",
        "tecnico": "Lucas Roese Bernardo",
        "dia_semana": 1,   # terça
        "inicio": "14:00",
    },
    {
        "cliente": "ANDINA DUQUE DE CAXIAS",
        "tecnico": "Thiago de Almeida Deulefeu",
        "dia_semana": 1,
        "inicio": "14:00",
    },
    {
        "cliente": "ANDINA JACAREPAGUÁ",
        "tecnico": "Thiago de Almeida Deulefeu",
        "dia_semana": 2,   # quarta
        "inicio": "08:00",
    },
]


def montar_mensagem(item, hoje):
    return f"""
🚨 PROJETO ANDINA NEW FLOW 🚨

👨‍🔧 TÉCNICO: {item["tecnico"]}
🔧 AUTO-ELÉTRICA: Queonetics

📅 AGENDAMENTO: {hoje.strftime("%d/%m/%Y")} {item["inicio"]}

📍 BRANCH ARGOS: {item["cliente"]}

===================================
"""


def verificar_andina():

    agora = datetime.now()

    for item in AGENDA_ANDINA:

        if agora.weekday() != item["dia_semana"]:
            continue

        horario = datetime.strptime(
            f'{agora.strftime("%Y-%m-%d")} {item["inicio"]}',
            "%Y-%m-%d %H:%M"
        )

        alerta = horario - timedelta(minutes=20)

        chave = f'{item["cliente"]}_{agora.strftime("%Y-%m-%d")}'

        if (
            agora.hour == alerta.hour
            and agora.minute == alerta.minute
            and chave not in ALERTAS_ENVIADOS
        ):

            bot.send_message(
                GRUPO_ID,
                montar_mensagem(item, agora)
            )

            ALERTAS_ENVIADOS.add(chave)

            print(
                f'[ANDINA] alerta enviado: {item["cliente"]}'
            )


def iniciar_alerta_andina():

    print("Andina New Flow iniciado")

    while True:
        try:
            verificar_andina()

        except Exception as e:
            print(
                f"[ANDINA] erro: {e}"
            )

        time.sleep(60)