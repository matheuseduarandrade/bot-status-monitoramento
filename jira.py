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
    """Testa se a autenticação com o Jira está funcionando"""
    
    response = requests.get(
        f"{JIRA_BASE_URL}/rest/api/2/myself",
        auth=HTTPBasicAuth(JIRA_USER, JIRA_PASSWORD),
        timeout=10
    )

    if response.status_code != 200:
        raise Exception("Usuário ou senha do Jira inválidos")

    return True


def obter_chamados_pendentes():
    """Retorna quantidade total de chamados pendentes"""

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
    """Retorna chamados agrupados por responsável"""

    testar_conexao_jira()

    params = {
        "jql": JQL_PENDENTES,
        "fields": f"key,assignee,updated,{CUSTOM_TECNICO_CAMPO}",
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
    chaves_processadas = set()  # evita duplicação

    for issue in issues:

        chave = issue["key"]

        if chave in chaves_processadas:
            continue

        chaves_processadas.add(chave)

        fields = issue["fields"]

        raw_tecnico = fields.get(CUSTOM_TECNICO_CAMPO)
        tecnico = "Não informado"

        if isinstance(raw_tecnico, dict):
            tecnico = raw_tecnico.get("value", "Não informado")

        elif isinstance(raw_tecnico, list) and raw_tecnico:
            item = raw_tecnico[0]
            if isinstance(item, dict):
                tecnico = item.get("value", "Não informado")

        elif isinstance(raw_tecnico, str):
            tecnico = raw_tecnico

        assignee = fields.get("assignee")
        responsavel = assignee["displayName"] if assignee else "Sem responsável"

        data_atualizacao = datetime.strptime(
            fields["updated"][:19],
            "%Y-%m-%dT%H:%M:%S"
        )

        dias_pendentes = (hoje - data_atualizacao).days

        chamado = {
            "chave": chave,
            "tecnico": tecnico,
            "atualizado_em": data_atualizacao.strftime("%d/%m/%Y"),
            "dias_pendentes": dias_pendentes
        }

        resultado.setdefault(responsavel, []).append(chamado)

    return resultado


def separar_pendencias(dados, somente_criticos=False):
    """
    Filtra chamados críticos.
    Críticos = mais de 2 dias sem atualização
    """

    resultado = {}

    for responsavel, chamados in dados.items():

        if somente_criticos:
            filtrados = [
                c for c in chamados
                if c["dias_pendentes"] >= 2
            ]
        else:
            filtrados = chamados

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

    response = requests.get(
        url,
        params={
            "jql": jql,
            "maxResults": 500
        },
        auth=HTTPBasicAuth(JIRA_USER, JIRA_PASSWORD),
        headers={"Accept": "application/json"}
    )

    data = response.json()

    return data.get("issues", [])
