from threading import Thread
from resumo_operacional import iniciar_resumo_operacional
from andina_new_flow import iniciar_alerta_andina
from alerta_zeca import iniciar_alerta_zeca
from alerta_agendamentos import iniciar_alerta
import telebot
from relatorio_pdf import gerar_pdf
from jira import obter_chamados_atrasados
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google_agenda import obter_agenda_do_dia, AGENDAS
from datetime import datetime
from jira import (
    obter_chamados_pendentes,
    obter_chamados_pendentes_por_responsavel
)
import os
import time
import json
import re as _re
from dotenv import load_dotenv
from datetime import datetime, timedelta

MENSAGENS_ENVIADAS = []

load_dotenv()

CHAVE_API = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(CHAVE_API)

ADMINS = list(map(int, os.getenv("ADMINS").split(",")))

USUARIOS = {
    int(k): v
    for k, v in json.loads(os.getenv("USUARIOS_JSON")).items()
}

CONFIG = {
    "sistema": {
        "nome_bot": "Status Monitoramento",
        "versao": "2.8.3",
        "ambiente": "PRODUÇÃO",
        "timezone": "America/Sao_Paulo",
        "desenvolvedor": "matheus.eduardo@queonetics.com",
        "integracoes": ["Jira API", "Google Calendar API"]
    },
    "bot": {
        "ativo": True,
        "log_detalhado": True,
        "auto_cadastro": False
    },
    "telemetria": {
        "CRM": "Em desenvolvimento",
        "TRIX": "Em desenvolvimento"
    }
}

ULTIMA_ACAO_ADMIN = None

# ──────────────────────────────────────────
# USERNAME DO BOT — buscado UMA vez só
# ──────────────────────────────────────────
BOT_USERNAME = bot.get_me().username
print(f"Bot iniciado como @{BOT_USERNAME}")


def eh_admin(user_id):
    return user_id in ADMINS


def registrar_acao_admin(acao):
    global ULTIMA_ACAO_ADMIN
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    ULTIMA_ACAO_ADMIN = f"{acao} - {agora}"


def menu_principal(user_id):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📅 Minha Agenda", callback_data="menu_agenda"),
        InlineKeyboardButton("📄 Relatório ZECA", callback_data="zeca_monitor")
    )
    if eh_admin(user_id):
        markup.add(
            InlineKeyboardButton("📊 Status", callback_data="menu_status"),
            InlineKeyboardButton(
                "📋 Pendencias", callback_data="menu_pendencias"),
            InlineKeyboardButton(
                "📅 Todas Agendas", callback_data="menu_agendas_admin"),
            InlineKeyboardButton("🛎️ Chamados do dia",
                                 callback_data="menu_chamados_dia"),
            InlineKeyboardButton("⚙️ Configurações",
                                 callback_data="menu_config")
        )
    return markup


def menu_config():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🧠 Sistema", callback_data="config_sistema"),
        InlineKeyboardButton("👥 Acesso", callback_data="config_acesso"),
        InlineKeyboardButton("📅 Agenda", callback_data="config_agenda"),
        InlineKeyboardButton("🤖 Bot", callback_data="config_bot"),
        InlineKeyboardButton(
            "👨‍💻 Telemetria", callback_data="config_telemetria")
    )
    markup.add(InlineKeyboardButton("⬅️ Voltar", callback_data="voltar_menu"))
    return markup


def menu_pendencias():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📋 Gerais", callback_data="pendentes_gerais"),
        InlineKeyboardButton("🚨 Críticas", callback_data="pendentes_criticas"),
        InlineKeyboardButton("⬅️ Voltar", callback_data="voltar_menu")
    )
    return markup


