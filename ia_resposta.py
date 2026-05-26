"""
ia_resposta.py - v7
ZECA - Assistente virtual da Queonetics
Modo casual + modo Jira
"""

import os
import re
import json
import random
import requests

from groq import Groq
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from jira import buscar_todas_issues, separar_pendencias, JQL_PENDENTES
from tecnicos import encontrar_tecnico

load_dotenv()

# ──────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

JIRA_BASE_URL     = os.getenv("JIRA_BASE_URL")
JIRA_USER         = os.getenv("JIRA_USER")
JIRA_PASSWORD     = os.getenv("JIRA_PASSWORD")

CAMPO_TECNICO     = os.getenv("JIRA_ID_TECNICO")
CAMPO_PROJETO     = os.getenv("JIRA_ID_PROJETO", "")

CAMPO_AGENDAMENTO = "customfield_10622"
CAMPO_BRANCH      = "customfield_15615"
CAMPO_PLACA       = "customfield_10900"

AUTH = HTTPBasicAuth(JIRA_USER, JIRA_PASSWORD)

HEADERS = {
    "Accept": "application/json"
}

TZ_BRASILIA = timezone(timedelta(hours=-3))

# ──────────────────────────────────────────
# OPERADORES
# ──────────────────────────────────────────

OPERADORES = [
    "Rene Filho",
    "Eduardo Andrade",
    "Lucas Paixão",
    "Lucas Dias",
    "Pedro Miguel",
    "Diego Oliveira",
    "Felipe Silva",
    "M. Vinicius",
    "Marcos Vinicius",
]

def encontrar_operador(nome: str) -> str | None:
    nome_norm = nome.lower().strip()

    for op in OPERADORES:
        if nome_norm in op.lower():
            return op

    return None

# ──────────────────────────────────────────
# STATUS
# ──────────────────────────────────────────

STATUS_DESCRICAO = {
    "sem reagendamento":                "✅ Concluído",
    "com reagendamento":                "🔄 Concluído com reagendamento",
    "a fazer - monitoramento projetos": "🕐 Não iniciado",
    "monitoramento - a fazer":          "🕐 Não iniciado",
    "monitoramento - fazendo":          "🔧 Em andamento",
    "monitorameto - fazendo":           "🔧 Em andamento",
    "aguardando assinatura da os":      "⏳ Aguardando assinatura da OS",
    "fazendo - monitoramento projetos": "🔧 Em andamento",
    "selected for development":         "⏳ Pendente de encerramento",
    "backlog":                          "🕐 Não iniciado",
}

STATUS_ENCERRAMENTO = {
    "aguardando assinatura da os",
    "selected for development"
}

def traduzir_status(s: str) -> str:
    return STATUS_DESCRICAO.get(s.strip().lower(), s)

def eh_reagendamento(s: str) -> bool:
    return s.strip().lower() == "com reagendamento"

# ──────────────────────────────────────────
# GATILHOS JIRA
# ──────────────────────────────────────────

GATILHOS_JIRA = {
    "#jira",
}

def eh_mensagem_jira(texto: str) -> bool:
    return any(g in texto.lower() for g in GATILHOS_JIRA)

def extrair_chave_chamado(texto: str) -> str | None:
    m = re.search(r"\b([A-Z][A-Z0-9]+-\d+)\b", texto)

    return m.group(1) if m else None

# ──────────────────────────────────────────
# DETECÇÃO CASUAL
# ──────────────────────────────────────────

def eh_conversa_casual(texto: str) -> bool:
    t = texto.lower()

    if eh_mensagem_jira(t):
        return False

    if extrair_chave_chamado(t):
        return False

    palavras_operacionais = [
        "chamado",
        "ticket",
        "jira",
        "agendamento",
        "pendente",
        "reagendamento",
        "tecnico",
        "técnico",
        "branch",
        "monitoramento",
    ]

    if any(p in t for p in palavras_operacionais):
        return False

    return True

# ──────────────────────────────────────────
# RESPOSTAS CASUAIS
# ──────────────────────────────────────────

