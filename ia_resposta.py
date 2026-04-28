"""
ia_resposta.py - v6
System prompt completo com contexto real do Jira da Queonetics.
"""

import os
import re
import json
import requests
from groq import Groq
from datetime import datetime, timezone, timedelta
from jira import buscar_todas_issues, separar_pendencias, JQL_PENDENTES
from tecnicos import encontrar_tecnico
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

JIRA_BASE_URL     = os.getenv("JIRA_BASE_URL")
JIRA_USER         = os.getenv("JIRA_USER")
JIRA_PASSWORD     = os.getenv("JIRA_PASSWORD")
CAMPO_TECNICO     = os.getenv("JIRA_ID_TECNICO")
CAMPO_PROJETO     = os.getenv("JIRA_ID_PROJETO", "")
CAMPO_AGENDAMENTO = "customfield_10622"
CAMPO_BRANCH      = "customfield_15615"
CAMPO_PLACA       = "customfield_10900"  # ajuste se necessário

AUTH    = HTTPBasicAuth(JIRA_USER, JIRA_PASSWORD)
HEADERS = {"Accept": "application/json"}

TZ_BRASILIA = timezone(timedelta(hours=-3))


# ──────────────────────────────────────────
# OPERADORES CONHECIDOS
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
# CONVERSÃO DE DATAS
# ──────────────────────────────────────────