def escapar_markdown(texto):
    especiais = ["_", "*", "[", "]",
                 "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]
    for c in especiais:
        texto = texto.replace(c, f"\\{c}")
    return texto


# ──────────────────────────────────────────
# HELPERS DE MENÇÃO
# ──────────────────────────────────────────

def _limpar_mencao(texto: str) -> str:
    """Remove @BotUsername do texto."""
    padrao = rf"@{_re.escape(BOT_USERNAME)}\s*"
    return _re.sub(padrao, "", texto, flags=_re.IGNORECASE).strip()


def _foi_mencionado(mensagem) -> bool:
    """Verifica se o bot foi mencionado ou se é reply ao bot."""
    texto = mensagem.text or ""
    if f"@{BOT_USERNAME}" in texto:
        return True
    if (
        mensagem.reply_to_message
        and mensagem.reply_to_message.from_user
        and mensagem.reply_to_message.from_user.username == BOT_USERNAME
    ):
        return True
    return False


def registrar_envio(msg):
    MENSAGENS_ENVIADAS.append({
        "message_id": msg.message_id,
        "data": datetime.now()
    })


# ──────────────────────────────────────────
# HANDLERS
# ──────────────────────────────────────────

@bot.message_handler(commands=["start"])
def start(mensagem):
    bot.send_message(
        mensagem.chat.id,
        "👋 Bem-vindo ao *Status Monitoramento*",
        parse_mode="Markdown",
        reply_markup=menu_principal(mensagem.from_user.id)
    )


@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    msg_id = call.message.message_id

    if call.data == "menu_status":
        bot.answer_callback_query(call.id, "Consultando Jira...")
        registrar_acao_admin("Consultou Status Jira")
        try:
            dados = obter_chamados_pendentes()
            texto = (
                "📊 *STATUS DO DIA*\n\n"
                f"⏳ Chamados pendentes: *{dados['total']}*\n"
                f"🕒 Atualizado em: {dados['atualizado_em']}"
            )
        except Exception as e:
            texto = f"⚠️ *Erro no Jira*\n\n`{str(e)}`"
        bot.edit_message_text(
            texto, chat_id, msg_id, parse_mode="Markdown", reply_markup=menu_principal(user_id))

    elif call.data == "menu_pendencias":
        bot.edit_message_text("📋 *Pendências*\n\nEscolha uma opção:", chat_id,
                              msg_id, parse_mode="Markdown", reply_markup=menu_pendencias())

    elif call.data == "pendentes_gerais":
        from jira import separar_pendencias
        dados = obter_chamados_pendentes_por_responsavel()
        dados = separar_pendencias(dados)
        texto = "📋 *Pendências Gerais*\n\n"
        for responsavel, chamados in dados.items():
            texto += f"👤 *{escapar_markdown(responsavel)}*\n"
            texto += f"⏳ Pendentes: *{len(chamados)}*\n\n"
            for c in chamados:
                texto += f"• `{c['chave']}` — {c['atualizado_em']} (_{c['dias_pendentes']} dias_)\n"
            texto += "\n"
        bot.edit_message_text(
            texto, chat_id, msg_id, parse_mode="Markdown", reply_markup=menu_pendencias())

    elif call.data == "pendentes_criticas":
        from jira import separar_pendencias
        dados = obter_chamados_pendentes_por_responsavel()
        dados = separar_pendencias(dados, somente_criticos=True)
        texto = "🚨 *PENDÊNCIAS CRÍTICAS (2+ DIAS)*\n\n"
        for responsavel, chamados in dados.items():
            texto += f"👤 *{escapar_markdown(responsavel)}*\n"
            texto += f"⏳ Pendentes: *{len(chamados)}*\n"
            for c in chamados:
                texto += (
                    f"• `{c['chave']}` — {escapar_markdown(c['tecnico'])} — "
                    f"{c['atualizado_em']} (_{c['dias_pendentes']} dias_)\n"
                )
            texto += "\n"
        if not dados:
            texto += "✅ Nenhuma pendência crítica encontrada!"
        bot.edit_message_text(
            texto, chat_id, msg_id, parse_mode="Markdown", reply_markup=menu_pendencias())

    elif call.data == "menu_agenda":
        if user_id not in USUARIOS:
            bot.answer_callback_query(
                call.id, "⛔ Acesso não vinculado.", show_alert=True)
            return
        bot.answer_callback_query(call.id, "Buscando agenda...")
        texto = obter_agenda_do_dia(USUARIOS[user_id])
        bot.edit_message_text(
            texto, chat_id, msg_id, parse_mode="Markdown", reply_markup=menu_principal(user_id))

    elif call.data == "menu_agendas_admin":
        if not eh_admin(user_id):
            return
        registrar_acao_admin("Consultou Agendas")
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton(
            "🌐 Geral", callback_data="ver_geral_agendas"))
        for nome in AGENDAS.keys():
            markup.add(InlineKeyboardButton(
                f"👤 {nome}", callback_data=f"ver_{nome}"))
        markup.add(InlineKeyboardButton(
            "⬅️ Voltar", callback_data="voltar_menu"))
        bot.edit_message_text("📅 *Agendas da Equipe*", chat_id,
                              msg_id, parse_mode="Markdown", reply_markup=markup)

    elif call.data == "ver_geral_agendas":
        texto = "🌐 *RELATÓRIO GERAL*\n\n"
        for nome in AGENDAS.keys():
            try:
                texto += obter_agenda_do_dia(nome) + "\n\n"
            except Exception:
                texto += f"👤 *{nome}*\n⚠️ Erro ao acessar agenda\n\n"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(
            "⬅️ Voltar", callback_data="menu_agendas_admin"))
        bot.edit_message_text(texto, chat_id, msg_id,
                              parse_mode="Markdown", reply_markup=markup)

    elif call.data.startswith("ver_"):
        nome_agenda = call.data.replace("ver_", "")
        if nome_agenda not in AGENDAS:
            bot.answer_callback_query(
                call.id, "Agenda não encontrada.", show_alert=True)
            return
        try:
            texto = obter_agenda_do_dia(nome_agenda)
        except Exception as e:
            texto = f"⚠️ Erro ao acessar agenda de *{nome_agenda}*\n\n`{str(e)}`"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(
            "⬅️ Voltar", callback_data="menu_agendas_admin"))
        bot.edit_message_text(texto, chat_id, msg_id,
                              parse_mode="Markdown", reply_markup=markup)

    elif call.data == "menu_config":
        registrar_acao_admin("Acessou Configurações")
        bot.edit_message_text("⚙️ *Configurações*", chat_id, msg_id,
                              parse_mode="Markdown", reply_markup=menu_config())

    elif call.data == "config_sistema":
        s = CONFIG["sistema"]
        texto = (
            "🧠 *SISTEMA*\n\n"
            f"🤖 {s['nome_bot']}\n"
            f"📦 Versão: {s['versao']}\n"
            f"🌍 Ambiente: {s['ambiente']}\n"
            f"🔗 Integrações: {', '.join(s['integracoes'])}"
        )
        bot.edit_message_text(texto, chat_id, msg_id,
                              parse_mode="Markdown", reply_markup=menu_config())

    elif call.data == "config_acesso":
        texto = (
            "👥 *ACESSO*\n\n"
            f"👑 Admins: {len(ADMINS)}\n"
            f"👤 Usuários: {len(USUARIOS)}\n\n"
            f"🕓 Última ação:\n`{ULTIMA_ACAO_ADMIN or 'Nenhuma'}`"
        )
        bot.edit_message_text(texto, chat_id, msg_id,
                              parse_mode="Markdown", reply_markup=menu_config())

    elif call.data == "config_agenda":
        texto = (
            f"📅 *AGENDA*\n\n📊 Total: {len(AGENDAS)}\n🟢 Google Calendar API")
        bot.edit_message_text(texto, chat_id, msg_id,
                              parse_mode="Markdown", reply_markup=menu_config())

    elif call.data == "config_bot":
        b = CONFIG["bot"]
        texto = f"🤖 *BOT*\n\nAtivo: {b['ativo']}\nLogs: {b['log_detalhado']}"
        bot.edit_message_text(texto, chat_id, msg_id,
                              parse_mode="Markdown", reply_markup=menu_config())

    elif call.data == "config_telemetria":
        t = CONFIG["telemetria"]
        texto = f"👨‍💻 *TELEMETRIA*\n\nCRM: {t['CRM']}\nTRIX: {t['TRIX']}"
        bot.edit_message_text(texto, chat_id, msg_id,
                              parse_mode="Markdown", reply_markup=menu_config())

    elif call.data == "voltar_menu":
        bot.edit_message_text("🏠 Menu Principal", chat_id,
                              msg_id, reply_markup=menu_principal(user_id))

    elif call.data == "menu_projetos":
        bot.answer_callback_query(call.id, "Em breve...", show_alert=True)

    elif call.data == "menu_telemetria":
        bot.answer_callback_query(
            call.id, "Módulo em desenvolvimento...", show_alert=True)

    elif call.data == "zeca_monitor":
        if call.from_user.id != 820571529:
            bot.answer_callback_query(
                call.id, "⛔ Acesso restrito", show_alert=True)
            return
        bot.answer_callback_query(call.id, "Gerando relatório...")
        try:
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
            pdf_path = gerar_pdf(pendencias, atrasados)
            with open(pdf_path, "rb") as pdf:
                bot.send_document(chat_id=820571529, document=pdf,
                                  filename="relatorio_zeca_monitor.pdf")
            os.remove(pdf_path)
        except Exception as e:
            bot.send_message(chat_id, f"❌ Erro ao gerar relatório:\n{str(e)}")