RESPOSTAS_CASUAIS = {
    "bom dia": [
        "Bom diaaa ☕ Bora pra mais um dia de luta kkkkk",
        "Bom dia 😄 Hoje promete...",
        "Bom dia! Café já tá rodando aí? 😂",
    ],

    "boa tarde": [
        "Boa tarde 😄",
        "Boa tarde! Sobrevivendo pós-almoço ainda 😂",
    ],

    "boa noite": [
        "Boa noite 🌙",
        "Boa noite! Finalmente sextou... ou quase 😅",
    ],

    "so bot veio trabalhar": [
        "Pelo visto só eu mesmo 😂 Bora acordar esse povo aí",
        "Tô carregando a operação nas costas hoje 😎",
        "O resto do time ainda tá inicializando o sistema kkkkk",
    ],

    "chovendo": [
        "Aqui no servidor segue clima de produção com 99 problemas 😅",
        "Chuva boa pra dormir... ruim pra operação 😂",
    ],
}

def gerar_resposta_casual(texto: str) -> str:
    t = texto.lower()

    if "bom dia" in t:
        return random.choice(RESPOSTAS_CASUAIS["bom dia"])

    if "boa tarde" in t:
        return random.choice(RESPOSTAS_CASUAIS["boa tarde"])

    if "boa noite" in t:
        return random.choice(RESPOSTAS_CASUAIS["boa noite"])

    if "só o bot veio trabalhar" in t or "so o bot veio trabalhar" in t:
        return random.choice(RESPOSTAS_CASUAIS["so bot veio trabalhar"])

    if "chuva" in t or "chovendo" in t:
        return random.choice(RESPOSTAS_CASUAIS["chovendo"])

    return gerar_resposta(texto)

# ──────────────────────────────────────────
# DATAS
# ──────────────────────────────────────────

def utc_para_brasilia(dt_str: str) -> datetime | None:
    if not dt_str:
        return None

    try:
        dt_utc = datetime.strptime(
            dt_str[:19],
            "%Y-%m-%dT%H:%M:%S"
        ).replace(tzinfo=timezone.utc)

        return dt_utc.astimezone(TZ_BRASILIA)

    except Exception:
        return None

def formatar_horario(dt_str: str) -> str:
    dt = utc_para_brasilia(dt_str)

    return dt.strftime("%H:%M") if dt else "N/D"

def formatar_data(dt_str: str) -> str:
    dt = utc_para_brasilia(dt_str)

    return dt.strftime("%d/%m/%Y") if dt else "N/D"

# ──────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────

def norm(s: str) -> str:
    import unicodedata

    s = s.lower().strip()
    s = unicodedata.normalize("NFD", s)

    return "".join(
        c for c in s
        if unicodedata.category(c) != "Mn"
    )

def nome_bate(busca: str, campo: str) -> bool:
    palavras = norm(busca).split()
    campo_n  = norm(campo)

    return all(p in campo_n for p in palavras)

def obter_nome_tecnico(fields: dict) -> str:
    raw = fields.get(CAMPO_TECNICO)

    if isinstance(raw, dict):
        return raw.get("value", "Não informado")

    if isinstance(raw, list) and raw:
        if isinstance(raw[0], dict):
            return raw[0].get("value", "Não informado")

        return str(raw[0])

    if isinstance(raw, str):
        return raw

    return "Não informado"

def obter_branch(fields: dict) -> str:
    raw = fields.get(CAMPO_BRANCH)

    if isinstance(raw, str):
        return raw

    if isinstance(raw, dict):
        return raw.get("value", "N/D")

    return "N/D"

# ──────────────────────────────────────────
# BUSCA CHAMADO ESPECÍFICO
# ──────────────────────────────────────────

def buscar_chamado(chave: str) -> str:

    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{chave}"

    resp = requests.get(
        url,
        auth=AUTH,
        headers=HEADERS,
        timeout=10,
    )

    if resp.status_code != 200:
        return f"Não encontrei o chamado {chave}"

    f = resp.json().get("fields", {})

    status_raw = f.get("status", {}).get("name", "N/D")

    assignee = f.get("assignee")

    operador = (
        assignee["displayName"]
        if assignee else
        "Sem responsável"
    )

    linhas = [
        f"Chamado: {chave}",
        f"Título: {f.get('summary', 'N/D')}",
        f"Status: {traduzir_status(status_raw)}",
        f"Técnico: {obter_nome_tecnico(f)}",
        f"Operador: {operador}",
        f"Branch: {obter_branch(f)}",
    ]

    return "\n".join(linhas)

# ──────────────────────────────────────────
# CONTEXTO JIRA
# ──────────────────────────────────────────

