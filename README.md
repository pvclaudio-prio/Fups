# Sistema de Gestão de Follow-ups de Auditoria

Aplicativo em **Streamlit** para gestão de follow-ups da Auditoria Interna, com integração ao Google Drive e envio automático de e-mails.

---

## Arquitetura

- **Frontend**: Streamlit  
- **Banco de dados**: `followups.csv` armazenado no Google Drive  
- **Armazenamento de evidências**: Google Drive (`evidencias/indice_x`)  
- **Envio de e-mails**: Gmail (via `yagmail`)  
- **Autenticação**: usuários definidos em dicionário no código  

---

## Funcionalidades

- **Login de usuários** com autenticação simples.  
- **Dashboard** com KPIs e gráficos interativos (Plotly).  
- **Meus Follow-ups**: filtros por auditoria, status, ano e prazo, além de edição e exclusão de registros.  
- **Cadastrar Follow-up**: formulário completo com envio automático de e-mail ao responsável.  
- **Enviar Evidências**: upload de documentos e observações vinculados ao índice do follow-up.  
- **Visualizar Evidências**: consulta e download em `.zip` das evidências armazenadas.  
- **Chatbot FUP**: integração com OpenAI GPT-4o para responder perguntas sobre follow-ups, com revisão automática da resposta.  

---

## Estrutura de Dados

Arquivo `followups.csv` contém as colunas:

- `Titulo`  
- `Ambiente`  
- `Ano`  
- `Auditoria`  
- `Risco`  
- `Plano_de_Acao`  
- `Responsavel`  
- `E-mail`  
- `Prazo`  
- `Data_Conclusao`  
- `Status`  
- `Avaliação FUP`  
- `Observação`  

---

## Integração com Google Drive

- Conexão via `OAuth2Credentials`.  
- Upload de `followups.csv` atualizado a cada alteração.  
- Evidências armazenadas em pastas no formato `evidencias/indice_<id>`.  
- Observações salvas em arquivos `observacao.txt`.  

---

## Envio de E-mails

- Configurado com **yagmail** e credenciais em `st.secrets`.  
- Notificações automáticas:  
  - Novo follow-up atribuído.  
  - Envio de evidências.  

---

## Dependências

- `streamlit`  
- `pandas`  
- `plotly`  
- `yagmail`  
- `pydrive`  
- `oauth2client`  
- `requests`  
- `openai`  
- `xlsxwriter`  

---

## Execução

1. Configure as credenciais no **Streamlit Secrets** (`.streamlit/secrets.toml`).  
2. Instale dependências:  
   ```bash
   pip install -r requirements.txt
