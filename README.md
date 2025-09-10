# 📊 Sistema de Gestão de Follow-ups de Auditoria

Aplicação **Streamlit** para gestão de follow-ups da Auditoria Interna, com integração ao **Google Drive**, envio de notificações por **SMTP interno**, dashboards interativos e módulo de análise via **OpenAI**.

---

## ⚙️ Arquitetura

- **Frontend:** Streamlit  
- **Persistência:** `followups.csv` no Google Drive (pasta `FUP`, com backups automáticos)  
- **Evidências:** armazenadas no Google Drive (`FUP/evidencias/indice_<ID>`)  
- **Notificações:** envio de e-mails via servidor SMTP interno (`10.40.0.106:587`)  
- **Autenticação:** usuários definidos em variáveis de ambiente (`USUARIO="Nome|Senha"`)  
- **IA:** análises automáticas com API da OpenAI (`gpt-4o`)  

FUP/
 ├── followups.csv
 ├── backup/
 │    └── followups_backup_<timestamp>.csv
 └── evidencias/
      └── indice_<ID>/
           ├── arquivo.pdf
           ├── arquivo.png
           └── observacao.txt

---

## 🚀 Funcionalidades

- **Login** com controle de perfis:
  - `admin_users`: administração, edição e exclusão
  - `cadastro_users`: inclusão de follow-ups
  - `chat_users`: acesso ao chatbot
- **Dashboard** com KPIs e gráficos (Plotly):
  - Distribuição por status, auditoria e ano
- **Gestão de Follow-ups**:
  - Consulta personalizada com filtros
  - Edição ou exclusão por índice
  - Exportação em Excel
- **Cadastro de Follow-up**:
  - Registro completo com metadados
  - Envio de notificação automática ao responsável
- **Evidências**:
  - Upload e associação a follow-ups
  - Visualização e download individual ou em lote (ZIP)
- **Chatbot FUP**:
  - Sumário executivo com riscos, prazos e frameworks (COSO, COBIT, ISO 27001, NIST, ITIL, PMBOK)
  - Consultoria prática para execução dos planos de ação
- **Notificações automáticas**:
  - Follow-ups **vencidos**  
  - Follow-ups **a vencer**

---

## 📦 Dependências

Arquivo `requirements.txt` mínimo:

```txt
streamlit
pandas
plotly
yagmail
pydrive
oauth2client
httplib2
requests
python-dotenv
openai
xlsxwriter