def buscar_contexto_jira(texto: str) -> str:

    chave = extrair_chave_chamado(texto)

    if chave:
        return buscar_chamado(chave)

    fields_q = (
        f"key,assignee,status,summary,"
        f"{CAMPO_TECNICO},"
        f"{CAMPO_BRANCH},"
        f"{CAMPO_AGENDAMENTO}"
    )

    issues = buscar_todas_issues(
        JQL_PENDENTES,
        fields_q
    )

    linhas = [
        f"Total de chamados pendentes: {len(issues)}"
    ]

    for issue in issues[:20]:

        f = issue["fields"]

        chave = issue["key"]

        status_raw = f.get(
            "status",
            {}
        ).get("name", "N/D")

        linhas.append(
            f"- {chave} | "
            f"{obter_nome_tecnico(f)} | "
            f"{obter_branch(f)} | "
            f"{traduzir_status(status_raw)}"
        )

    return "\n".join(linhas)

# ──────────────────────────────────────────
# SYSTEM PROMPT
# ──────────────────────────────────────────

SYSTEM_PROMPT = f"""
Você é o ZECA, assistente virtual do time de operações da Queonetics.

━━━━━━━━━━━━━━━━━━━━━━
PERSONALIDADE
━━━━━━━━━━━━━━━━━━━━━━

Você conversa como alguém do time.

Seu tom deve parecer:
- humano
- espontâneo
- leve
- engraçado quando fizer sentido
- natural em grupos corporativos

Você pode:
- brincar
- responder perguntas retóricas
- fazer comentários engraçados
- provocar amigavelmente
- reagir ao clima da conversa

NUNCA pareça um robô corporativo.

━━━━━━━━━━━━━━━━━━━━━━
MODO CASUAL
━━━━━━━━━━━━━━━━━━━━━━

Quando a conversa for casual:

- responda como um colega da empresa
- seja leve
- seja espontâneo
- use humor quando fizer sentido

Exemplos:

Usuário:
"Só o bot veio trabalhar hoje?"

ZECA:
"Pelo visto só eu mesmo 😂 Bora acordar esse povo aí"

Usuário:
"Bom dia"

ZECA:
"Bom diaaa ☕ Hoje promete..."

━━━━━━━━━━━━━━━━━━━━━━
MODO JIRA
━━━━━━━━━━━━━━━━━━━━━━

Quando houver:
- #jira
- #ticket
- #chamado
- chave Jira
- assunto operacional

Então:

- seja profissional
- seja preciso
- nunca invente dados
- use o contexto fornecido
- destaque reagendamentos

━━━━━━━━━━━━━━━━━━━━━━
REGRAS IMPORTANTES
━━━━━━━━━━━━━━━━━━━━━━

- Nunca invente chamados
- Nunca invente horários
- Nunca invente técnicos
- Nunca invente status

Hoje é {datetime.now(TZ_BRASILIA).strftime('%d/%m/%Y')}
"""

# ──────────────────────────────────────────
# IA
# ──────────────────────────────────────────

def truncar_contexto(
    contexto: str,
    limite_chars: int = 6000
) -> str:

    if len(contexto) <= limite_chars:
        return contexto

    linhas = contexto.split("\n")

    resultado = []
    total = 0

    for linha in linhas:

        if total + len(linha) > limite_chars:
            resultado.append(
                "... contexto truncado ..."
            )
            break

        resultado.append(linha)

        total += len(linha) + 1

    return "\n".join(resultado)

def gerar_resposta(
    pergunta: str,
    contexto_jira: str | None = None
) -> str:

    if contexto_jira:

        contexto_safe = truncar_contexto(
            contexto_jira
        )

        conteudo = (
            f"Dados do Jira:\n\n"
            f"{contexto_safe}\n\n"
            f"Pergunta: {pergunta}"
        )

    else:
        conteudo = pergunta

    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=600,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": conteudo
            },
        ],
    )

    return resp.choices[0].message.content.strip()

# ──────────────────────────────────────────
# ENTRADA PRINCIPAL
# ──────────────────────────────────────────

def processar_mensagem(
    texto: str,
    nome_usuario: str = ""
) -> str:

    texto = texto.strip()

    if not texto:
        return "Oi 😄"

    try:

        # CASUAL
        if eh_conversa_casual(texto):
            return gerar_resposta_casual(texto)

        # JIRA
        if eh_mensagem_jira(texto):

            contexto = buscar_contexto_jira(
                texto
            )

            return gerar_resposta(
                texto,
                contexto_jira=contexto
            )

        # FALLBACK
        return gerar_resposta(texto)

    except Exception as e:

        return (
            "⚠️ Deu ruim aqui no servidor 😅\n"
            f"{str(e)}"
        )