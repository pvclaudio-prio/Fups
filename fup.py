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
import json
import httpx
from sentence_transformers import SentenceTransformer, util
from openai import OpenAI
import json
import requests
import tempfile
from difflib import get_close_matches
import re
from datetime import timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


st.set_page_config(layout = 'wide')

#st.sidebar.text(f"Diretório atual: {os.getcwd()}")

caminho_csv = "followups.csv"
admin_users = ["cvieira", "amendonca", "mathayde"]
cadastro_users = ["cvieira", "amendonca", "mathayde"]
chat_users = ["cvieira", "amendonca", "mathayde","bromanelli","ysouza"]
    
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
        
def enviar_email_outlook(destinatario, assunto, corpo_html):
    try:
        remetente = st.secrets["email_user"]
        senha = st.secrets["email_pass"]

        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo_html, 'html'))

        # Conecta ao servidor SMTP da Microsoft
        with smtplib.SMTP('smtp.office365.com', 587) as server:
            server.starttls()
            server.login(remetente, senha)
            server.send_message(msg)

        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail via Outlook: {e}")
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
        
def carregar_followups():
    drive = conectar_drive()
    arquivos = drive.ListFile({'q': "title = 'followups.csv' and trashed=false"}).GetList()

    colunas = [
        "Titulo", "Ambiente", "Ano", "Auditoria", "Risco",
        "Plano de Acao", "Responsavel", "Usuario", "E-mail",
        "Prazo", "Data de Conclusão", "Status", "Avaliação FUP", "Observação"
    ]

    if not arquivos:
        df_vazio = pd.DataFrame(columns=colunas)
        caminho_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv").name
        df_vazio.to_csv(caminho_temp, sep=";", index=False, encoding="utf-8-sig")
        novo_arquivo = drive.CreateFile({'title': 'followups.csv'})
        novo_arquivo.SetContentFile(caminho_temp)
        novo_arquivo.Upload()
        return df_vazio

    caminho_temp = tempfile.NamedTemporaryFile(delete=False).name
    arquivos[0].GetContentFile(caminho_temp)

    try:
        df = pd.read_csv(caminho_temp, sep=";", encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(caminho_temp, sep=";", encoding="latin1")

    return df

# --- Usuários e autenticação simples ---
@st.cache_data
def carregar_usuarios():
    usuarios_config = st.secrets.get("users", {})
    usuarios = {}
    for user, dados in usuarios_config.items():
        try:
            nome, senha = dados.split("|", 1)
            usuarios[user] = {"name": nome, "password": senha}
        except:
            st.warning(f"Erro ao carregar usuário '{user}' nos secrets.")
    return usuarios

users = carregar_usuarios()

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
        df = pd.read_csv(caminho_temp, sep=";", encoding="utf-8-sig")
        df.columns = df.columns.str.strip()
    
        usuario_logado = st.session_state.username
        nome_usuario = users[usuario_logado]["name"]
    
        if usuario_logado not in admin_users:
            df = df[df["Responsavel"].str.lower() == nome_usuario.lower()]
    
        if df.empty:
            st.info("Nenhum dado disponível para exibir KPIs.")
            st.stop()
    
        df["Prazo"] = pd.to_datetime(df["Prazo"], format="mixed", errors="coerce")
        df["Ano"] = df["Ano"].astype(str)
        df["Status"] = df["Status"].fillna("Não informado")
    
        # --- KPIs principais ---
        total = len(df)
        concluidos = (df["Status"] == "Concluído").sum()
        pendentes = (df["Status"] == "Pendente").sum()
        andamento = (df["Status"] == "Em Andamento").sum()
        taxa_conclusao = round((concluidos / total) * 100, 1) if total > 0 else 0.0
    
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total Follow-ups", total)
        col2.metric("Concluídos", concluidos)
        col3.metric("Pendentes", pendentes)
        col4.metric("Em Andamento", andamento)
        col5.metric("Conclusão (%)", f"{taxa_conclusao}%")
    
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
        fig_ano.update_layout(xaxis=dict(tickformat=".0f"))
        st.plotly_chart(fig_ano, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao acessar dados do Google Drive: {e}")

elif menu == "Meus Follow-ups":
    st.title("📁 Meus Follow-ups")
    st.info("Esta seção exibirá os follow-ups atribuídos a você.")

    try:
        df = carregar_followups()
        df.columns = df.columns.str.strip()

        usuario_logado = st.session_state.username
        nome_usuario = users[usuario_logado]["name"]

        if usuario_logado not in admin_users:
            df = df[df["Responsavel"].str.lower() == nome_usuario.lower()]
            
        df["Prazo"] = pd.to_datetime(df["Prazo"], format = "mixed", errors="coerce")
        #df["Prazo"] = df["Prazo"].dt.strftime("%d/%m/%Y")
        df["Data de Conclusão"] = pd.to_datetime(df["Data de Conclusão"], format = "mixed", errors="coerce")
        #df["Data de Conclusão"] = df["Data de Conclusão"].dt.strftime("%d/%m/%Y")
        df["Ano"] = df["Ano"].astype(str)

        # --- Filtros na sidebar ---
        st.sidebar.subheader("Filtros de Pesquisa")

        if st.sidebar.button("🔄 Limpar Filtros"):
            st.rerun()

        auditorias = ["Todos"] + sorted(df["Auditoria"].dropna().unique().tolist())
        auditoria_selecionada = st.sidebar.selectbox("Auditoria", auditorias)

        status_lista = ["Todos"] + sorted(df["Status"].dropna().unique().tolist())
        status_selecionado = st.sidebar.selectbox("Status", status_lista)

        status_ambiente = ["Todos"] + sorted(df["Ambiente"].dropna().unique().tolist())
        status_ambiente_selecionado = st.sidebar.selectbox("Ambiente", status_ambiente)

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

        if status_ambiente_selecionado != "Todos":
            df = df[df["Ambiente"] == status_ambiente_selecionado]
        
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

            if coluna_escolhida in ["Prazo", "Data de Conclusão"]:
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
                df_original = carregar_followups()
                df_original.at[indice_selecionado, coluna_escolhida] = novo_valor_str
                df_original.to_csv(caminho_csv, sep=";", index=False, encoding="utf-8-sig")

                try:
                    drive = conectar_drive()
                    arquivos = drive.ListFile({'q': "title = 'followups.csv' and trashed=false"}).GetList()
                    if arquivos:
                        arquivo = arquivos[0]
                        arquivo.SetContentFile(caminho_csv)
                        arquivo.Upload()
                    st.info("📤 Arquivo 'followups.csv' atualizado no Google Drive.")
                except Exception as e:
                    st.warning(f"Erro ao enviar para o Drive: {e}")

                st.success(f"'{coluna_escolhida}' atualizado com sucesso.")
                st.rerun()

            if usuario_logado in admin_users:
                if st.button("🗑️ Excluir este follow-up"):
                    df_original = df.drop(index=indice_selecionado)
                    df_original.to_csv(caminho_csv, sep=";", index=False, encoding="utf-8-sig")

                    try:
                        drive = conectar_drive()
                        arquivos = drive.ListFile({'q': "title = 'followups.csv' and trashed=false"}).GetList()
                        if arquivos:
                            arquivo = arquivos[0]
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
    if st.session_state.username in cadastro_users:
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
                "Plano de Acao": plano,
                "Responsavel": responsavel,
                "Usuario": usuario,
                "E-mail": email,
                "Prazo": prazo.strftime("%Y-%m-%d"),
                "Data de Conclusão": data_conclusao.strftime("%Y-%m-%d"),
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
                    df = pd.read_csv(caminho_temp, sep=";", encoding="utf-8-sig")
                else:
                    df = pd.DataFrame()
                    arquivo = drive.CreateFile({'title': 'followups.csv'})
    
                # Atualiza e salva
                df = pd.concat([df, pd.DataFrame([novo])], ignore_index=True)
                df.to_csv(caminho_csv, sep=";", index=False, encoding="utf-8-sig")
    
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
                    sucesso_envio = enviar_email_outlook(
                        destinatario=email,
                        assunto=f"[Follow-up] Nova Atribuição: {titulo}",
                        corpo_html=corpo
                    )
                    if sucesso_envio:
                        st.success("📧 E-mail de notificação enviado com sucesso!")
    
            except Exception as e:
                st.error(f"Erro ao cadastrar follow-up: {e}")
    else:
        st.warning("Você não possui permissão para cadastrar follow ups!")

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
        df = pd.read_csv(caminho_temp, sep=";", encoding="utf-8-sig")
        df.columns = df.columns.str.strip()

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
        📝 **Plano de Ação:** {linha['Plano de Acao']}
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

                sucesso_envio = enviar_email_outlook(
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
        df = carregar_followups()
        df.columns = df.columns.str.strip()

        usuario_logado = st.session_state.username
        nome_usuario = users[usuario_logado]["name"].lower()

        # Pasta "evidencias"
        pasta_principal = drive.ListFile({
            'q': "title='evidencias' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        }).GetList()

        if not pasta_principal:
            st.warning("Nenhuma pasta de evidências encontrada.")
            st.stop()

        pasta_id = pasta_principal[0]['id']

        subpastas = drive.ListFile({
            'q': f"'{pasta_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        }).GetList()

        if usuario_logado in admin_users:
            opcoes = {
                p['title'].split('_')[1]: {'id': p['id'], 'obj': p}
                for p in subpastas if p['title'].startswith('indice_') and '_' in p['title']
            }
        else:
            indices_usuario = df[df['Responsavel'].str.lower() == nome_usuario].index.astype(str).tolist()
            opcoes = {
                p['title'].split('_')[1]: {'id': p['id'], 'obj': p}
                for p in subpastas
                if p['title'].startswith('indice_') and '_' in p['title'] and p['title'].split('_')[1] in indices_usuario
            }

        if not opcoes:
            st.warning("Você não possui evidências associadas.")
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

        if usuario_logado in admin_users:
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

    st.title("🤖 Chatbot dos relatórios de auditoria")
    if st.session_state.username in chat_users:
        def carregar_followups():
            drive = conectar_drive()
            arquivos = drive.ListFile({
                'q': "title = 'followups.csv' and trashed=false"
            }).GetList()
            if not arquivos:
                return pd.DataFrame()
            caminho_temp = tempfile.NamedTemporaryFile(delete=False).name
            arquivos[0].GetContentFile(caminho_temp)
            return pd.read_csv(caminho_temp, sep=";", encoding="utf-8-sig")
    
        df = carregar_followups()
        if df.empty:
            st.warning("Nenhum dado disponível.")
            st.stop()
    
        st.markdown("### 📝 Digite sua pergunta sobre os relatórios de auditoria:")
        pergunta = st.text_input("Ex: Quais follow-ups em andamento no ambiente SAP em 2024?", key="pergunta_fup")
        enviar = st.button("📨 Enviar")
    
        if enviar:
            st.write("✅ Chat encaminhado para o agente!")
    
            if pergunta and isinstance(pergunta, str):
                prompt_chat = pergunta.strip().lower()
                st.write("✅ Chat recebido:", prompt_chat)
            else:
                st.error("❌ Nenhuma pergunta válida recebida.")
                st.stop()
    
            API_KEY = st.secrets["openai"]["api_key"]
            filtros = {}
    
            st.write("🔍 Analisando valores semelhantes nas colunas...")
    
            # Pré-processa valores únicos das colunas textuais
            valores_unicos = {}
            for col in df.select_dtypes(include="object").columns:
                valores_unicos[col] = df[col].astype(str).str.lower().str.strip().unique().tolist()
    
            # Tokeniza o prompt
            tokens = re.findall(r"\w+", prompt_chat)
    
            melhor_match = None
            melhor_coluna = None
    
            for token in tokens:
                for col, valores in valores_unicos.items():
                    match = get_close_matches(token, valores, n=1, cutoff=0.8)
                    if match:
                        melhor_match = match[0]
                        melhor_coluna = col
                        break
                if melhor_match:
                    break
    
            if melhor_match and melhor_coluna:
                filtros[melhor_coluna] = melhor_match
                st.write(f"📌 Valor interpretado: `{melhor_match}` na coluna `{melhor_coluna}`")
            else:
                st.warning("⚠️ Nenhuma coluna textual contém esse valor.")
    
            # Extrair ano
            ano_match = re.search(r"(\d{4})", prompt_chat)
            if ano_match:
                filtros["Ano"] = ano_match.group(1)
                st.write("📅 Ano identificado:", filtros["Ano"])
    
            # 📊 Aplicar filtros
            if filtros:
                df_filtrado = df.copy()
                for col in df_filtrado.select_dtypes(include="object").columns:
                    df_filtrado[col] = df_filtrado[col].astype(str).str.lower().str.strip()
    
                for k, v in filtros.items():
                    if k in df_filtrado.columns:
                        df_filtrado[k] = df_filtrado[k].astype(str)
                        df_filtrado = df_filtrado[df_filtrado[k].str.contains(str(v).lower().strip(), na=False)]
    
                if not df_filtrado.empty:
                    try:
                        dados_markdown = df_filtrado.fillna("").astype(str).to_markdown(index=False)
                    except ImportError:
                        st.warning("⚠️ Instale `tabulate` para melhor formatação: `pip install tabulate`")
                        dados_markdown = df_filtrado.fillna("").astype(str).to_csv(index=False, sep=";")
                else:
                    dados_markdown = "❌ Nenhum follow-up encontrado com os critérios especificados."
            else:
                try:
                    dados_markdown = df.fillna("").astype(str).to_markdown(index=False)
                except ImportError:
                    st.warning("⚠️ Instale `tabulate` para melhor formatação: `pip install tabulate`")
                    dados_markdown = df.fillna("").astype(str).to_csv(index=False, sep=";")
    
            # 🧠 Prompt para análise
            # Gera versão textual da base total
            df_completo_markdown = df.fillna("").astype(str).to_markdown(index=False)
            system_prompt = f"""
    Você é um analista sênior de auditoria interna com acesso a duas bases de dados:
    
    1. **Base completa (`df_completo`)**: contém todos os follow-ups de auditoria disponíveis.
    2. **Base filtrada (`dados_filtrados`)**: contém apenas os registros mais relevantes com base na pergunta do usuário.
    
    Sua missão é:
    - Responder com base **principalmente na base filtrada**, mas sempre **comparando com a base total** para validar sua resposta.
    - Na sua resposta não faça diferenciação entre os nomes das bases, faça referência à uma base única e não apresente informações conflitantes sobre as duas. Analise as duas bases e chegue na melhor resposta.
    - Trazer uma lista com a relação de relatórios identificados com base nos critérios especificados pelo usuário.
    - Informar quantos registros estão na base total e quantos foram filtrados.
    - Indicar percentuais, tendências ou discrepâncias entre as duas bases.
    - Fazer um resumo executivo no início sobre os principais assuntos críticos abordados na descrição dos follow ups.
    
    ---
    
    ### Base filtrada (`dados_filtrados`):
    {dados_markdown}
    
    ---
    
    ### Base completa (`df_completo`):
    {df_completo_markdown}
    
    ---
    
    ### Instruções finais:
    - Se a base filtrada estiver vazia, diga “Não há registros compatíveis”.
    - Seja direto, técnico e conciso.
    - Use contagens e percentuais sempre que possível.
    - Evite respostas genéricas, repetições ou rodeios.
    """
    
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt_chat}
                ],
                "temperature": 0.2
            }
    
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
    
            resposta_final = "❌ Nenhuma resposta gerada."
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                verify=False
            )
    
            if response.status_code == 200:
                resposta_final = response.json()["choices"][0]["message"]["content"]
            else:
                resposta_final = f"Erro na API: {response.status_code} - {response.text}"
    
            # 🔁 Revisor
            revisor_prompt = f"""
    Você é um revisor técnico. Reescreva a resposta com:
    - Clareza
    - Estrutura objetiva
    - Correção gramatical
    - Sem repetições
    
    Base de dados:
    {dados_markdown}
    """
    
            payload_revisor = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": revisor_prompt},
                    {"role": "user", "content": resposta_final}
                ],
                "temperature": 0.2
            }
    
            response_revisor = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload_revisor,
                verify=False
            )
    
            if response_revisor.status_code == 200:
                resposta_final = response_revisor.json()["choices"][0]["message"]["content"]
            else:
                resposta_final = f"(Erro ao revisar resposta: {response_revisor.status_code})\n\n{resposta_final}"
    
            # 💬 Exibir resposta e base
            st.markdown("### 💬 Resposta do Assistente")
            st.write(resposta_final)
    
            st.markdown("### 📋 Follow-ups encontrados:")
            if 'df_filtrado' in locals() and not df_filtrado.empty:
                st.dataframe(df_filtrado, use_container_width=True)
            else:
                st.info("Nenhum follow-up encontrado com os critérios aplicados.")
    else:
        st.warning("Você não tem permissão para acessar o chatbot, solicite ao time de auditoria!")
        
