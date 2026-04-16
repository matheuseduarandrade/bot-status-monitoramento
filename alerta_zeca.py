import time
from datetime import datetime
import os

from jira import obter_chamados_pendentes_por_responsavel, obter_chamados_atrasados
from relatorio_pdf import gerar_pdf
import telebot
from dotenv import load_dotenv

load_dotenv()

BOT = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))
USUARIOS_ALERTA  = [820571529, 1693264743]

ultimo_total = None


def coletar_dados():
    dados = obter_chamados_pendentes_por_responsavel()

    pendencias = []
    for resp, chamados in dados.items():
        for c in chamados:
            pendencias.append({
                "key": c["chave"],
                "cliente": resp,
                "data": c["atualizado_em"],
                "link": f"{os.getenv('JIRA_BASE_URL')}/browse/{c['chave']}"
            })

    atrasados = obter_chamados_atrasados()

    return pendencias, atrasados


def enviar_alerta():
    global ultimo_total

    try:
        pendencias, _ = coletar_dados()
        atrasados = obter_chamados_atrasados()

        total = len(pendencias) + len(atrasados)

        # evita spam
        if total == ultimo_total:
            return

        ultimo_total = total

        mensagem = (
            "🚨 ZECA MONITOR - ALERTA\n\n"
            f"📊 Pendências: {len(pendencias)}\n"
            f"⚠️ Atrasados Hoje: {len(atrasados['hoje'])}\n"
            f"🚨 Atrasados Antigos: {len(atrasados['anteriores'])}"
        )

        # Gera PDF junto
        pdf = gerar_pdf(pendencias, atrasados)

        for user_id in USUARIOS_ALERTA:
            BOT.send_message(user_id, mensagem)

            with open(pdf, "rb") as f:
                BOT.send_document(user_id, f)

        os.remove(pdf)

    except Exception as e:
        print("Erro alerta ZECA:", e)


def iniciar_alerta_zeca():
    print("Monitor ZECA iniciado")

    horarios_disparo = ["08:00", "18:00", "22:00"]  # 👈 COLOCA AQUI (horário de teste)

    ja_enviado_hoje = set()

    while True:
        agora = datetime.now().strftime("%H:%M")

        if agora in horarios_disparo and agora not in ja_enviado_hoje:
            print(f"Enviando alerta ZECA {agora}")
            
            enviar_alerta()
            
            ja_enviado_hoje.add(agora)

        # limpa no dia seguinte
        if agora == "00:00":
            ja_enviado_hoje.clear()

        time.sleep(30)