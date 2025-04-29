import streamlit as st
import pandas as pd
from datetime import datetime, date
import yagmail
from io import BytesIO
from pathlib import Path
import plotly.express as px
import os

st.set_page_config(layout = 'wide')

st.sidebar.text(f"Diretório atual: {os.getcwd()}")

caminho_csv = r"C:\Users\cvieira\Desktop\Claudio\Area de Trabalho\Dashboards\Automacao\Fup\followups.csv"
admin_users = ["cvieira", "amendonca", "mathayde", "bella"]

def enviar_email_gmail(destinatario, assunto, corpo_html):
    try:
        # ✅ Substitua pelo seu Gmail e senha de app:
        yag = yagmail.SMTP("pvclaudio95@gmail.com", "cner eaea afpi fuyb")
        yag.send(to=destinatario, subject=assunto, contents=corpo_html)
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False
        
def enviar_email(destinatario, assunto, corpo_html):
    try:
        import yagmail
        yag = yagmail.SMTP("pvclaudio95@gmail.com", "cner eaea afpi fuyb")
        yag.send(to=destinatario, subject=assunto, contents=corpo_html)
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
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
    "Visualizar Evidências"
])

# --- Conteúdo das páginas ---

if menu == "Dashboard":
    st.title("📊 Painel de KPIs")
    
    try:
        df = pd.read_csv(caminho_csv)
        usuario_logado = st.session_state.username
        nome_usuario = users[usuario_logado]["name"]
    
        # Filtra os dados: admins veem tudo
        if usuario_logado not in admin_users:
            df = df[df["Responsavel"].str.lower() == nome_usuario.lower()]
    
        if df.empty:
            st.info("Nenhum dado disponível para exibir KPIs.")
            st.stop()
    
        # Conversões
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
    
        # --- Gráfico de pizza: Status ---
        st.subheader("📌 Distribuição por Status")
        fig_status = px.pie(
            df,
            names="Status",
            title="Distribuição dos Follow-ups por Status",
            hole=0.4
        )
        st.plotly_chart(fig_status, use_container_width=True)
    
        # --- Gráfico de barras: Auditoria ---
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
    
        # --- Gráfico de linha: Ano ---
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
    
    except FileNotFoundError:
        st.warning("Arquivo followups.csv não encontrado.")

elif menu == "Meus Follow-ups":
    st.title("📁 Meus Follow-ups")
    st.info("Esta seção exibirá os follow-ups atribuídos a você.")
    
    try:
        df = pd.read_csv(caminho_csv)
    
        # Pega o username logado
        usuario_logado = st.session_state.username
        nome_usuario = users[usuario_logado]["name"]
    
        # Se não for admin, filtra pelo usuário
        if usuario_logado not in admin_users:
            df = df[df["Responsavel"].str.lower() == nome_usuario.lower()]
    
        # Conversões
        df["Prazo"] = pd.to_datetime(df["Prazo"])
        df["Ano"] = df["Ano"].astype(str)
    
        # Filtros Sidebar
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
    
        # Aplicar filtros
        if auditoria_selecionada != "Todos":
            df = df[df["Auditoria"] == auditoria_selecionada]
    
        if status_selecionado != "Todos":
            df = df[df["Status"] == status_selecionado]
    
        if ano_selecionado != "Todos":
            df = df[df["Ano"] == ano_selecionado]
    
        df = df[(df["Prazo"].dt.date >= prazo_inicial) & (df["Prazo"].dt.date <= prazo_final)]
    
        # Ordenar
        df = df.sort_values(by="Prazo")
    
        # Mostrar Follow-ups
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.success(f"Total Follow Ups: {len(df)}")
    
            # Área de edição de Status
            st.subheader("🛠️ Atualizar / Excluir Follow-up por Índice")

            # Exibe os índices disponíveis da tabela atual
            indices_disponiveis = df.index.tolist()
            indice_selecionado = st.selectbox("Selecione o índice para edição", indices_disponiveis)
            
            # Mostrar dados da linha selecionada
            linha = df.loc[indice_selecionado]
            st.markdown(f"""
            🔎 **Título:** {linha['Titulo']}  
            📅 **Prazo:** {linha['Prazo'].strftime('%d/%m/%Y')}  
            👤 **Responsável:** {linha['Responsavel']}  
            📌 **Status:** {linha['Status']}
            """)
            
            # Exibir colunas editáveis
            colunas_editaveis = [col for col in df.columns if col not in ["Prazo", "Data_Conclusao"]]
            coluna_escolhida = st.selectbox("Selecione a coluna para alterar", colunas_editaveis)
            
            # Mostrar valor atual e campo para novo valor
            valor_atual = linha[coluna_escolhida]
            novo_valor = st.text_input(f"Valor atual de '{coluna_escolhida}':", value=str(valor_atual))
            
            # Botão para atualizar valor
            if novo_valor.strip() != str(valor_atual).strip():
                if st.button("💾 Atualizar campo"):
                    df_original = pd.read_csv(caminho_csv)
                    df_original.at[indice_selecionado, coluna_escolhida] = novo_valor.strip()
                    df_original.to_csv(caminho_csv, index=False)
                    st.success(f"'{coluna_escolhida}' atualizado com sucesso.")
                    st.rerun()
            
            # Exclusão (apenas admin)
            if usuario_logado in admin_users:
                if st.button("🗑️ Excluir este follow-up"):
                    df_original = pd.read_csv(caminho_csv)
                    df_original = df_original.drop(index=indice_selecionado)
                    df_original.to_csv(caminho_csv, index=False)
                    st.success("Follow-up excluído com sucesso.")
                    st.rerun()
    
            # Exportar para Excel
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
    
    except FileNotFoundError:
        st.warning("Nenhum follow-up cadastrado ainda.")

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
            df = pd.read_csv(caminho_csv)
        except FileNotFoundError:
            df = pd.DataFrame()
    
        df = pd.concat([df, pd.DataFrame([novo])], ignore_index=True)
        df.to_csv(caminho_csv, index=False)
    
        st.success("✅ Follow-up salvo com sucesso!")
    
        # Gera corpo do e-mail SEM 'if' aqui
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
    
        # Só tenta enviar se email não estiver vazio
        if email:
            sucesso_envio = enviar_email_gmail(
                destinatario=email,
                assunto=f"[Follow-up] Nova Atribuição: {titulo}",
                corpo_html=corpo
            )
            if sucesso_envio:
                st.success("📧 E-mail de notificação enviado com sucesso!")