# Função para enviar e-mail mensal com follow-ups vencidos

def enviar_emails_followups_vencidos():
    df = carregar_followups()
    df.columns = df.columns.str.strip()

    df["Prazo"] = pd.to_datetime(df["Prazo"], errors="coerce")
    df_vencidos = df[(df["Status"].str.lower() != "concluído") & (df["Prazo"] < pd.Timestamp.today())]

    if df_vencidos.empty:
        st.info("✅ Nenhum follow-up vencido identificado para envio.")
        return

    responsaveis = df_vencidos["E-mail"].dropna().unique().tolist()

    for email in responsaveis:
        df_resp = df_vencidos[df_vencidos["E-mail"] == email]

        if df_resp.empty:
            continue

        corpo = f"""
        <p>Olá,</p>
        <p>Você possui os seguintes follow-ups vencidos:</p>
        <table border='1' cellpadding='4' cellspacing='0'>
            <tr><th>Título</th><th>Auditoria</th><th>Plano de Ação</th><th>Responsável</th><th>Prazo</th><th>Status</th></tr>
        """

        for _, row in df_resp.iterrows():
            corpo += f"<tr><td>{row['Titulo']}</td><td>{row['Auditoria']}</td><td>{row['Plano de Acao']}</td><td>{row['Responsavel']}</td><td>{row['Prazo'].date()}</td><td>{row['Status']}</td></tr>"

        corpo += """
        </table>
        <p>Por favor, atualize os registros no sistema ou entre em contato com a Auditoria Interna.</p>
        <p>Acesse o aplicativo para incluir evidências e acompanhar o andamento:</p>
        <p><a href='https://fup-auditoria.streamlit.app/' target='_blank'>🔗 fup-auditoria.streamlit.app</a></p>
        <br>
        <p>Atenciosamente,<br>Time de Auditoria</p>
        """

        try:
            remetente = st.secrets["email_user"]
            senha = st.secrets["email_pass"]

            msg = MIMEMultipart()
            msg['From'] = remetente
            msg['To'] = email
            msg['Subject'] = "📌 Follow-ups vencidos - Auditoria Interna"
            msg.attach(MIMEText(corpo, 'html'))

            with smtplib.SMTP('smtp.office365.com', 587) as server:
                server.starttls()
                server.login(remetente, senha)
                server.send_message(msg)

            st.success(f"📧 E-mail enviado para: {email}")
        except Exception as e:
            st.warning(f"Erro ao enviar para {email}: {e}")

