import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from google_agenda import obter_agenda_do_dia, AGENDAS
from datetime import datetime
from jira import obter_chamados_pendentes, obter_chamados_pendentes_por_responsavel  # <-- ADICIONADO
import os
from dotenv import load_dotenv

load_dotenv()

CHAVE_API = os.getenv("TELEGRAM_TOKEN")

bot = telebot.TeleBot(CHAVE_API)

# ==========================
# DADOS DO SISTEMA
# ==========================
ADMINS = [1693264743, 820571529, 454348064]
USUARIOS = {
    111111111: "Rene Filho",
    222222222: "Diego Ribeiro",
    333333333: "Felipe Silva",
    444444444: "Lucas Paixao",
    555555555: "Lucas Dias",
    666666666: "Mateus Accioly",
    1693264743: "Matheus Eduardo"
}

CONFIG = {
    "sistema": {
        "nome_bot": "Status Monitoramento",
        "versao": "2.5.0",
        "ambiente": "PRODUÇÃO",
        "timezone": "America/Sao_Paulo",
        "desenvolvedor": "matheus.eduardo@queonetics.com"
    },
    "bot": {"ativo": True, "log_detalhado": True, "auto_cadastro": False}
}

ULTIMA_ACAO_ADMIN = None

# ==========================
# FUNÇÕES AUXILIARES
# ==========================
def eh_admin(user_id):
    return user_id in ADMINS

def registrar_acao_admin(acao):
    global ULTIMA_ACAO_ADMIN
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    ULTIMA_ACAO_ADMIN = f"{acao} - {agora}"

# ==========================
# MENUS
# ==========================
def menu_principal(user_id):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📅 Minha Agenda", callback_data="menu_agenda"),
    )
    if eh_admin(user_id):
        markup.add(
            InlineKeyboardButton("📊 Status", callback_data="menu_status"),
            InlineKeyboardButton("📋 Chamados", callback_data="menu_chamados"),
            InlineKeyboardButton("📊 Projetos", callback_data="menu_projetos"),
            InlineKeyboardButton("📅 Todas Agendas", callback_data="menu_agendas_admin"),
            InlineKeyboardButton("⚙️ Configurações", callback_data="menu_config")
        )
    return markup

def menu_config():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🧠 Sistema", callback_data="config_sistema"),
        InlineKeyboardButton("👥 Acesso", callback_data="config_acesso"),
        InlineKeyboardButton("📅 Agenda", callback_data="config_agenda"),
        InlineKeyboardButton("🤖 Bot", callback_data="config_bot")
    )
    markup.add(InlineKeyboardButton("⬅️ Voltar", callback_data="voltar_menu"))
    return markup

