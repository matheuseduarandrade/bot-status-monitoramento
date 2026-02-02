# 🗺️ Plano de Evolução — Status Monitoramento

Documento de planejamento técnico e funcional do bot **Status Monitoramento**.

---

## 🎯 Objetivo

Transformar o bot em uma **plataforma central de acompanhamento operacional**, rodando 24/7, com alertas automáticos, confiável e segura.

---

## 📍 Fase Atual (Concluída)

### ✅ Infraestrutura Base

* [x] Bot Telegram funcional
* [x] Integração com Jira
* [x] Integração com Google Calendar
* [x] Controle de acesso (admin x operador)
* [x] Código organizado e versionado
* [x] GitHub configurado com segurança

---

## 🚧 Próxima Fase (Curto Prazo)

### 1️⃣ Deploy 24/7 (PRIORIDADE)

Objetivo: manter o bot **sempre online**.

Opções:

* Railway (recomendado)
* Render
* Fly.io

Tarefas:

* [ ] Criar serviço Python
* [ ] Configurar variáveis de ambiente
* [ ] Definir comando de start
* [ ] Validar logs

---

### 2️⃣ Sistema de Alertas por Agenda

Objetivo: alertar operadores **30 minutos antes** dos atendimentos.

Características:

* Alertas individuais
* Baseados no Google Calendar
* Envio automático via Telegram
* Admins NÃO recebem alertas

Tarefas:

* [ ] Mapear usuários Telegram ↔ agendas
* [ ] Criar scheduler (APScheduler)
* [ ] Checar eventos futuros
* [ ] Evitar alertas duplicados

---

## 🔮 Médio Prazo

### 📊 Dashboard Administrativo

* Estatísticas de chamados
* SLA médio
* Chamados críticos

### 🔔 Alertas Inteligentes

* Chamado parado há X dias
* SLA estourado
* Projeto sem atualização

---

## 🧠 Longo Prazo

### 🧑‍💼 Gestão Operacional

* Aprovação de OS
* Check-in de atendimento
* Encerramento via bot

### 📈 BI & Relatórios

* Exportação CSV/PDF
* Relatórios mensais automáticos

---

## 🔐 Segurança & Governança

* Rotação de tokens
* Logs estruturados
* Controle de permissões

---

## 🧩 Stack Atual

* Python 3.13
* pyTelegramBotAPI
* Jira REST API
* Google Calendar API
* GitHub

---

## 📌 Observação Final

O projeto está **bem estruturado e escalável**. O foco agora deve ser:

> **Deploy 24/7 + Alertas Automáticos**

Esses dois pontos elevam o bot de "útil" para **essencial**.
