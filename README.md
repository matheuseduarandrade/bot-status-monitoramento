# 🤖 Status Monitoramento — Bot Telegram Corporativo

Bot corporativo em **Python** para monitoramento operacional, integrado ao **Jira** e **Google Calendar**, com foco em visibilidade de chamados, agendas individuais e gestão administrativa via Telegram.

---

## 📌 Visão Geral

O **Status Monitoramento** foi criado para centralizar informações críticas do dia a dia operacional diretamente no Telegram, evitando acessos manuais a múltiplas ferramentas.

Ele permite que:

* Operadores vejam **apenas sua própria agenda**
* Gestores tenham **visão geral de chamados, agendas e status**
* O time acompanhe **chamados pendentes por responsável**, com tempo sem atualização

---

## 🚀 Funcionalidades

### 👤 Operador

* 📅 Visualizar **agenda do dia** (Google Calendar)
* Recebe apenas informações relacionadas ao seu usuário

### 👑 Administrador / Gestor

* 📊 **Status geral de chamados** no Jira
* 📋 **Chamados pendentes por responsável**

  * Quantidade
  * Chave do chamado (ex: MONITORAR-1234)
  * Data da última atualização
  * Dias sem movimentação
* 📅 Visualizar **agenda de toda a equipe**
* ⚙️ Acesso a configurações do sistema

---

## 🔗 Integrações

### Jira

* Consulta via **JQL**
* Autenticação Basic (usuário + token/senha)
* Projetos monitorados:

  * `MONITORAR`
  * `PROMONITOR`

### Google Calendar

* Uso de **Service Account**
* Acesso somente leitura
* Agendas individuais por e-mail corporativo

---

## 🧱 Estrutura do Projeto

```
BOT-TELEGRAM/
│
├── bot.py                 # Arquivo principal do bot
├── jira.py                # Integração com Jira
├── google_agenda.py       # Integração com Google Calendar
├── requirements.txt       # Dependências
├── .env                   # Variáveis de ambiente (NÃO versionar)
├── .env.example           # Exemplo de variáveis
├── .gitignore             # Arquivos ignorados pelo Git
├── credentials.json       # Credencial Google (NÃO versionar)
└── README.md
```

---

## 🔐 Segurança

✔️ Tokens e credenciais **NÃO ficam no código**
✔️ Uso de `.env` para secrets
✔️ `.gitignore` configurado para proteger dados sensíveis

Arquivos sensíveis ignorados:

* `.env`
* `credentials.json`
* `__pycache__/`

---

## ⚙️ Variáveis de Ambiente

Crie um arquivo `.env` baseado no `.env.example`:

```
JIRA_BASE_URL=https://seudominio.atlassian.net
JIRA_USER=seu_email@empresa.com
JIRA_PASSWORD=seu_token_ou_senha
TELEGRAM_BOT_TOKEN=seu_token_do_bot
```

---

## ▶️ Como Executar Localmente

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python bot.py
```

---

## 📌 Status do Projeto

🟢 Em produção local
🟡 Deploy 24/7 pendente
🟡 Sistema de alertas automáticos planejado

---

## 👨‍💻 Desenvolvedor

**Matheus Eduardo**
📧 [matheus.eduardo@queonetics.com](mailto:matheus.eduardo@queonetics.com)

---

> Projeto corporativo — uso interno
