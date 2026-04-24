"""
ia_resposta.py - v2
Groq + Jira com suporte a nomes compostos, filtro por projeto e técnico em campo.
"""

import os
import re
import requests
from groq import Groq
from jira import separar_pendencias
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

JIRA_BASE_URL  = os.getenv("JIRA_BASE_URL")
JIRA_USER      = os.getenv("JIRA_USER")
JIRA_PASSWORD  = os.getenv("JIRA_PASSWORD")
CAMPO_TECNICO  = os.getenv("JIRA_ID_TECNICO")          # ex: customfield_XXXXX
CAMPO_PROJETO  = os.getenv("JIRA_ID_PROJETO", "")      # ex: customfield_YYYYY  (se tiver)

AUTH = HTTPBasicAuth(JIRA_USER, JIRA_PASSWORD)
HEADERS = {"Accept": "application/json"}

# ──────────────────────────────────────────
# MAPEAMENTO DE STATUS
# ──────────────────────────────────────────

STATUS_DESCRICAO = {
    "sem reagendamento":                "✅ Concluído",
    "com reagendamento":                "🔄 Concluído — voltou para reagendar nova data",
    "a fazer - monitoramento projetos": "🕐 Não iniciado",
    "monitoramento - a fazer":          "🕐 Não iniciado",
    "monitoramento - fazendo":          "🔧 Em andamento/encerramento",
    "monitorameto - fazendo":           "🔧 Em andamento/encerramento",
    "aguardando assinatura da os":      "⏳ Pendente de informações/encerramento",
    "fazendo - monitoramento projetos": "🔧 Em andamento",
    "selected for development":         "⏳ Pendente de informações/encerramento",
    "backlog":                          "🕐 Não iniciado",
}

def traduzir_status(s: str) -> str:
    return STATUS_DESCRICAO.get(s.strip().lower(), s)

def eh_reagendamento(s: str) -> bool:
    return s.strip().lower() == "com reagendamento"

# ──────────────────────────────────────────
# DETECÇÃO DE INTENÇÃO
# ──────────────────────────────────────────

GATILHOS_JIRA = {"#jira", "#chamado", "#ticket"}

def eh_mensagem_jira(texto: str) -> bool:
    return any(g in texto.lower() for g in GATILHOS_JIRA)

def extrair_chave_chamado(texto: str) -> str | None:
    m = re.search(r"\b([A-Z][A-Z0-9]+-\d+)\b", texto)
    return m.group(1) if m else None

# ──────────────────────────────────────────
# EXTRAÇÃO INTELIGENTE VIA IA
# ──────────────────────────────────────────

def extrair_filtros_ia(texto: str) -> dict:
    """
    Usa a IA para extrair filtros da pergunta: nome do técnico e projeto.
    Retorna dict com chaves 'tecnico' e 'projeto' (podem ser None).
    """
    prompt = f"""
Extraia do texto abaixo:
1. O nome completo do técnico (se mencionado) — pode ser composto como "Marcos José de Oliveira"
2. O nome do projeto (se mencionado) — ex: "Input Solar", "PROMONITOR", "MONITORAR"

Responda APENAS em JSON, sem explicações, sem markdown. Exemplo:
{{"tecnico": "Marcos José de Oliveira", "projeto": "Input Solar"}}

Se não encontrar um dos campos, use null.

Texto: {texto}
"""
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=100,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.choices[0].message.content.strip()
    try:
        import json
        # remove possíveis backticks
        raw = re.sub(r"```.*?```", "", raw, flags=re.DOTALL).strip()
        return json.loads(raw)
    except Exception:
        return {"tecnico": None, "projeto": None}

# ──────────────────────────────────────────
# BUSCA NO JIRA
# ──────────────────────────────────────────

JQL_BASE = (
    'project IN (MONITORAR, PROMONITOR) '
    'AND status IN ('
    '"Backlog", '
    '"Selected for Development", '
    '"Monitoramento - fazendo", '
    '"Aguardando assinatura da OS", '
    '"Fazendo - Monitoramento projetos", '
    '"A FAZER - MONITORAMENTO PROJETOS", '
    '"MONITORAMENTO - A FAZER"'
    ')'
)

def buscar_jira_raw(jql: str, fields: str, max_results: int = 200) -> list:
    resp = requests.get(
        f"{JIRA_BASE_URL}/rest/api/2/search",
        auth=AUTH,
        headers=HEADERS,
        params={"jql": jql, "fields": fields, "maxResults": max_results},
        timeout=15,
    )
    if resp.status_code != 200:
        raise Exception(f"Erro Jira ({resp.status_code}): {resp.text[:200]}")
    return resp.json().get("issues", [])


