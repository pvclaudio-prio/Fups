import streamlit as st
import pandas as pd
from datetime import datetime, date
import yagmail
from io import BytesIO
from pathlib import Path
import plotly.express as px
import os
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import zipfile
import tempfile
import json
from oauth2client.client import OAuth2Credentials
import httplib2
import traceback
import openai
from sentence_transformers import SentenceTransformer, util

st.set_page_config(layout = 'wide')

#st.sidebar.text(f"Diretório atual: {os.getcwd()}")

caminho_csv = "followups.csv"
admin_users = ["cvieira", "amendonca", "mathayde", "bella"]

def enviar_email_gmail(destinatario, assunto, corpo_html):
    try:
        yag = yagmail.SMTP(user=st.secrets["email_user"], password=st.secrets["email_pass"])
        yag.send(to=destinatario, subject=assunto, contents=corpo_html)
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False
    
def conectar_drive():
    cred_dict = st.secrets["credentials"]

    credentials = OAuth2Credentials(
        access_token=cred_dict["access_token"],
        client_id=cred_dict["client_id"],
        client_secret=cred_dict["client_secret"],
        refresh_token=cred_dict["refresh_token"],
        token_expiry=datetime.strptime(cred_dict["token_expiry"], "%Y-%m-%dT%H:%M:%SZ"),
        token_uri=cred_dict["token_uri"],
        user_agent="streamlit-app/1.0",
        revoke_uri=cred_dict["revoke_uri"]
    )

    # Atualiza token se expirado
    if credentials.access_token_expired:
        credentials.refresh(httplib2.Http())

    gauth = GoogleAuth()
    gauth.credentials = credentials
    drive = GoogleDrive(gauth)
    return drive
        
def enviar_email(destinatario, assunto, corpo_html):
    try:
        yag = yagmail.SMTP(user=st.secrets["email_user"], password=st.secrets["email_pass"])
        yag.send(to=destinatario, subject=assunto, contents=corpo_html)
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False

def upload_para_drive():
    try:
        drive = conectar_drive()
        arquivo = drive.CreateFile({'title': 'followups.csv'})
        arquivo.SetContentFile(caminho_csv)
        arquivo.Upload()
        st.info("📤 Arquivo 'followups.csv' enviado ao Google Drive com sucesso.")
    except Exception as e:
        st.warning(f"Erro ao enviar para o Drive: {e}")

