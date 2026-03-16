# 🤖 Status Monitoramento — Bot Telegram Corporativo

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue)
![Jira](https://img.shields.io/badge/Jira-Integration-0052CC)
![Google Calendar](https://img.shields.io/badge/Google-Calendar-red)
![Status](https://img.shields.io/badge/Status-Active%20Development-green)

Bot corporativo desenvolvido em **Python** para monitoramento operacional, integrado ao **Jira** e **Google Calendar**, com foco em **visibilidade de chamados, agendas individuais e gestão administrativa diretamente no Telegram**.

---

## 📌 Visão Geral

O **Status Monitoramento** centraliza informações críticas do dia a dia operacional diretamente no **Telegram**, eliminando a necessidade de acessar múltiplos sistemas manualmente.

Com ele é possível:

* 📊 Consultar **status de chamados no Jira**
* 📅 Visualizar **agenda individual ou da equipe**
* ⏱️ Monitorar **tempo sem atualização de chamados**
* 🔔 Receber **alertas automáticos de agendamentos**
* ⚙️ Gerenciar informações operacionais via bot

---

## 🚀 Funcionalidades

### 👤 Operador
* 📅 Visualizar **agenda do dia**
* 🔔 Receber **alertas automáticos de agendamentos**
* Acesso apenas às informações relacionadas ao seu usuário

### 👑 Administrador / Gestor

#### 📊 Status Geral de Chamados
Consulta consolidada dos chamados nos projetos monitorados do **Jira**.

#### 📋 Chamados Pendentes por Responsável
O bot exibe:
* Quantidade de chamados
* Chave do chamado (`MONITORAR-1234`)
* Data da última atualização
* Dias sem movimentação

> [!TIP]
> Isso permite identificar rapidamente **chamados parados ou sem atualização**.

#### 📅 Agenda da Equipe
Gestores podem visualizar:
* Agenda individual
* Agenda consolidada da equipe

#### 🔔 Alertas Automáticos de Agendamentos
O bot monitora o **Google Calendar** e envia alertas automáticos no Telegram.

**Exemplo:**
> ⚠️ **AGENDAMENTO HOJE**
> **Responsável:** João
> **Cliente:** Empresa X
> **Horário:** 14:00

---

## 🔗 Integrações

### Jira
Consulta de chamados utilizando **JQL**.
* **Autenticação:** Basic Auth (Usuário + Token/Senha)
* **Projetos monitorados:** `MONITORAR`, `PROMONITOR`

### Google Calendar
Integração via **Service Account**.
* **Permissões:** Acesso somente leitura
* **Consulta:** Agendas individuais por e-mail corporativo

---

## 🏗️ Arquitetura do Sistema



```text
             ┌──────────────────┐
             │    Telegram      │
             │      Bot         │
             └─────────┬────────┘
                       │
                       │
                ┌──────▼──────┐
                │   bot.py    │
                │ (Controller)│
                └──────┬──────┘
                       │
        ┌──────────────┼──────────────┐
        │                              │
 ┌──────▼──────┐               ┌──────▼──────┐
 │   jira.py   │               │google_agenda│
 │ Integração  │               │     .py     │
 │   Jira API  │               │Google API   │
 └──────┬──────┘               └──────┬──────┘
        │                              │
  ┌─────▼─────┐                ┌──────▼─────┐
  │   Jira    │                │ Google     │
  │  Cloud    │                │ Calendar   │
  └───────────┘                └────────────┘

            ┌─────────────────────┐
            │ alerta_agendamentos │
            │      .py            │
            │ Monitoramento       │
            │ automático          │
            └─────────────────────┘
```

🧱 Estrutura do Projeto
```
BOT-TELEGRAM/
│
├── bot.py
├── jira.py
├── google_agenda.py
├── alerta_agendamentos.py
│
├── requirements.txt
│
├── .env
├── .env.example
│
├── .gitignore
├── credentials.json
│
└── README.md
```
🔐 Segurança
Boas práticas aplicadas:

✔️ Credenciais não ficam no código

✔️ Uso de variáveis de ambiente (.env)

✔️ Arquivos sensíveis ignorados pelo Git


▶️ Executando Localmente
Criar ambiente virtual:
```
Bash
python -m venv venv
```
Ativar ambiente:
```
Windows: venv\Scripts\activate
```
Instalar dependências:
```
Bash
pip install -r requirements.txt
```
Executar o bot:
```
Bash
python bot.py
```

🤝 Contribuição
Este projeto é interno, mas melhorias podem ser feitas via:

Criar uma branch

Implementar melhorias

Criar Pull Request

👨‍💻 Desenvolvedor
```
Matheus Eduardo
📧 matheus.eduardo@queonetics.com
```