def buscar_contexto_jira(texto: str) -> str:
    linhas = []

    # ── Chamado específico ──
    chave = extrair_chave_chamado(texto)
    if chave:
        url = f"{JIRA_BASE_URL}/rest/api/2/issue/{chave}"
        resp = requests.get(url, auth=AUTH, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            fields = resp.json().get("fields", {})
            assignee = fields.get("assignee")
            status_raw = fields.get("status", {}).get("name", "N/D")
            linhas.append(f"Chamado: {chave}")
            linhas.append(f"Título: {fields.get('summary', 'N/D')}")
            linhas.append(f"Status: {status_raw} → {traduzir_status(status_raw)}")
            linhas.append(f"Responsável: {assignee['displayName'] if assignee else 'Sem responsável'}")
            linhas.append(f"Última atualização: {fields.get('updated', '')[:10]}")
            if eh_reagendamento(status_raw):
                linhas.append("⚠️ ATENÇÃO: chamado voltou para reagendamento de nova data.")
        else:
            linhas.append(f"Chamado {chave} não encontrado.")
        return "\n".join(linhas)

    # ── Extrai filtros via IA ──
    filtros = extrair_filtros_ia(texto)
    tecnico  = (filtros.get("tecnico") or "").strip()
    projeto  = (filtros.get("projeto") or "").strip()

    # Monta fields a buscar
    fields_query = f"key,assignee,updated,status,summary,{CAMPO_TECNICO}"
    if CAMPO_PROJETO:
        fields_query += f",{CAMPO_PROJETO}"

    issues = buscar_jira_raw(JQL_BASE, fields_query)

    # ── Filtra por técnico e/ou projeto ──
    def normalizar(s: str) -> str:
        return s.lower().strip()

    resultado = []
    for issue in issues:
        f = issue["fields"]

        # Filtro por técnico em campo (campo customizado)
        if tecnico:
            raw_tec = f.get(CAMPO_TECNICO)
            nome_tec = ""
            if isinstance(raw_tec, dict):
                nome_tec = raw_tec.get("value", "")
            elif isinstance(raw_tec, list) and raw_tec:
                nome_tec = raw_tec[0].get("value", "") if isinstance(raw_tec[0], dict) else str(raw_tec[0])
            elif isinstance(raw_tec, str):
                nome_tec = raw_tec

            # Também verifica no assignee como fallback
            assignee_nome = ""
            if f.get("assignee"):
                assignee_nome = f["assignee"].get("displayName", "")

            tec_encontrado = (
                normalizar(tecnico) in normalizar(nome_tec) or
                normalizar(tecnico) in normalizar(assignee_nome)
            )
            if not tec_encontrado:
                continue

        # Filtro por projeto (nome do projeto ou campo customizado)
        if projeto:
            proj_key = issue["key"].split("-")[0].lower()
            summary  = (f.get("summary") or "").lower()
            proj_custom = ""
            if CAMPO_PROJETO:
                raw_proj = f.get(CAMPO_PROJETO)
                if isinstance(raw_proj, str):
                    proj_custom = raw_proj.lower()
                elif isinstance(raw_proj, dict):
                    proj_custom = raw_proj.get("value", "").lower()

            proj_encontrado = (
                normalizar(projeto) in proj_key or
                normalizar(projeto) in summary or
                normalizar(projeto) in proj_custom
            )
            if not proj_encontrado:
                continue

        resultado.append(issue)

    # ── Monta contexto ──
    if not resultado:
        filtro_desc = []
        if tecnico:
            filtro_desc.append(f"técnico '{tecnico}'")
        if projeto:
            filtro_desc.append(f"projeto '{projeto}'")
        linhas.append(
            f"Nenhum chamado pendente encontrado"
            + (f" para {' e '.join(filtro_desc)}." if filtro_desc else ".")
        )
        return "\n".join(linhas)

    filtro_desc = []
    if tecnico:
        filtro_desc.append(f"técnico '{tecnico}'")
    if projeto:
        filtro_desc.append(f"projeto '{projeto}'")

    desc = f" ({' | '.join(filtro_desc)})" if filtro_desc else ""
    linhas.append(f"Total de chamados pendentes{desc}: {len(resultado)}")

    reagendamentos = 0
    from datetime import datetime
    hoje = datetime.now()

    for issue in resultado:
        f       = issue["fields"]
        chave   = issue["key"]
        status_raw = f.get("status", {}).get("name", "N/D")
        status_desc = traduzir_status(status_raw)
        updated = f.get("updated", "")[:10]
        dias    = (hoje - datetime.strptime(updated, "%Y-%m-%d")).days if updated else "?"
        reagend = ""
        if eh_reagendamento(status_raw):
            reagendamentos += 1
            reagend = " ⚠️ REAGENDAMENTO"

        linhas.append(
            f"  - {chave} | {updated} | {dias} dias | {status_desc}{reagend}"
        )

    if reagendamentos:
        linhas.insert(1, f"  ↳ Com reagendamento: {reagendamentos}")

    return "\n".join(linhas)

# ──────────────────────────────────────────
# GERAÇÃO DE RESPOSTA
# ──────────────────────────────────────────

SYSTEM_PROMPT = """
Você é o ZECA, assistente de monitoramento da equipe de TI.
Responda sempre em português do Brasil, de forma educada, direta e objetiva.
Use no máximo 1-2 emojis por mensagem. Nunca invente dados.
Organize listas com bullets. Seja breve.

Status dos chamados:
- Sem Reagendamento → Concluído
- Com Reagendamento → Concluído, mas voltou para reagendar nova data (SEMPRE destaque!)
- A Fazer / Monitoramento - A Fazer → Não iniciado
- Monitoramento - Fazendo / Fazendo - Monitoramento Projetos → Em andamento
- Aguardando Assinatura da OS / Selected for Development → Pendente de informações
"""

def gerar_resposta(pergunta: str, contexto_jira: str | None = None) -> str:
    conteudo = (
        f"Dados do Jira:\n\n{contexto_jira}\n\nResponda: {pergunta}"
        if contexto_jira else pergunta
    )
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=600,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": conteudo},
        ],
    )
    return resp.choices[0].message.content.strip()

# ──────────────────────────────────────────
# PONTO DE ENTRADA
# ──────────────────────────────────────────

def processar_mensagem(texto: str, nome_usuario: str = "") -> str:
    texto = texto.strip()
    if not texto:
        return "Oi! Pode perguntar 😊"
    try:
        if eh_mensagem_jira(texto):
            contexto = buscar_contexto_jira(texto)
            return gerar_resposta(texto, contexto_jira=contexto)
        else:
            return gerar_resposta(texto)
    except Exception as e:
        return f"⚠️ Erro ao processar sua mensagem:\n`{str(e)}`"