def utc_para_brasilia(dt_str: str) -> datetime | None:
    if not dt_str:
        return None
    try:
        dt_utc = datetime.strptime(dt_str[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
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
# MAPEAMENTO DE STATUS
# ──────────────────────────────────────────

STATUS_DESCRICAO = {
    "sem reagendamento":                "✅ Concluído",
    "com reagendamento":                "🔄 Concluído com reagendamento — nova data necessária",
    "a fazer - monitoramento projetos": "🕐 Não iniciado",
    "monitoramento - a fazer":          "🕐 Não iniciado",
    "monitoramento - fazendo":          "🔧 Em andamento",
    "monitorameto - fazendo":           "🔧 Em andamento",
    "aguardando assinatura da os":      "⏳ Aguardando assinatura da OS",
    "fazendo - monitoramento projetos": "🔧 Em andamento",
    "selected for development":         "⏳ Pendente de encerramento",
    "backlog":                          "🕐 Não iniciado",
}

STATUS_ENCERRAMENTO = {"aguardando assinatura da os", "selected for development"}

def traduzir_status(s: str) -> str:
    return STATUS_DESCRICAO.get(s.strip().lower(), s)

def eh_reagendamento(s: str) -> bool:
    return s.strip().lower() == "com reagendamento"

def eh_encerramento(s: str) -> bool:
    return s.strip().lower() in STATUS_ENCERRAMENTO

FILTRO_PARA_STATUS = {
    "encerramento":  STATUS_ENCERRAMENTO,
    "nao_iniciado":  {"a fazer - monitoramento projetos", "monitoramento - a fazer", "backlog"},
    "andamento":     {"monitoramento - fazendo", "monitorameto - fazendo", "fazendo - monitoramento projetos"},
    "reagendamento": {"com reagendamento"},
    "concluido":     {"sem reagendamento", "com reagendamento"},
}


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
# EXTRAÇÃO DE FILTROS VIA IA
# ──────────────────────────────────────────

def extrair_filtros_ia(texto: str) -> dict:
    prompt = f"""
Você é um assistente que extrai filtros de consultas sobre chamados do Jira de uma empresa de monitoramento veicular.

Estrutura dos chamados:
- "técnico em campo": profissional que vai fisicamente ao cliente realizar o serviço
- "responsável/operador": pessoa do monitoramento que gerencia o chamado (ex: Lucas Paixão, Pedro Miguel, Eduardo Andrade, Lucas Dias, Felipe Silva, Diego Oliveira, Rene Filho, M. Vinicius)
- "branch": filial/localização do cliente (ex: "Femsa - Santa Maria RS", "Solar BR - Caruaru PE")
- "projeto": nome do projeto (ex: "Input Solar", "Upgrade Rotograma Femsa 360")

Extraia do texto:
1. "tecnico": nome do técnico em campo (se mencionado)
2. "operador": nome do operador/responsável (se mencionado)  
3. "branch": filial ou cliente (se mencionado)
4. "projeto": nome do projeto (se mencionado)
5. "status_filtro": 
   "encerramento" | "nao_iniciado" | "andamento" | "reagendamento" | "concluido" | null
6. "tempo":
   "hoje" | "semana_passada" | "essa_semana" | null
7. "ambiguo": true se o nome mencionado pode ser tanto técnico quanto operador (ex: "Lucas" pode ser Lucas Paixão operador ou Lucas técnico), false caso contrário

Responda APENAS JSON puro:
{{"tecnico": null, "operador": null, "branch": null, "projeto": null, "status_filtro": null, "tempo": null, "ambiguo": false}}

Texto: {texto}
"""
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.choices[0].message.content.strip()
    try:
        raw = re.sub(r"```.*?```", "", raw, flags=re.DOTALL).strip()
        return json.loads(raw)
    except Exception:
        return {"tecnico": None, "operador": None, "branch": None,
                "projeto": None, "status_filtro": None, "tempo": None, "ambiguo": False}


# ──────────────────────────────────────────
# HELPERS DE FILTRO
# ──────────────────────────────────────────

def norm(s: str) -> str:
    import unicodedata
    s = s.lower().strip()
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn")

def nome_bate(busca: str, campo: str) -> bool:
    palavras = norm(busca).split()
    campo_n  = norm(campo)
    return all(p in campo_n for p in palavras)

def obter_nome_tecnico(fields: dict) -> str:
    raw = fields.get(CAMPO_TECNICO)
    if isinstance(raw, dict):   return raw.get("value", "Não informado")
    if isinstance(raw, list) and raw:
        return raw[0].get("value", "Não informado") if isinstance(raw[0], dict) else str(raw[0])
    if isinstance(raw, str):    return raw
    return "Não informado"

def obter_branch(fields: dict) -> str:
    raw = fields.get(CAMPO_BRANCH)
    if isinstance(raw, str):  return raw
    if isinstance(raw, dict): return raw.get("value", "N/D")
    return "N/D"

def filtrar_por_tecnico(issues: list, tecnico: str) -> list:
    if not tecnico: return issues
    nome_resolvido = encontrar_tecnico(tecnico) or tecnico
    return [i for i in issues
            if nome_bate(nome_resolvido, obter_nome_tecnico(i["fields"])) or
               nome_bate(nome_resolvido, (i["fields"].get("assignee") or {}).get("displayName", ""))]

def filtrar_por_operador(issues: list, operador: str) -> list:
    if not operador: return issues
    return [i for i in issues
            if nome_bate(operador, (i["fields"].get("assignee") or {}).get("displayName", ""))]

def filtrar_por_branch(issues: list, branch: str) -> list:
    if not branch: return issues
    return [i for i in issues if nome_bate(branch, obter_branch(i["fields"]))]

def filtrar_por_projeto(issues: list, projeto: str) -> list:
    if not projeto: return issues
    resultado = []
    for issue in issues:
        f           = issue["fields"]
        proj_key    = issue["key"].split("-")[0].lower()
        summary     = norm(f.get("summary") or "")
        proj_custom = ""
        if CAMPO_PROJETO:
            raw = f.get(CAMPO_PROJETO)
            proj_custom = norm(raw if isinstance(raw, str) else (raw or {}).get("value", ""))
        if norm(projeto) in proj_key or norm(projeto) in summary or norm(projeto) in proj_custom:
            resultado.append(issue)
    return resultado


# ──────────────────────────────────────────
# BUSCA DE CHAMADOS HOJE
# ──────────────────────────────────────────

def buscar_chamados_hoje(tecnico: str = "", operador: str = "", branch: str = "") -> str:
    jql = (
        'project IN (MONITORAR, PROMONITOR) '
        'AND "Agendamento" >= startOfDay() '
        'AND "Agendamento" <= endOfDay() '
        'ORDER BY "Agendamento" ASC'
    )
    fields_q = f"key,assignee,status,summary,{CAMPO_TECNICO},{CAMPO_AGENDAMENTO},{CAMPO_BRANCH}"

    issues = buscar_todas_issues(jql, fields_q)
    issues = filtrar_por_tecnico(issues, tecnico)
    issues = filtrar_por_operador(issues, operador)
    issues = filtrar_por_branch(issues, branch)

    hoje_fmt = datetime.now(TZ_BRASILIA).strftime("%d/%m/%Y")
    partes = []
    if tecnico:  partes.append(f"técnico '{tecnico}'")
    if operador: partes.append(f"operador '{operador}'")
    if branch:   partes.append(f"branch '{branch}'")
    desc = f" ({' | '.join(partes)})" if partes else ""

    linhas = [f"Chamados agendados para hoje ({hoje_fmt}){desc}: {len(issues)}"]

    por_tecnico: dict = {}
    for issue in issues:
        f        = issue["fields"]
        nome_tec = obter_nome_tecnico(f)
        horario  = formatar_horario(f.get(CAMPO_AGENDAMENTO, ""))
        branch_v = obter_branch(f)
        status_r = f.get("status", {}).get("name", "N/D")

        por_tecnico.setdefault(nome_tec, []).append({
            "chave":   issue["key"],
            "horario": horario,
            "branch":  branch_v,
            "status":  traduzir_status(status_r),
        })

    for tec, chamados in sorted(por_tecnico.items()):
        linhas.append(f"\n👤 {tec} — {len(chamados)} chamado(s)")
        for c in sorted(chamados, key=lambda x: x["horario"]):
            linhas.append(f"  - {c['chave']} | ⏰ {c['horario']} | 📍 {c['branch']} | {c['status']}")

    return "\n".join(linhas)


# ──────────────────────────────────────────
# BUSCA DE CONCLUÍDOS
# ──────────────────────────────────────────

def buscar_concluidos(tecnico: str = "", operador: str = "", tempo: str = "") -> str:
    hoje = datetime.now(TZ_BRASILIA)

    if tempo == "semana_passada":
        dias = hoje.weekday()
        seg  = hoje - timedelta(days=dias + 7)
        dom  = seg + timedelta(days=6)
        data_ini, data_fim = seg.strftime("%Y-%m-%d"), dom.strftime("%Y-%m-%d")
        periodo = f"semana passada ({seg.strftime('%d/%m')} a {dom.strftime('%d/%m/%Y')})"
    elif tempo == "essa_semana":
        seg  = hoje - timedelta(days=hoje.weekday())
        data_ini, data_fim = seg.strftime("%Y-%m-%d"), hoje.strftime("%Y-%m-%d")
        periodo = f"esta semana ({seg.strftime('%d/%m')} a {hoje.strftime('%d/%m/%Y')})"
    else:
        data_ini = (hoje - timedelta(days=7)).strftime("%Y-%m-%d")
        data_fim = hoje.strftime("%Y-%m-%d")
        periodo  = "últimos 7 dias"

    jql = (
        f'project IN (MONITORAR, PROMONITOR) '
        f'AND status = "Sem Reagendamento" '
        f'AND updated >= "{data_ini}" AND updated <= "{data_fim}" '
        f'ORDER BY updated DESC'
    )
    fields_q = f"key,assignee,updated,status,summary,{CAMPO_TECNICO}"
    issues   = buscar_todas_issues(jql, fields_q)
    issues   = filtrar_por_tecnico(issues, tecnico)
    issues   = filtrar_por_operador(issues, operador)

    partes = []
    if tecnico:  partes.append(f"técnico '{tecnico}'")
    if operador: partes.append(f"operador '{operador}'")
    desc = f" ({' | '.join(partes)})" if partes else ""

    linhas = [f"Chamados concluídos{desc} — {periodo}: {len(issues)}"]

    por_tecnico: dict = {}
    for issue in issues:
        f        = issue["fields"]
        nome_tec = obter_nome_tecnico(f)
        updated  = formatar_data(f.get("updated", ""))
        por_tecnico.setdefault(nome_tec, []).append({"chave": issue["key"], "data": updated})

    for tec, chamados in sorted(por_tecnico.items(), key=lambda x: -len(x[1])):
        linhas.append(f"\n👤 {tec} — {len(chamados)} concluído(s)")
        for c in chamados:
            linhas.append(f"  - {c['chave']} | {c['data']}")

    return "\n".join(linhas)


# ──────────────────────────────────────────
# BUSCA GERAL
# ──────────────────────────────────────────

def buscar_contexto_jira(texto: str) -> str:
    linhas = []

    # Chamado específico
    chave = extrair_chave_chamado(texto)
    if chave:
        url  = f"{JIRA_BASE_URL}/rest/api/2/issue/{chave}"
        resp = requests.get(url, auth=AUTH, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            f          = resp.json().get("fields", {})
            assignee   = f.get("assignee")
            status_raw = f.get("status", {}).get("name", "N/D")
            agend_raw  = f.get(CAMPO_AGENDAMENTO, "")
            branch_v   = obter_branch(f)
            tec        = obter_nome_tecnico(f)
            operador   = assignee["displayName"] if assignee else "Sem responsável"
            linhas += [
                f"Chamado: {chave}",
                f"Título: {f.get('summary', 'N/D')}",
                f"Status: {status_raw} → {traduzir_status(status_raw)}",
                f"Técnico em campo: {tec}",
                f"Operador responsável: {operador}",
                f"Branch: {branch_v}",
                f"Atualizado: {formatar_data(f.get('updated', ''))}",
            ]
            if agend_raw:
                linhas.append(f"Agendamento: {formatar_data(agend_raw)} às {formatar_horario(agend_raw)}")
            if eh_reagendamento(status_raw):
                linhas.append("⚠️ ATENÇÃO: chamado voltou para reagendamento — nova data necessária.")
        else:
            linhas.append(f"Chamado {chave} não encontrado.")
        return "\n".join(linhas)

    # Extrai filtros
    filtros       = extrair_filtros_ia(texto)
    tecnico       = (filtros.get("tecnico") or "").strip()
    operador      = (filtros.get("operador") or "").strip()
    branch        = (filtros.get("branch") or "").strip()
    projeto       = (filtros.get("projeto") or "").strip()
    status_filtro = filtros.get("status_filtro") or ""
    tempo         = filtros.get("tempo") or ""
    ambiguo       = filtros.get("ambiguo", False)

    # Nome ambíguo — pode ser técnico ou operador
    if ambiguo and tecnico and not operador:
        op_encontrado  = encontrar_operador(tecnico)
        tec_encontrado = encontrar_tecnico(tecnico)
        if op_encontrado and tec_encontrado:
            return (
                f"⚠️ O nome '{tecnico}' pode ser tanto um técnico em campo quanto um operador.\n"
                f"Pode especificar? Ex:\n"
                f"• '#jira chamados do {tecnico} técnico'\n"
                f"• '#jira chamados do {tecnico} operador'"
            )

    # Chamados de hoje
    if tempo == "hoje":
        return buscar_chamados_hoje(tecnico=tecnico, operador=operador, branch=branch)

    # Concluídos
    if status_filtro == "concluido":
        return buscar_concluidos(tecnico=tecnico, operador=operador, tempo=tempo)

    # Busca geral pendentes
    fields_q = f"key,assignee,updated,status,summary,{CAMPO_TECNICO},{CAMPO_BRANCH}"
    if CAMPO_PROJETO:
        fields_q += f",{CAMPO_PROJETO}"

    issues = buscar_todas_issues(JQL_PENDENTES, fields_q)

    if status_filtro and status_filtro in FILTRO_PARA_STATUS:
        issues = [i for i in issues
                  if norm(i["fields"].get("status", {}).get("name", "")) in FILTRO_PARA_STATUS[status_filtro]]

    issues = filtrar_por_tecnico(issues, tecnico)
    issues = filtrar_por_operador(issues, operador)
    issues = filtrar_por_branch(issues, branch)
    issues = filtrar_por_projeto(issues, projeto)

    if not issues:
        partes = []
        if tecnico:       partes.append(f"técnico '{tecnico}'")
        if operador:      partes.append(f"operador '{operador}'")
        if branch:        partes.append(f"branch '{branch}'")
        if projeto:       partes.append(f"projeto '{projeto}'")
        if status_filtro: partes.append(f"status '{status_filtro}'")
        linhas.append("Nenhum chamado pendente encontrado" +
                      (f" para {' e '.join(partes)}." if partes else "."))
        return "\n".join(linhas)

    partes = []
    if tecnico:       partes.append(f"técnico '{tecnico}'")
    if operador:      partes.append(f"operador '{operador}'")
    if branch:        partes.append(f"branch '{branch}'")
    if projeto:       partes.append(f"projeto '{projeto}'")
    if status_filtro: partes.append(f"status '{status_filtro}'")
    desc = f" ({' | '.join(partes)})" if partes else ""
    linhas.append(f"Total de chamados pendentes{desc}: {len(issues)}")

    hoje      = datetime.now(TZ_BRASILIA)
    reagend   = 0
    encerram  = 0

    for issue in issues:
        f          = issue["fields"]
        chave      = issue["key"]
        status_raw = f.get("status", {}).get("name", "N/D")
        updated    = f.get("updated", "")[:10]
        branch_v   = obter_branch(f)
        tec        = obter_nome_tecnico(f)
        try:
            dias = (hoje.date() - datetime.strptime(updated, "%Y-%m-%d").date()).days
        except Exception:
            dias = "?"

        tags = ""
        if eh_reagendamento(status_raw):
            reagend += 1
            tags += " ⚠️ REAGENDAMENTO"
        if eh_encerramento(status_raw):
            encerram += 1

        linhas.append(
            f"  - {chave} | {tec} | {branch_v} | {dias} dias | {traduzir_status(status_raw)}{tags}"
        )

    if reagend:   linhas.insert(1, f"  ↳ Com reagendamento: {reagend}")
    if encerram and not status_filtro:
        linhas.insert(1, f"  ↳ Pendentes de encerramento: {encerram}")

    return "\n".join(linhas)


# ──────────────────────────────────────────
# SYSTEM PROMPT COMPLETO
# ──────────────────────────────────────────

SYSTEM_PROMPT = f"""
Você é o ZECA, assistente virtual do time de monitoramento da Queonetics.
Responda sempre em português do Brasil, de forma educada, direta e objetiva.
Use no máximo 1-2 emojis por mensagem. NUNCA invente dados.
Hoje é {datetime.now(TZ_BRASILIA).strftime('%d/%m/%Y')} — horário de Brasília (UTC-3).

━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTO DO SISTEMA
━━━━━━━━━━━━━━━━━━━━━━━━
A Queonetics é uma empresa de monitoramento veicular. Os chamados no Jira representam
atendimentos técnicos realizados em veículos de clientes (frotas).

PROJETOS:
- PROMONITOR: chamados de projetos (ex: Upgrade Rotograma Femsa 360°, Input Solar)
- MONITORAR: chamados de monitoramento geral

CAMPOS PRINCIPAIS:
- "Técnico em campo": profissional que vai fisicamente ao cliente realizar o serviço (ex: Anderson Fernandes de Amorim, Wallace Vitor Ferreira Silva)
- "Responsável/Operador": pessoa do time de monitoramento que gerencia o chamado
- "Branch via Argos": filial/localização do cliente (ex: "Femsa - Santa Maria RS", "Solar BR - Caruaru PE")
- "Agendamento": data e hora marcada para o atendimento (já convertida para horário de Brasília)
- "Placas": placa do veículo a ser atendido
- "Tipo de serviço": o que será feito (ex: Telemetria Can + Rotograma + Autenticação)
- "Tipo de requisição": Intervenção Física, Desinstalação/Aditivo, Atualização de Tecnologia

OPERADORES DO MONITORAMENTO:
Rene Filho, Eduardo Andrade, Lucas Paixão, Lucas Dias, Pedro Miguel, Diego Oliveira, Felipe Silva, M. Vinicius (Marcos Vinicius)

STATUS DOS CHAMADOS:
- "Monitoramento - A Fazer" / "A Fazer - Monitoramento Projetos" / "Backlog" → 🕐 Não iniciado
- "Monitoramento - Fazendo" / "Fazendo - Monitoramento Projetos" → 🔧 Em andamento
- "Aguardando Assinatura da OS" → ⏳ Aguardando assinatura da OS (pendente de encerramento)
- "Selected for Development" → ⏳ Pendente de encerramento
- "Sem Reagendamento" → ✅ Concluído
- "Com Reagendamento" → 🔄 Concluído mas voltou para reagendar nova data (SEMPRE destaque!)

━━━━━━━━━━━━━━━━━━━━━━━━
REGRAS DE RESPOSTA
━━━━━━━━━━━━━━━━━━━━━━━━
1. NUNCA invente chamados, técnicos, horários ou dados. Se não tiver no contexto do Jira fornecido, diga que não encontrou.
2. Se os dados do Jira foram fornecidos no contexto, use-os fielmente para responder.
3. Se não houver dados do Jira no contexto, oriente o usuário a usar #jira na pergunta.
4. Quando listar chamados do dia, agrupe por técnico e mostre horário do agendamento e branch.
5. Quando um chamado tiver status "Com Reagendamento", sempre destaque isso.
6. "Lucas" pode ser o operador Lucas Paixão/Lucas Dias ou um técnico — se ambíguo, pergunte.
7. Seja breve. Não repita informações desnecessariamente.
"""


# ──────────────────────────────────────────
# GERAÇÃO DE RESPOSTA
# ──────────────────────────────────────────

def truncar_contexto(contexto: str, limite_chars: int = 6000) -> str:
    """Limita o contexto para evitar rate limit do Groq."""
    if len(contexto) <= limite_chars:
        return contexto
    linhas = contexto.split("\n")
    resultado = []
    total = 0
    for linha in linhas:
        if total + len(linha) > limite_chars:
            resultado.append("  ... (lista truncada — mostre apenas os totais acima)")
            break
        resultado.append(linha)
        total += len(linha) + 1
    return "\n".join(resultado)


def gerar_resposta(pergunta: str, contexto_jira: str | None = None) -> str:
    if contexto_jira:
        contexto_safe = truncar_contexto(contexto_jira)
        conteudo = f"Dados do Jira:\n\n{contexto_safe}\n\nPergunta: {pergunta}"
    else:
        conteudo = pergunta
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=800,
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
