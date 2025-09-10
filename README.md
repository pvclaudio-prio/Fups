README — Sistema de Gestão de Follow-ups de Auditoria (Streamlit + Google Drive)

Este repositório contém um aplicativo Streamlit para gestão de follow-ups de Auditoria Interna da PRIO, com autenticação simples, integração ao Google Drive (PyDrive/OAuth2), envio de e-mails por relay SMTP interno, dashboards interativos, cadastro e acompanhamento de evidências, além de um “Chatbot FUP” que apoia análises executivas e a construção de planos de ação baseados em frameworks (COSO, COBIT, ISO 27001, NIST, ITIL e PMBOK).

Sumário

Arquitetura e Fluxo

Principais Funcionalidades

Requisitos

Variáveis de Ambiente (.env)

Instalação

Execução

Autenticação de Usuários

Estrutura de Dados (followups.csv)

Integração com Google Drive

Envio de E-mails

Páginas do Aplicativo

Dashboard

Meus Follow-ups

Cadastrar Follow-up

Enviar Evidências

Visualizar Evidências

Chatbot FUP

Rotinas de Lembrete (Vencidos e a Vencer)

Boas Práticas de Segurança

Solução de Problemas

Roadmap / Melhorias Sugeridas

Licença

Arquitetura e Fluxo

Frontend: Streamlit.

Dados: CSV followups.csv versionado no Google Drive (pasta “FUP”), com backups automáticos em FUP/backup.

Evidências: Armazenadas no Google Drive em FUP/evidencias/indice_<id>, com observações salvas como observacao*.txt.

E-mails: Relay SMTP interno (sem TLS/autenticação, conforme infraestrutura). Servidor: 10.40.0.106:587.

Autenticação: Mapa de usuários em variáveis de ambiente (usuário|senha).

Análises IA: “Chatbot FUP” chama a API da OpenAI (endpoint oficial). O código está preparado para ambientes com SSL autossinado, utilizando verify=False nas requisições HTTP.

Fluxo simplificado:

Usuário faz login.

App carrega followups.csv do Drive (ou cria vazio).

Usuário navega pelas páginas (dashboard, filtros, cadastro, evidências).

Ações de e-mail podem ser disparadas manualmente (vencidos, a vencer) ou por seleção.

Chatbot FUP executa análise em chunks do DataFrame e retorna sumário executivo e consultoria de planos de ação.

Principais Funcionalidades

KPI Dashboard (status, prazos, auditorias, anos) com gráficos Plotly.

Filtros por auditoria, status, ambiente, ano e intervalo de prazo.

Edição e exclusão de follow-ups por índice (com upload e backup automático no Drive).

Cadastro de novos follow-ups e e-mail automático de notificação ao responsável.

Envio e visualização de evidências (upload múltiplo, observações por arquivo, download em lote .zip).

Envio de lembretes por e-mail:

Itens selecionados.

Follow-ups vencidos.

Follow-ups a vencer.

Chatbot FUP:

Sumário executivo dos follow-ups filtrados (riscos, temas críticos, controles, prazos, distribuição por ambiente/ano/risco/auditoria, referências a frameworks).

Consultoria com plano de execução detalhado por follow-up, orientado pelo conteúdo do campo “Plano de Acao”.

Requisitos

Python 3.10+ recomendado

Bibliotecas principais:

streamlit, pandas, plotly, python-dotenv

pydrive, oauth2client, httplib2

requests, httpx

openai (SDK oficial)

sentence-transformers (instalado; o exemplo atual não usa embeddings explicitamente no fluxo crítico)

xlsxwriter (para exportação Excel)

Exemplo de requirements.txt:

streamlit>=1.36.0
pandas>=2.2.2
plotly>=5.22.0
python-dotenv>=1.0.1
pydrive>=1.3.1
oauth2client>=4.1.3
httplib2>=0.22.0
requests>=2.32.3
httpx>=0.27.0
openai>=1.35.3
sentence-transformers>=3.0.1
xlsxwriter>=3.2.0
