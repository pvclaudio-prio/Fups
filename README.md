# Documentação Técnica do Sistema de Monitoramento de Follow-ups de Auditoria

## Visão Geral

O sistema de monitoramento de follow-ups de auditoria é um aplicativo web desenvolvido em **Streamlit**, com integração ao **Google Drive** e à **API da OpenAI**, com o objetivo de:

* Centralizar o registro, acompanhamento e evidências de follow-ups.
* Permitir análise assistida por IA para interpretação semântica de relatórios.
* Automatizar o envio de alertas sobre pendências vencidas.

A aplicação segue uma arquitetura leve baseada em microserviços e APIs, com autenticação local e segmentação de permissões por usuário.

---

## Arquitetura

### Componentes

* **Frontend:** Streamlit
* **Armazenamento:** Google Drive (PyDrive)
* **IA Conversacional:** OpenAI GPT-4o via API
* **E-mail:** Yagmail (SMTP Gmail)

### Estrutura dos dados

* Arquivo `followups.csv` salvo no Google Drive
* Padrão de colunas:

  * Titulo, Ambiente, Ano, Auditoria, Risco
  * Plano de Acao, Responsavel, Usuario, E-mail
  * Prazo, Data de Conclusão, Status, Avaliação FUP, Observação

### Autenticação

* Login local via `st.session_state`
* Lista de `admin_users` para controle de acessos privilegiados

---

## Funcionalidades

### 1. **Dashboard**

* Apresenta KPIs gerais (concluídos, pendentes, etc.)
* Gráficos de distribuição por Status, Auditoria e Ano
* Filtra por responsável se o usuário não for admin

### 2. **Meus Follow-ups**

* Lista os follow-ups atribuídos ao usuário logado
* Permite filtrar por auditoria, status, ano e prazo
* Suporta edição campo a campo e exclusão controlada
* Exporta os resultados para Excel

### 3. **Cadastrar Follow-up**

* Formulário completo de registro
* Valida campos obrigatórios
* Atualiza o arquivo `followups.csv` no Drive
* Envia e-mail automático para o responsável

### 4. **Enviar Evidências**

* Permite upload de arquivos (PDF, imagem, ZIP)
* Organiza por subpastas nomeadas por índice
* Armazena observações em `.txt`
* Registra log local

### 5. **Visualizar Evidências**

* Admins veem todas as pastas
* Usuários comuns só veem índices atribuídos
* Visualiza arquivos e observacoes
* Permite download em ZIP
* Admins podem excluir pastas

### 6. **Chatbot FUP (IA)**

* Campo de entrada para perguntas livres
* Envia base completa + base filtrada para o GPT-4o
* Modelo responde com base em evidências reais, apontando participações, proporções e discrepâncias
* Resposta revisada por segundo prompt (revisor técnico)

### 7. **Envio Automático de E-mails de Follow-ups Vencidos**

* Identifica follow-ups com status ≠ Concluído e prazo vencido
* Agrupa por responsável
* Envia e-mail com tabela HTML dos itens vencidos
* Restringido a admins via botão no sidebar

---

## Segurança

* Apenas usuários autorizados logam na plataforma
* Apenas admins têm acesso à exclusão e envio de e-mails em lote
* E-mails e tokens são armazenados em `st.secrets`

---

## Considerações Finais

O sistema é modular, extensível e pode ser integrado a agendadores externos (cron, Airflow, Zapier) para automações futuras.