# ──────────────────────────────────────────
# IA — MENÇÕES NO GRUPO E MENSAGENS PRIVADAS
# ──────────────────────────────────────────

@bot.message_handler(
    func=lambda msg: (
        msg.text and (
            (msg.chat.type in ("group", "supergroup") and _foi_mencionado(msg))
            or
            (msg.chat.type == "private" and not msg.text.startswith("/"))
        )
    ),
    content_types=["text"],
)
def responder_com_ia(mensagem):
    from ia_resposta import processar_mensagem

    chat_id = mensagem.chat.id
    nome_usuario = mensagem.from_user.first_name or "usuário"
    texto_limpo = _limpar_mencao(mensagem.text or "")

    if not texto_limpo:
        bot.reply_to(mensagem, "Oi! Pode me perguntar algo 😊")
        return

    bot.send_chat_action(chat_id, "typing")

    try:
        resposta = processar_mensagem(
            texto_limpo,
            nome_usuario=nome_usuario
        )
    except Exception as e:
        bot.reply_to(
            mensagem,
            f"⚠️ Ocorreu um erro: {str(e)}"
        )
        return

    # FOTO DO ZECA
    if isinstance(resposta, dict) and resposta.get("tipo") == "foto":

        with open(resposta["arquivo"], "rb") as foto:
            bot.send_photo(
                chat_id=mensagem.chat.id,
                photo=foto,
                caption=resposta["legenda"]
            )

        return

    # TEXTO NORMAL
    try:
        bot.reply_to(
            mensagem,
            resposta,
            parse_mode="Markdown"
        )
    except Exception:
        bot.reply_to(mensagem, resposta)

    except Exception as e:
        bot.reply_to(
            mensagem,
            f"⚠️ Ocorreu um erro: {str(e)}"
        )