# 🔁 Botão para envio manual

if st.session_state.username in admin_users:
    if st.sidebar.button("✉️ Enviar lembrete de follow-ups vencidos"):
        enviar_emails_followups_vencidos()
#-------------------------------------------------------------------- e-mail de follow ups a vencer
def enviar_emails_followups_a_vencer():
    df = carregar_followups()
    df.columns = df.columns.str.strip()
    df["Prazo"] = pd.to_datetime(df["Prazo"], errors="coerce")

    hoje = pd.Timestamp.today()
    limite = hoje + timedelta(days=30)

    df_a_vencer = df[
        (df["Status"].str.lower() != "concluído") &
        (df["Prazo"] >= hoje) &
        (df["Prazo"] <= limite)
    ]

    if df_a_vencer.empty:
        st.info("✅ Nenhum follow-up com prazo a vencer em 30 dias.")
        return

    responsaveis = df_a_vencer["E-mail"].dropna().unique().tolist()

    for email in responsaveis:
        df_resp = df_a_vencer[df_a_vencer["E-mail"] == email]
        if df_resp.empty:
            continue

        corpo = f"""
        <p>Olá,</p>
        <p>Você possui os seguintes follow-ups com prazo a vencer em até 30 dias:</p>
        <table border='1' cellpadding='4' cellspacing='0'>
            <tr><th>Título</th><th>Auditoria</th><th>Plano de Ação</th><th>Responsável</th><th>Prazo</th><th>Status</th></tr>
        """

        for _, row in df_resp.iterrows():
            corpo += f"<tr><td>{row['Titulo']}</td><td>{row['Auditoria']}</td><td>{row['Plano de Acao']}</td><td>{row['Responsavel']}</td><td>{row['Prazo'].date()}</td><td>{row['Status']}</td></tr>"

        corpo += """
        </table>
        <p>Por favor, antecipe ações necessárias e atualize o status no sistema.</p>
        <p>Acesse o aplicativo para mais detalhes:</p>
        <p><a href='https://fup-auditoria.streamlit.app/' target='_blank'>🔗 fup-auditoria.streamlit.app</a></p>
        <br>
        <p>Atenciosamente,<br>Time de Auditoria</p>
        """

        try:
            remetente = st.secrets["email_user"]
            senha = st.secrets["email_pass"]

            msg = MIMEMultipart()
            msg['From'] = remetente
            msg['To'] = email
            msg['Subject'] = "⏳ Follow-ups próximos do vencimento"
            msg.attach(MIMEText(corpo, 'html'))

            with smtplib.SMTP('smtp.office365.com', 587) as server:
                server.starttls()
                server.login(remetente, senha)
                server.send_message(msg)

            st.success(f"📧 E-mail enviado para: {email}")
        except Exception as e:
            st.warning(f"Erro ao enviar para {email}: {e}")
            
if st.session_state.username in admin_users:
    if st.sidebar.button("📅 Enviar lembrete de follow-ups a vencer"):
        enviar_emails_followups_a_vencer()
