import requests
import os
from datetime import datetime
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_USER = os.getenv("JIRA_USER")
JIRA_PASSWORD = os.getenv("JIRA_PASSWORD")
CUSTOM_TECNICO_CAMPO = os.getenv("JIRA_ID_TECNICO")

AUTH = HTTPBasicAuth(JIRA_USER, JIRA_PASSWORD)
HEADERS = {"Accept": "application/json"}

JQL_PENDENTES = (
    'project IN (MONITORAR, PROMONITOR) '
    'AND status IN ('
    '"Backlog", '
    '"Selected for Development", '
    '"Monitoramento - fazendo", '
    '"Aguardando assinatura da OS", '
    '"Fazendo - Monitoramento projetos", '
    '"A FAZER - MONITORAMENTO PROJETOS", '
    '"MONITORAMENTO - A FAZER"'
    ') ORDER BY updated DESC'
)


def testar_conexao_jira():
    response = requests.get(
        f"{JIRA_BASE_URL}/rest/api/2/myself",
        auth=AUTH,
        timeout=10
    )
    if response.status_code != 200:
        raise Exception("Usuário ou senha do Jira inválidos")
    return True


def buscar_todas_issues(jql: str, fields: str) -> list:
    """Busca TODAS as issues com paginação automática."""
    todas = []
    start = 0
    page_size = 100

    while True:
        resp = requests.get(
            f"{JIRA_BASE_URL}/rest/api/2/search",
            auth=AUTH,
            headers=HEADERS,
            params={
                "jql": jql,
                "fields": fields,
                "maxResults": page_size,
                "startAt": start,
            },
            timeout=20,
        )
        if resp.status_code != 200:
            raise Exception(f"Erro ao consultar Jira ({resp.status_code})")

        data = resp.json()
        issues = data.get("issues", [])
        todas.extend(issues)

        total = data.get("total", 0)
        start += len(issues)

        if start >= total or not issues:
            break

    return todas


def obter_chamados_pendentes():
    """Retorna quantidade total de chamados pendentes."""
    testar_conexao_jira()
    resp = requests.get(
        f"{JIRA_BASE_URL}/rest/api/2/search",
        auth=AUTH,
        params={"jql": JQL_PENDENTES, "maxResults": 0},
        timeout=10,
    )
    if resp.status_code != 200:
        raise Exception(f"Erro ao consultar Jira ({resp.status_code})")

    return {
        "total": resp.json().get("total", 0),
        "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }


def obter_chamados_pendentes_por_responsavel():
    """Retorna chamados agrupados por responsável, com paginação."""
    testar_conexao_jira()

    fields = f"key,assignee,updated,status,{CUSTOM_TECNICO_CAMPO}"
    issues = buscar_todas_issues(JQL_PENDENTES, fields)

    hoje = datetime.now()
    resultado = {}
    chaves_processadas = set()

    for issue in issues:
        chave = issue["key"]
        if chave in chaves_processadas:
            continue
        chaves_processadas.add(chave)

        fields_data = issue["fields"]

        # Técnico em campo (customfield)
        raw_tecnico = fields_data.get(CUSTOM_TECNICO_CAMPO)
        tecnico = "Não informado"
        if isinstance(raw_tecnico, dict):
            tecnico = raw_tecnico.get("value", "Não informado")
        elif isinstance(raw_tecnico, list) and raw_tecnico:
            item = raw_tecnico[0]
            tecnico = item.get("value", "Não informado") if isinstance(item, dict) else str(item)
        elif isinstance(raw_tecnico, str):
            tecnico = raw_tecnico

        assignee = fields_data.get("assignee")
        responsavel = assignee["displayName"] if assignee else "Sem responsável"

        status = fields_data.get("status", {}).get("name", "N/D")

        data_atualizacao = datetime.strptime(
            fields_data["updated"][:19], "%Y-%m-%dT%H:%M:%S"
        )
        dias_pendentes = (hoje - data_atualizacao).days

        chamado = {
            "chave": chave,
            "tecnico": tecnico,
            "status": status,
            "atualizado_em": data_atualizacao.strftime("%d/%m/%Y"),
            "dias_pendentes": dias_pendentes,
        }

        resultado.setdefault(responsavel, []).append(chamado)

    return resultado


def separar_pendencias(dados, somente_criticos=False):
    """Filtra chamados críticos (2+ dias sem atualização)."""
    resultado = {}
    for responsavel, chamados in dados.items():
        filtrados = (
            [c for c in chamados if c["dias_pendentes"] >= 2]
            if somente_criticos
            else chamados
        )
        if filtrados:
            resultado[responsavel] = filtrados
    return resultado


def buscar_agendamentos_hoje():
    url = f"{JIRA_BASE_URL}/rest/api/2/search"
    jql = """
    project in (PROMONITOR, MONITORAR)
    AND status in ("MONITORAMENTO - A FAZER", "A FAZER - MONITORAMENTO PROJETOS")
    AND "Agendamento" IS NOT EMPTY
    AND "Agendamento" >= startOfDay()
    AND "Agendamento" <= endOfDay()
    ORDER BY "Agendamento" ASC
    """
    resp = requests.get(
        url,
        params={"jql": jql, "maxResults": 500},
        auth=AUTH,
        headers=HEADERS,
    )
    return resp.json().get("issues", [])


def obter_chamados_atrasados():
    url = f"{JIRA_BASE_URL}/rest/api/2/search"
    jql = """
    project in (PROMONITOR, MONITORAR)
    AND status in ("MONITORAMENTO - A FAZER", "A FAZER - MONITORAMENTO PROJETOS")
    AND "Agendamento" IS NOT EMPTY
    ORDER BY "Agendamento" ASC
    """
    resp = requests.get(
        url,
        params={
            "jql": jql,
            "maxResults": 500,
            "fields": "key,summary,customfield_10622,customfield_15615,assignee",
        },
        auth=AUTH,
        headers=HEADERS,
    )
    if resp.status_code != 200:
        raise Exception(f"Erro ao buscar atrasados: {resp.status_code}")

    issues = resp.json().get("issues", [])
    hoje = datetime.now().date()
    atrasados_hoje = []
    atrasados_anteriores = []

    for issue in issues:
        fields = issue["fields"]
        agendamento_raw = fields.get("customfield_10622")
        if not agendamento_raw:
            continue
        try:
            data_agendada = datetime.strptime(
                agendamento_raw[:19], "%Y-%m-%dT%H:%M:%S"
            ).date()
        except Exception:
            continue

        item = {
            "key": issue["key"],
            "data": data_agendada.strftime("%d/%m/%Y"),
            "cliente": fields.get("customfield_15615", "N/D"),
            "link": f"{JIRA_BASE_URL}/browse/{issue['key']}",
        }

        if data_agendada == hoje:
            atrasados_hoje.append(item)
        elif data_agendada < hoje:
            atrasados_anteriores.append(item)

    return {"hoje": atrasados_hoje, "anteriores": atrasados_anteriores}