# ──────────────────────────────────────────
# COMANDOS DE BROADCAST
# ──────────────────────────────────────────

GRUPO_ID = int(os.getenv("GRUPO_ID"))


@bot.message_handler(commands=["broadcast"])
def broadcast(mensagem):
    if not eh_admin(mensagem.from_user.id):
        bot.reply_to(mensagem, "⛔ Acesso negado.")
        return
    partes = mensagem.text.split(" ", 1)
    if len(partes) < 2 or not partes[1].strip():
        bot.reply_to(
            mensagem, "⚠️ *Uso correto:*\n`/broadcast Sua mensagem aqui`", parse_mode="Markdown")
        return
    try:
        bot.send_message(
            GRUPO_ID, f"📢 *Aviso do Monitoramento:*\n\n{partes[1].strip()}", parse_mode="Markdown")
        registrar_acao_admin(f"Broadcast enviado: {partes[1][:30]}...")
        bot.reply_to(mensagem, "✅ Mensagem enviada ao grupo!")
    except Exception as e:
        bot.reply_to(
            mensagem, f"❌ Erro ao enviar:\n`{str(e)}`", parse_mode="Markdown")


@bot.message_handler(commands=["mensagem"])
def mensagem_livre(mensagem):
    if not eh_admin(mensagem.from_user.id):
        bot.reply_to(mensagem, "⛔ Acesso negado.")
        return
    partes = mensagem.text.split(" ", 1)
    if len(partes) < 2 or not partes[1].strip():
        bot.reply_to(
            mensagem, "⚠️ *Uso correto:*\n`/mensagem Sua mensagem aqui`", parse_mode="Markdown")
        return
    try:
        bot.send_message(GRUPO_ID, partes[1].strip(), parse_mode="Markdown")
        registrar_acao_admin(f"Mensagem livre enviada: {partes[1][:30]}...")
        bot.reply_to(mensagem, "✅ Mensagem enviada!")
    except Exception as e:
        bot.reply_to(mensagem, f"❌ Erro:\n`{str(e)}`", parse_mode="Markdown")