# ==========================
# HANDLERS
# ==========================

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

    # --- STATUS JIRA ---
    if call.data == "menu_status":
        bot.answer_callback_query(call.id, "Consultando Jira...")

        try:
            dados = obter_chamados_pendentes()
            texto = (
                "📊 *STATUS DO DIA*\n\n"
                f"⏳ Chamados pendentes: *{dados['total']}*\n"
                f"🕒 Atualizado em: {dados['atualizado_em']}"
            )
        except Exception as e:
            texto = (
                "⚠️ *ERRO NO JIRA*\n\n"
                "Não foi possível consultar os chamados agora.\n"
                f"Detalhes técnicos:\n`{str(e)}`"
            )

        bot.edit_message_text(
            texto,
            chat_id,
            msg_id,
            parse_mode="Markdown",
            reply_markup=menu_principal(user_id)
        )

    # --- NOVA FUNÇÃO: CHAMADOS POR RESPONSÁVEL ---
    elif call.data == "menu_chamados":
        bot.answer_callback_query(call.id, "Consultando chamados...")

        try:
            dados = obter_chamados_pendentes_por_responsavel()
            texto = "📋 *CHAMADOS PENDENTES POR RESPONSÁVEL*\n\n"

            for responsavel, chamados in dados.items():
                texto += f"👤 *{responsavel}*\n"
                texto += f"⏳ Pendentes: *{len(chamados)}*\n"
                for c in chamados:
                    texto += (
                        f"• `{c['chave']}` — {c['atualizado_em']} "
                        f"(_{c['dias_pendentes']} dias_)\n"
                    )
                texto += "\n"

            if not dados:
                texto += "✅ Nenhum chamado pendente."

        except Exception as e:
            texto = f"⚠️ *Erro ao consultar chamados*\n\n`{str(e)}`"

        bot.edit_message_text(
            texto,
            chat_id,
            msg_id,
            parse_mode="Markdown",
            reply_markup=menu_principal(user_id)
        )

    # --- MINHA AGENDA ---
    elif call.data == "menu_agenda":
        if user_id not in USUARIOS:
            bot.answer_callback_query(call.id, "⛔ Seu ID não está vinculado a nenhuma agenda.", show_alert=True)
            return
        
        bot.answer_callback_query(call.id, "Buscando sua agenda...")
        nome_usuario = USUARIOS[user_id]
        texto_agenda = obter_agenda_do_dia(nome_usuario)
        bot.send_message(chat_id, texto_agenda, parse_mode="Markdown")

    # --- TODAS AS AGENDAS ---
    elif call.data == "menu_agendas_admin":
        if not eh_admin(user_id):
            bot.answer_callback_query(call.id, "Acesso negado")
            return
        
        markup = InlineKeyboardMarkup(row_width=2)
        for nome in AGENDAS.keys():
            markup.add(InlineKeyboardButton(f"👤 {nome}", callback_data=f"ver_{nome}"))
        markup.add(InlineKeyboardButton("⬅️ Voltar", callback_data="voltar_menu"))
        
        bot.edit_message_text("📅 *Agendas da Equipe*", chat_id, msg_id, parse_mode="Markdown", reply_markup=markup)

    elif call.data.startswith("ver_"):
        nome = call.data.replace("ver_", "")
        bot.answer_callback_query(call.id, f"Buscando agenda de {nome}")
        texto = obter_agenda_do_dia(nome)
        bot.send_message(chat_id, texto, parse_mode="Markdown")

    # --- CONFIGURAÇÕES ---
    elif call.data == "menu_config":
        if not eh_admin(user_id): return
        registrar_acao_admin("Acessou Configurações")
        bot.edit_message_text("⚙️ *Configurações*", chat_id, msg_id, parse_mode="Markdown", reply_markup=menu_config())

    elif call.data == "config_sistema":
        s = CONFIG["sistema"]
        texto = f"🧠 *SISTEMA*\n\n🤖 Bot: {s['nome_bot']}\n📦 Versão: {s['versao']}\n🌍 Ambiente: {s['ambiente']}"
        bot.edit_message_text(texto, chat_id, msg_id, parse_mode="Markdown", reply_markup=menu_config())

    elif call.data == "config_acesso":
        texto = f"👥 *ACESSO*\n\n👑 Admins: {len(ADMINS)}\n👤 Usuários: {len(USUARIOS)}\n🕓 Última ação:\n`{ULTIMA_ACAO_ADMIN or 'Nenhuma'}`"
        bot.edit_message_text(texto, chat_id, msg_id, parse_mode="Markdown", reply_markup=menu_config())

    elif call.data == "config_agenda":
        texto = f"📅 *AGENDA*\n\n📊 Total de agendas: {len(AGENDAS)}\n🟢 Provedor: Google Calendar API"
        bot.edit_message_text(texto, chat_id, msg_id, parse_mode="Markdown", reply_markup=menu_config())

    elif call.data == "config_bot":
        b = CONFIG["bot"]
        texto = f"🤖 *BOT*\n\nAtivo: {b['ativo']}\nLogs: {b['log_detalhado']}"
        bot.edit_message_text(texto, chat_id, msg_id, parse_mode="Markdown", reply_markup=menu_config())

    # --- OUTROS ---
    elif call.data == "voltar_menu":
        bot.edit_message_text("🏠 Menu principal", chat_id, msg_id, reply_markup=menu_principal(user_id))

    elif call.data == "menu_projetos":
        bot.answer_callback_query(call.id, "Em breve...", show_alert=True)

print("Bot rodando...")
bot.polling(none_stop=True)
