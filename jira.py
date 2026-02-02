import requests
import os
from datetime import datetime
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_USER = os.getenv("JIRA_USER")
JIRA_PASSWORD = os.getenv("JIRA_PASSWORD")

JQL_PENDENTES = (
    'project IN (MONITORAR, PROMONITOR) '
    'AND status IN ('
    'Backlog, '
    '"Selected for Development", '
    '"Monitoramento - fazendo", '
    '"Aguardando assinatura da OS", '
    '"Fazendo - Monitoramento projetos"'
    ')'
)

def testar_conexao_jira():
    response = requests.get(
        f"{JIRA_BASE_URL}/rest/api/2/myself",
        auth=HTTPBasicAuth(JIRA_USER, JIRA_PASSWORD),
        timeout=10
    )

    if response.status_code != 200:
        raise Exception("Usuario ou senha do Jira invalidos")

    return True


def obter_chamados_pendentes():
    testar_conexao_jira()

    params = {
        "jql": JQL_PENDENTES,
        "maxResults": 0
    }

    response = requests.get(
        f"{JIRA_BASE_URL}/rest/api/2/search",
        auth=HTTPBasicAuth(JIRA_USER, JIRA_PASSWORD),
        params=params,
        timeout=10
    )

    if response.status_code != 200:
        raise Exception(f"Erro ao consultar Jira ({response.status_code})")

    dados = response.json()

    return {
        "total": dados.get("total", 0),
        "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
    }


def obter_chamados_pendentes_por_responsavel():
    testar_conexao_jira()

    params = {
        "jql": JQL_PENDENTES,
        "fields": "key,assignee,updated",
        "maxResults": 100
    }

    response = requests.get(
        f"{JIRA_BASE_URL}/rest/api/2/search",
        auth=HTTPBasicAuth(JIRA_USER, JIRA_PASSWORD),
        params=params,
        timeout=15
    )

    if response.status_code != 200:
        raise Exception(f"Erro ao consultar Jira ({response.status_code})")

    issues = response.json().get("issues", [])
    hoje = datetime.now()
    resultado = {}

    for issue in issues:
        fields = issue["fields"]
        assignee = fields.get("assignee")

        responsavel = assignee["displayName"] if assignee else "Sem responsável"

        data_atualizacao = datetime.strptime(
            fields["updated"][:19],
            "%Y-%m-%dT%H:%M:%S"
        )

        dias_pendentes = (hoje - data_atualizacao).days

        chamado = {
            "chave": issue["key"],
            "atualizado_em": data_atualizacao.strftime("%d/%m/%Y"),
            "dias_pendentes": dias_pendentes
        }

        resultado.setdefault(responsavel, []).append(chamado)

    return resultado