elif menu == "Enviar Evidências":
    st.title("📌 Enviar Evidências")
    st.info("Aqui você poderá enviar comprovantes e observações para follow-ups.")

    try:
        df = pd.read_csv(caminho_csv)

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

            try:
                indice_str = str(idx)
                pasta_destino = Path(
                    fr"C:\Users\cvieira\Desktop\Claudio\Area de Trabalho\Dashboards\Automacao\Fup\evidencias\indice_{indice_str}"
                )
                pasta_destino.mkdir(parents=True, exist_ok=True)
                st.info(f"Pasta criada ou existente: {pasta_destino}")
            except Exception as e:
                st.error(f"Erro ao criar pasta de evidências: {e}")
                st.stop()

            nomes_arquivos = []
            for arquivo in arquivos:
                try:
                    caminho = pasta_destino / arquivo.name
                    with open(caminho, "wb") as f:
                        f.write(arquivo.getbuffer())
                    nomes_arquivos.append(arquivo.name)
                except Exception as e:
                    st.error(f"Erro ao salvar arquivo '{arquivo.name}': {e}")

            # Observação opcional
            if observacao.strip():
                try:
                    with open(pasta_destino / "observacao.txt", "w", encoding="utf-8") as f:
                        f.write(observacao.strip())
                except Exception as e:
                    st.error(f"Erro ao salvar observação: {e}")

            # Registro em log
            try:
                log_path = Path(
                    r"C:\Users\cvieira\Desktop\Claudio\Area de Trabalho\Dashboards\Automacao\Fup\log_evidencias.csv"
                )
                from datetime import datetime

                log_data = {
                    "indice": idx,
                    "titulo": linha["Titulo"],
                    "responsavel": linha["Responsavel"],
                    "arquivos": "; ".join(nomes_arquivos),
                    "observacao": observacao,
                    "data_envio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "enviado_por": nome_usuario,
                }
                log_df = pd.DataFrame([log_data])
                if log_path.exists():
                    log_df.to_csv(log_path, mode="a", header=False, index=False)
                else:
                    log_df.to_csv(log_path, index=False)
            except Exception as e:
                st.error(f"Erro ao registrar evidência no log: {e}")

            st.success("✅ Evidência enviada com sucesso!")

            # ✅ ENVIA E-MAIL usando função padronizada
            corpo = f"""
            <p>🕵️ Evidência enviada para o follow-up:</p>
            <ul>
                <li><b>Índice:</b> {idx}</li>
                <li><b>Título:</b> {linha['Titulo']}</li>
                <li><b>Responsável:</b> {linha['Responsavel']}</li>
                <li><b>Arquivos:</b> {"; ".join(nomes_arquivos)}</li>
                <li><b>Data:</b> {datetime.now().strftime("%d/%m/%Y %H:%M")}</li>
            </ul>
            <p>Evidências salvas na pasta: <b>{pasta_destino}</b></p>
            """

            sucesso_envio = enviar_email(
                destinatario="cvieira@prio3.com.br",
                assunto=f"[Evidência] Follow-up #{idx} - {linha['Titulo']}",
                corpo_html=corpo
            )
            if sucesso_envio:
                st.success("📧 Notificação enviada ao time de auditoria!")

    except FileNotFoundError:
        st.warning("Arquivo followups.csv não encontrado.")

elif menu == "Visualizar Evidências":
    st.title("📂 Visualização de Evidências")

    pasta_base = Path(r"C:\Users\cvieira\Desktop\Claudio\Area de Trabalho\Dashboards\Automacao\Fup\evidencias")

    if not pasta_base.exists():
        st.warning("Nenhuma evidência enviada ainda.")
        st.stop()

    # Lista pastas como "indice_1", "indice_2", etc.
    pastas = sorted([p for p in pasta_base.iterdir() if p.is_dir()])
    if not pastas:
        st.info("Nenhuma evidência encontrada.")
        st.stop()

    indice_selecionado = st.selectbox("Selecione o índice do follow-up:", [p.name.split("_")[1] for p in pastas])
    pasta = pasta_base / f"indice_{indice_selecionado}"

    st.subheader(f"Evidências para Follow-up #{indice_selecionado}")

    arquivos = list(pasta.glob("*"))
    if not arquivos:
        st.info("Nenhum arquivo enviado para esse follow-up.")
    else:
        for arq in arquivos:
            if arq.name.lower() == "observacao.txt":
                with open(arq, "r", encoding="utf-8") as f:
                    st.markdown("**📝 Observação:**")
                    st.info(f.read())
            else:
                with open(arq, "rb") as f:
                    btn_label = f"📎 Baixar: {arq.name}"
                    st.download_button(label=btn_label, data=f, file_name=arq.name)

