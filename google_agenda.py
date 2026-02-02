from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

AGENDAS = {
    "Rene Filho": "rene.filho@queonetics.com",
    "Diego Ribeiro": "diego.ribeiro@queonetics.com",
    "Felipe Silva": "felipe.silva@queonetics.com",
    "Lucas Paixao": "lucas.paixao@queonetics.com",
    "Lucas Dias": "lucas.dias@queonetics.com",
    "Mateus Accioly": "mateus.accioly@queonetics.com",
    "Matheus Eduardo": "matheus.eduardo@queonetics.com"
}

def obter_agenda_do_dia(nome):
    if nome not in AGENDAS:
        return "❌ Agenda não encontrada."

    credentials = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=SCOPES
    )

    service = build("calendar", "v3", credentials=credentials)

    hoje = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    fim_hoje = hoje + timedelta(days=1)

    eventos = service.events().list(
        calendarId=AGENDAS[nome],
        timeMin=hoje.isoformat() + "Z",
        timeMax=fim_hoje.isoformat() + "Z",
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    itens = eventos.get("items", [])

    if not itens:
        return f"📭 *Agenda de {nome}*\n\nSem compromissos hoje."

    resposta = f"📅 *Agenda de {nome} (hoje)*\n\n"

    for evento in itens:
        inicio = evento["start"].get("dateTime", evento["start"].get("date"))
        hora = inicio[11:16] if "T" in inicio else "Dia inteiro"
        titulo = evento.get("summary", "Sem título")
        resposta += f"⏰ {hora} — {titulo}\n"

    return resposta
