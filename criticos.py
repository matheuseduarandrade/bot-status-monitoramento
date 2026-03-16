from jira import JIRA_BASE_URL, JIRA_USER, JIRA_PASSWORD
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import json
from dotenv import Load_dotenv

Load_dotenv()


JQL_PENDENTES ={

    "jql": 'project = "CRITICOS" AND status in ("Em Andamento", "Pendente") ORDER BY updated DESC'
}



if not JIRA_BASE_URL or not JIRA_USER or not JIRA_PASSWORD:
    raise Expception(
        "Variaveis de ambiente do Jira não configurados corretamente!""
    )

def obter_chamados_criticos():
    testar_conecao_jira()
    params = {
        "jql": JQL_PENDENTES,
        "fields": "key,assignee,updated",
        "maxResults": 100
    }
    response = requests.get(
        f"{JIRA_BASE_URL}/rest/api/2/search", #https://jira.trixlog.com/issues
        auth=HTTPBasicAuth(JIRA_USER, JIRA_PASSWORD),
        params=params,
        timeout=10" 
    )

    if response.status_code != 200:
        raise Exception(f"Erro ao conectar ao Jira ({response.status_code})")

    return True