@bot.message_handler(commands=["enviar"])
def enviar_foto_grupo(mensagem):
    if not eh_admin(mensagem.from_user.id):
        bot.reply_to(mensagem, "⛔ Acesso negado.")
        return

    if not mensagem.reply_to_message:
        bot.reply_to(
            mensagem,
            "⚠️ Responda uma foto com /enviar"
        )
        return

    foto_msg = mensagem.reply_to_message

    if not foto_msg.photo:
        bot.reply_to(
            mensagem,
            "⚠️ A mensagem respondida não contém uma foto."
        )
        return

    try:
        # legenda opcional após o comando
        partes = mensagem.text.split(" ", 1)
        legenda = partes[1] if len(partes) > 1 else foto_msg.caption

        file_id = foto_msg.photo[-1].file_id

        bot.send_photo(
            chat_id=GRUPO_ID,
            photo=file_id,
            caption=legenda
        )

        registrar_acao_admin("Foto enviada ao grupo")
        bot.reply_to(mensagem, "✅ Foto enviada ao grupo!")

    except Exception as e:
        bot.reply_to(
            mensagem,
            f"❌ Erro ao enviar foto:\n{str(e)}"
        )
    

@bot.message_handler(commands=["enviar_audio"])
def enviar_audio_grupo(mensagem):
    if not eh_admin(mensagem.from_user.id):
        bot.reply_to(mensagem, "⛔ Acesso negado.")
        return

    if not mensagem.reply_to_message:
        bot.reply_to(
            mensagem,
            "⚠️ Responda um áudio com /enviar_audio"
        )
        return

    msg = mensagem.reply_to_message

    try:

        # Mensagem de voz (gravada pelo Telegram)
        if msg.voice:
            bot.send_voice(
                chat_id=GRUPO_ID,
                voice=msg.voice.file_id
            )

            bot.reply_to(
                mensagem,
                "✅ Mensagem de voz enviada ao grupo!"
            )
            return

        # Arquivo de áudio (mp3, etc)
        if msg.audio:
            bot.send_audio(
                chat_id=GRUPO_ID,
                audio=msg.audio.file_id,
                caption=msg.caption
            )

            bot.reply_to(
                mensagem,
                "✅ Áudio enviado ao grupo!"
            )
            return

        bot.reply_to(
            mensagem,
            "⚠️ A mensagem respondida não contém áudio."
        )

    except Exception as e:
        bot.reply_to(
            mensagem,
            f"❌ Erro ao enviar:\n{str(e)}"
        )


@bot.message_handler(commands=["apagar"])
def apagar_ultimos_5_minutos(mensagem):

    if not eh_admin(mensagem.from_user.id):
        bot.reply_to(mensagem, "⛔ Acesso negado.")
        return

    agora = datetime.now()
    limite = agora - timedelta(minutes=5)

    apagadas = 0

    for item in MENSAGENS_ENVIADAS[:]:

        if item["data"] >= limite:

            try:
                bot.delete_message(
                    chat_id=GRUPO_ID,
                    message_id=item["message_id"]
                )

                apagadas += 1

            except Exception:
                pass

            MENSAGENS_ENVIADAS.remove(item)

        bot.reply_to(
            mensagem,
            f"🗑️ {apagadas} mensagem(ns) apagada(s) dos últimos 5 minutos."
        )


@bot.message_handler(commands=["apagar_id"])
def apagar_id(mensagem):

    if not eh_admin(mensagem.from_user.id):
        return

    partes = mensagem.text.split()

    if len(partes) != 2:
        bot.reply_to(
            mensagem,
            "Uso: /apagar_id 60622"
        )
        return

    try:

        message_id = int(partes[1])

        bot.delete_message(
            chat_id=GRUPO_ID,
            message_id=message_id
        )

        bot.reply_to(
            mensagem,
            "✅ Mensagem apagada."
        )

    except Exception as e:
        bot.reply_to(
            mensagem,
            f"❌ Erro: {e}"
        )
# ──────────────────────────────────────────
# THREADS DE ALERTA
# ──────────────────────────────────────────


Thread(
    target=iniciar_resumo_operacional,
    daemon=True
).start()

Thread(
    target=iniciar_alerta,
    daemon=True
).start()

Thread(
    target=iniciar_alerta_zeca,
    daemon=True
).start()

Thread(
    target=iniciar_alerta_andina,
    daemon=True
).start()


print("\nBot rodando...")

while True:
    try:
        bot.polling(none_stop=True, timeout=60)
    except Exception as e:
        print(f"Erro crítico: {e}")
        time.sleep(5)