def upload_evidencias_para_drive(idx, arquivos, observacao):
    try:
        drive = conectar_drive()
        pasta_principal = None

        # Procura ou cria a pasta principal "evidencias"
        lista = drive.ListFile({'q': "title='evidencias' and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
        if lista:
            pasta_principal = lista[0]
        else:
            pasta_principal = drive.CreateFile({'title': 'evidencias', 'mimeType': 'application/vnd.google-apps.folder'})
            pasta_principal.Upload()

        # Cria subpasta indice_x
        subpasta_nome = f"indice_{idx}"
        subpastas = drive.ListFile({'q': f"'{pasta_principal['id']}' in parents and title='{subpasta_nome}' and mimeType='application/vnd.google-apps.folder' and trashed=false"}).GetList()
        if subpastas:
            subpasta = subpastas[0]
        else:
            subpasta = drive.CreateFile({'title': subpasta_nome, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [{'id': pasta_principal['id']}]})
            subpasta.Upload()

        # Envia arquivos
        for arq in arquivos:
            arquivo_drive = drive.CreateFile({'title': arq.name, 'parents': [{'id': subpasta['id']}]})
            
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_file.write(arq.getvalue())
                tmp_file.flush()
                arquivo_drive.SetContentFile(tmp_file.name)
                arquivo_drive.Upload()

        # Observação
        if observacao.strip():
            obs_file = drive.CreateFile({'title': 'observacao.txt', 'parents': [{'id': subpasta['id']}]})
            obs_file.SetContentString(observacao.strip())
            obs_file.Upload()

        st.success("✅ Evidências enviadas ao Google Drive com sucesso.")
        return True
    except Exception as e:
        st.error(f"Erro ao enviar evidências para o Drive: {e}")
        return False

# --- Usuários e autenticação simples ---
users = {
    "cvieira": {"name": "Claudio Vieira", "password": "1234"},
    "auditoria": {"name": "Time Auditoria", "password": "auditoria"},
    "amendonca": {"name": "Alex Mendonça", "password": "1234"},
    "mathayde": {"name": "Maria Luiza", "password": "1234"},
    "bella": {"name": "Isabella Miranda", "password": "claudio meu amor"}
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🔐 Login")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        user = users.get(username)
        if user and user["password"] == password:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Bem-vindo, {user['name']}!")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
    st.stop()

# --- Layout principal após login ---
st.sidebar.image("PRIO_SEM_POLVO_PRIO_PANTONE_LOGOTIPO_Azul.png")
nome_usuario = users[st.session_state.username]["name"]
st.sidebar.success(f"Logado como: {nome_usuario}")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

# --- Menu lateral ---
st.sidebar.title("📋 Menu")
menu = st.sidebar.radio("Navegar para:", [
    "Dashboard",
    "Meus Follow-ups",
    "Cadastrar Follow-up",
    "Enviar Evidências",
    "Visualizar Evidências",
    "🔍 Chatbot FUP"
])

# --- Conteúdo das páginas ---

if menu == "Dashboard":
    st.title("📊 Painel de KPIs")

    try:
        # Conecta ao Google Drive
        drive = conectar_drive()

        # Procura arquivo chamado 'followups.csv'
        arquivos = drive.ListFile({
            'q': "title = 'followups.csv' and trashed=false"
        }).GetList()

        if not arquivos:
            st.warning("Arquivo followups.csv não encontrado no Drive.")
            st.stop()

        arquivo = arquivos[0]
        caminho_temp = tempfile.NamedTemporaryFile(delete=False).name
        arquivo.GetContentFile(caminho_temp)

        # Carrega CSV com pandas
        df = pd.read_csv(caminho_temp)

        usuario_logado = st.session_state.username
        nome_usuario = users[usuario_logado]["name"]

        if usuario_logado not in admin_users:
            df = df[df["Responsavel"].str.lower() == nome_usuario.lower()]

        if df.empty:
            st.info("Nenhum dado disponível para exibir KPIs.")
            st.stop()

        df["Prazo"] = pd.to_datetime(df["Prazo"])
        df["Ano"] = df["Ano"].astype(str)
        df["Status"] = df["Status"].fillna("Não informado")

        # --- KPIs principais ---
        total = len(df)
        concluidos = (df["Status"] == "Concluído").sum()
        pendentes = (df["Status"] == "Pendente").sum()
        andamento = (df["Status"] == "Em Andamento").sum()
        taxa_conclusao = round((concluidos / total) * 100, 1) if total > 0 else 0.0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Follow-ups", total)
        col2.metric("Concluídos", concluidos)
        col3.metric("Pendentes", pendentes)
        col4.metric("Conclusão (%)", f"{taxa_conclusao}%")

        # --- Gráficos ---
        st.subheader("📌 Distribuição por Status")
        fig_status = px.pie(
            df,
            names="Status",
            title="Distribuição dos Follow-ups por Status",
            hole=0.4
        )
        st.plotly_chart(fig_status, use_container_width=True)

        st.subheader("📁 Follow-ups por Auditoria")
        auditoria_counts = df["Auditoria"].value_counts().reset_index()
        auditoria_counts.columns = ["Auditoria", "Quantidade"]
        fig_auditoria = px.bar(
            auditoria_counts,
            x="Auditoria",
            y="Quantidade",
            title="Distribuição de Follow-ups por Auditoria"
        )
        st.plotly_chart(fig_auditoria, use_container_width=True)

        st.subheader("📅 Follow-ups por Ano")
        ano_counts = df["Ano"].value_counts().sort_index().reset_index()
        ano_counts.columns = ["Ano", "Quantidade"]
        fig_ano = px.line(
            ano_counts,
            x="Ano",
            y="Quantidade",
            markers=True,
            title="Evolução de Follow-ups por Ano"
        )
        st.plotly_chart(fig_ano, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao acessar dados do Google Drive: {e}")

elif menu == "Meus Follow-ups":
    st.title("📁 Meus Follow-ups")
    st.info("Esta seção exibirá os follow-ups atribuídos a você.")

    try:
        # Conecta ao Google Drive
        drive = conectar_drive()

        # Procura arquivo chamado 'followups.csv'
        arquivos = drive.ListFile({
            'q': "title = 'followups.csv' and trashed=false"
        }).GetList()

        if not arquivos:
            st.warning("Arquivo followups.csv não encontrado no Google Drive.")
            st.stop()

        arquivo = arquivos[0]
        caminho_temp = tempfile.NamedTemporaryFile(delete=False).name
        arquivo.GetContentFile(caminho_temp)

        df = pd.read_csv(caminho_temp)

        usuario_logado = st.session_state.username
        nome_usuario = users[usuario_logado]["name"]

        if usuario_logado not in admin_users:
            df = df[df["Responsavel"].str.lower() == nome_usuario.lower()]

        df["Prazo"] = pd.to_datetime(df["Prazo"])
        df["Ano"] = df["Ano"].astype(str)

        # --- Filtros na sidebar ---
        st.sidebar.subheader("Filtros de Pesquisa")

        if st.sidebar.button("🔄 Limpar Filtros"):
            st.rerun()

        auditorias = ["Todos"] + sorted(df["Auditoria"].dropna().unique().tolist())
        auditoria_selecionada = st.sidebar.selectbox("Auditoria", auditorias)

        status_lista = ["Todos"] + sorted(df["Status"].dropna().unique().tolist())
        status_selecionado = st.sidebar.selectbox("Status", status_lista)

        anos = ["Todos"] + sorted(df["Ano"].dropna().unique().tolist())
        ano_selecionado = st.sidebar.selectbox("Ano", anos)

        prazo_inicial, prazo_final = st.sidebar.date_input(
            "Intervalo de Prazo",
            [df["Prazo"].min().date(), df["Prazo"].max().date()]
        )

        if auditoria_selecionada != "Todos":
            df = df[df["Auditoria"] == auditoria_selecionada]

        if status_selecionado != "Todos":
            df = df[df["Status"] == status_selecionado]

        if ano_selecionado != "Todos":
            df = df[df["Ano"] == ano_selecionado]

        df = df[(df["Prazo"].dt.date >= prazo_inicial) & (df["Prazo"].dt.date <= prazo_final)]
        df = df.sort_values(by="Prazo")

        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.success(f"Total Follow Ups: {len(df)}")

            st.subheader("🛠️ Atualizar / Excluir Follow-up por Índice")

            indices_disponiveis = df.index.tolist()
            indice_selecionado = st.selectbox("Selecione o índice para edição", indices_disponiveis)

            linha = df.loc[indice_selecionado]
            st.markdown(f"""
            🔎 **Título:** {linha['Titulo']}  
            📅 **Prazo:** {linha['Prazo'].strftime('%d/%m/%Y')}  
            👤 **Responsável:** {linha['Responsavel']}  
            📌 **Status:** {linha['Status']}
            """)

            colunas_editaveis = [col for col in df.columns]
            coluna_escolhida = st.selectbox("Selecione a coluna para alterar", colunas_editaveis)

            valor_atual = linha[coluna_escolhida]

            if coluna_escolhida in ["Prazo", "Data_Conclusao"]:
                try:
                    data_inicial = pd.to_datetime(valor_atual).date()
                except:
                    data_inicial = date.today()
                novo_valor = st.date_input(f"Novo valor para '{coluna_escolhida}':", value=data_inicial)
                novo_valor_str = novo_valor.strftime("%Y-%m-%d")
            else:
                novo_valor = st.text_input(f"Valor atual de '{coluna_escolhida}':", value=str(valor_atual))
                novo_valor_str = novo_valor.strip()

            if st.button("💾 Atualizar campo"):
                df_original = pd.read_csv(caminho_temp)
                df_original.at[indice_selecionado, coluna_escolhida] = novo_valor_str
                df_original.to_csv(caminho_csv, index=False)

                try:
                    arquivo.SetContentFile(caminho_csv)
                    arquivo.Upload()
                    st.info("📤 Arquivo 'followups.csv' atualizado no Google Drive.")
                except Exception as e:
                    st.warning(f"Erro ao enviar para o Drive: {e}")

                st.success(f"'{coluna_escolhida}' atualizado com sucesso.")
                st.rerun()

            if usuario_logado in admin_users:
                if st.button("🗑️ Excluir este follow-up"):
                    df_original = pd.read_csv(caminho_temp)
                    df_original = df_original.drop(index=indice_selecionado)
                    df_original.to_csv(caminho_csv, index=False)

                    try:
                        arquivo.SetContentFile(caminho_csv)
                        arquivo.Upload()
                        st.info("📤 Arquivo 'followups.csv' atualizado no Google Drive.")
                    except Exception as e:
                        st.warning(f"Erro ao enviar para o Drive: {e}")

                    st.success("Follow-up excluído com sucesso.")
                    st.rerun()

            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='FollowUps')

            st.download_button(
                label="📥 Exportar resultados para Excel",
                data=buffer.getvalue(),
                file_name="followups_filtrados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        else:
            st.info("Nenhum follow-up encontrado com os filtros aplicados.")

    except Exception as e:
        st.error(f"Erro ao acessar dados do Google Drive: {e}")

elif menu == "Cadastrar Follow-up":
    st.title("📝 Cadastrar Follow-up")
    st.info("Aqui você poderá cadastrar um novo follow-up.")

    with st.form("form_followup"):
        titulo = st.text_input("Título")
        ambiente = st.text_input("Ambiente")
        ano = st.selectbox("Ano", list(range(2020, date.today().year + 2)))
        auditoria = st.text_input("Auditoria")
        risco = st.selectbox("Risco", ["Baixo", "Médio", "Alto"])
        plano = st.text_area("Plano de Ação")
        responsavel = st.text_input("Responsável")
        usuario = st.text_input("Usuário")
        email = st.text_input("E-mail do Responsável")
        prazo = st.date_input("Prazo", min_value=date.today())
        data_conclusao = st.date_input("Data de Conclusão", value=date.today())
        status = st.selectbox("Status", ["Pendente", "Em Andamento", "Concluído"])
        avaliacao = st.selectbox("Avaliação FUP", ["", "Satisfatório", "Insatisfatório"])
        observacao = st.text_area("Observação")

        submitted = st.form_submit_button("Salvar Follow-up")

    if submitted:
        novo = {
            "Titulo": titulo,
            "Ambiente": ambiente,
            "Ano": ano,
            "Auditoria": auditoria,
            "Risco": risco,
            "Plano_de_Acao": plano,
            "Responsavel": responsavel,
            "E-mail": email,
            "Prazo": prazo.strftime("%Y-%m-%d"),
            "Data_Conclusao": data_conclusao.strftime("%Y-%m-%d"),
            "Status": status,
            "Avaliação FUP": avaliacao,
            "Observação": observacao
        }

        try:
            # Conecta ao Google Drive e busca o followups.csv
            drive = conectar_drive()
            arquivos = drive.ListFile({
                'q': "title = 'followups.csv' and trashed=false"
            }).GetList()

            if arquivos:
                arquivo = arquivos[0]
                caminho_temp = tempfile.NamedTemporaryFile(delete=False).name
                arquivo.GetContentFile(caminho_temp)
                df = pd.read_csv(caminho_temp)
            else:
                df = pd.DataFrame()
                arquivo = drive.CreateFile({'title': 'followups.csv'})

            # Atualiza e salva
            df = pd.concat([df, pd.DataFrame([novo])], ignore_index=True)
            df.to_csv(caminho_csv, index=False)

            arquivo.SetContentFile(caminho_csv)
            arquivo.Upload()

            st.success("✅ Follow-up salvo e sincronizado com o Google Drive!")

            corpo = f"""
            <p>Olá <b>{responsavel}</b>,</p>
            <p>Um novo follow-up foi atribuído a você:</p>
            <ul>
                <li><b>Título:</b> {titulo}</li>
                <li><b>Auditoria:</b> {auditoria}</li>
                <li><b>Prazo:</b> {prazo.strftime('%d/%m/%Y')}</li>
                <li><b>Status:</b> {status}</li>
            </ul>
            <p>Acesse o aplicativo para incluir evidências e acompanhar o andamento:</p>
            <p><a href='https://fup-auditoria.streamlit.app/' target='_blank'>🔗 fup-auditoria.streamlit.app</a></p>
            <br>
            <p>Atenciosamente,<br>Auditoria Interna</p>
            """

            if email:
                sucesso_envio = enviar_email_gmail(
                    destinatario=email,
                    assunto=f"[Follow-up] Nova Atribuição: {titulo}",
                    corpo_html=corpo
                )
                if sucesso_envio:
                    st.success("📧 E-mail de notificação enviado com sucesso!")

        except Exception as e:
            st.error(f"Erro ao cadastrar follow-up: {e}")

elif menu == "Enviar Evidências":
    st.title("📌 Enviar Evidências")
    st.info("Aqui você poderá enviar comprovantes e observações para follow-ups.")

    try:
        # 🔄 Puxa o arquivo mais recente do Drive
        drive = conectar_drive()
        arquivos_drive = drive.ListFile({
            'q': "title = 'followups.csv' and trashed=false"
        }).GetList()

        if not arquivos_drive:
            st.warning("Arquivo followups.csv não encontrado no Google Drive.")
            st.stop()

        arquivo_drive = arquivos_drive[0]
        caminho_temp = tempfile.NamedTemporaryFile(delete=False).name
        arquivo_drive.GetContentFile(caminho_temp)
        df = pd.read_csv(caminho_temp)

        usuario_logado = st.session_state.username
        nome_usuario = users[usuario_logado]["name"]

        if usuario_logado not in admin_users:
            df = df[df["Responsavel"].str.lower() == nome_usuario.lower()]

        if df.empty:
            st.info("Nenhum follow-up disponível para envio de evidência.")
            st.stop()

        idx = st.selectbox("Selecione o índice do follow-up:", df.index.tolist())
        linha = df.loc[idx]

        st.markdown(f"""
        🔎 **Título:** {linha['Titulo']}  
        📅 **Prazo:** {linha['Prazo']}  
        👤 **Responsável:** {linha['Responsavel']}  
        📝 **Plano de Ação:** {linha['Plano_de_Acao']}
        """)

        arquivos = st.file_uploader(
            "Anexe arquivos de evidência",
            type=["pdf", "png", "jpg", "jpeg", "zip"],
            accept_multiple_files=True
        )
        observacao = st.text_area("Observações (opcional)")

        submitted = st.button("📨 Enviar Evidência")
        if submitted:
            if not arquivos:
                st.warning("Você precisa anexar pelo menos um arquivo.")
                st.stop()

            # Upload direto para o Google Drive
            sucesso_upload = upload_evidencias_para_drive(idx, arquivos, observacao)

            # Registro em log (local)
            if sucesso_upload:
                try:
                    log_path = Path("log_evidencias.csv")
                    log_data = {
                        "indice": idx,
                        "titulo": linha["Titulo"],
                        "responsavel": linha["Responsavel"],
                        "arquivos": "; ".join([arq.name for arq in arquivos]),
                        "observacao": observacao,
                        "data_envio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "enviado_por": nome_usuario,
                    }
                    log_df = pd.DataFrame([log_data])
                    if log_path.exists():
                        log_df.to_csv(log_path, mode="a", header=False, index=False)
                    else:
                        log_df.to_csv(log_path, index=False)
                    st.success("✅ Registro salvo no log local.")
                except Exception as e:
                    st.error(f"Erro ao salvar log local: {e}")

                # Enviar e-mail de notificação
                corpo = f"""
                <p>🕵️ Evidência enviada para o follow-up:</p>
                <ul>
                    <li><b>Índice:</b> {idx}</li>
                    <li><b>Título:</b> {linha['Titulo']}</li>
                    <li><b>Responsável:</b> {linha['Responsavel']}</li>
                    <li><b>Arquivos:</b> {"; ".join([arq.name for arq in arquivos])}</li>
                    <li><b>Data:</b> {datetime.now().strftime("%d/%m/%Y %H:%M")}</li>
                </ul>
                <p>Evidências armazenadas no Google Drive (pasta: <b>evidencias/indice_{idx}</b>).</p>
                """

                sucesso_envio = enviar_email(
                    destinatario="cvieira@prio3.com.br",
                    assunto=f"[Evidência] Follow-up #{idx} - {linha['Titulo']}",
                    corpo_html=corpo
                )
                if sucesso_envio:
                    st.success("📧 Notificação enviada ao time de auditoria!")

    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Drive: {e}")

elif menu == "Visualizar Evidências":

    st.title("📂 Visualização de Evidências - Google Drive")

    try:
        drive = conectar_drive()

        # Pasta "evidencias"
        pasta_principal = drive.ListFile({
            'q': "title='evidencias' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        }).GetList()

        if not pasta_principal:
            st.warning("Nenhuma pasta de evidências encontrada.")
            st.stop()

        pasta_id = pasta_principal[0]['id']

        # Subpastas tipo indice_1, indice_2...
        subpastas = drive.ListFile({
            'q': f"'{pasta_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        }).GetList()

        if not subpastas:
            st.info("Nenhuma evidência disponível.")
            st.stop()

        # Cria dicionário com chaves como "1", "2", etc.
        opcoes = {
            p['title'].split('_')[1]: {'id': p['id'], 'obj': p}
            for p in subpastas if p['title'].startswith('indice_') and '_' in p['title']
        }

        if not opcoes:
            st.warning("Nenhuma subpasta válida encontrada no Google Drive.")
            st.stop()

        indices_disponiveis = sorted(opcoes.keys(), key=int)
        indice_escolhido = st.selectbox("Selecione o índice do follow-up:", indices_disponiveis)

        if indice_escolhido not in opcoes:
            st.error(f"Índice '{indice_escolhido}' não encontrado.")
            st.stop()

        pasta_selecionada_id = opcoes[indice_escolhido]['id']
        pasta_obj = opcoes[indice_escolhido]['obj']

        st.subheader(f"📁 Evidências para Follow-up #{indice_escolhido}")

        arquivos = drive.ListFile({
            'q': f"'{pasta_selecionada_id}' in parents and trashed=false"
        }).GetList()

        if not arquivos:
            st.info("Nenhum arquivo nesta pasta.")
            st.stop()

        buffer_zip = BytesIO()
        with zipfile.ZipFile(buffer_zip, "w") as zipf:
            for arq in arquivos:
                nome = arq['title']
                if nome.lower() == "observacao.txt":
                    conteudo = arq.GetContentString()
                    st.markdown("**📝 Observação:**")
                    st.info(conteudo)
                    zipf.writestr(nome, conteudo)
                else:
                    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                        arq.GetContentFile(tmp_file.name)
                        tmp_file.seek(0)
                        zipf.write(tmp_file.name, arcname=nome)
                        link = arq['alternateLink']
                        st.markdown(f"📎 [{nome}]({link})", unsafe_allow_html=True)

        buffer_zip.seek(0)
        st.download_button(
            label="📦 Baixar todos como .zip",
            data=buffer_zip,
            file_name=f"evidencias_indice_{indice_escolhido}.zip",
            mime="application/zip"
        )

        # Botão de exclusão (somente admin)
        if st.session_state.username in admin_users:
            if st.button("🗑️ Excluir todas as evidências deste índice"):
                try:
                    pasta_obj.Delete()
                    st.success(f"Evidências do índice {indice_escolhido} excluídas com sucesso.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir evidências: {e}")

    except Exception as e:
        st.error("Erro ao acessar evidências no Google Drive.")
        st.code(traceback.format_exc())

elif menu == "🔍 Chatbot FUP":
    st.title("🤖 Chatbot - Consulta Inteligente de Follow-ups")

    import openai
    from sentence_transformers import SentenceTransformer, util

    # API da OpenAI
    openai.api_key = st.secrets["openai"]["api_key"]

    @st.cache_resource
    def carregar_modelo():
        return SentenceTransformer('all-MiniLM-L6-v2')

    @st.cache_data
    def carregar_followups():
        drive = conectar_drive()
        arquivos = drive.ListFile({
            'q': "title = 'followups.csv' and trashed=false"
        }).GetList()
        if not arquivos:
            return pd.DataFrame()
        caminho_temp = tempfile.NamedTemporaryFile(delete=False).name
        arquivos[0].GetContentFile(caminho_temp)
        return pd.read_csv(caminho_temp)

    modelo = carregar_modelo()
    df = carregar_followups()

    if df.empty:
        st.warning("Nenhum follow-up disponível para análise.")
        st.stop()

    df['texto_completo'] = df.fillna('').astype(str).agg(' '.join, axis=1)
    embeddings = modelo.encode(df['texto_completo'].tolist(), convert_to_tensor=True)

    consulta = st.text_area("📝 Digite sua pergunta ou descrição livre do que procura:")

    if st.button("🔎 Buscar Follow-ups"):
        with st.spinner("Analisando similaridade semântica..."):
            consulta_emb = modelo.encode(consulta, convert_to_tensor=True)
            scores = util.cos_sim(consulta_emb, embeddings)[0]
            top_k = min(5, len(scores))
            top_indices = [int(i) for i in scores.argsort(descending=True)[:top_k]]

            st.subheader("🔍 Resultados mais relevantes:")
            for idx in top_indices:
                st.markdown(f"**🎯 Score de similaridade:** `{scores[idx]:.2f}`")
                st.write(df.iloc[idx]["texto_completo"])
                st.markdown("---")

            if st.button("🧠 Obter mais respostas"):
                top_textos = [df.iloc[idx]["texto_completo"] for idx in top_indices]
                contexto = "\n\n".join(top_textos)

                prompt_usuario = f"""
Você é um especialista de auditoria interna. Com base nas informações abaixo dos follow-ups, responda a pergunta do usuário de forma direta e baseada em evidências reais dos registros:

Follow-ups:
{contexto}

Pergunta:
{consulta}
"""

                resposta = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "Você é um especialista em auditoria interna e follow-ups."},
                        {"role": "user", "content": prompt_usuario}
                    ],
                    temperature=0.3
                )

                st.markdown("### 💬 Resposta do Agente")
                st.write(resposta.choices[0].message.content)
