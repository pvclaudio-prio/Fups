import streamlit as st
import pandas as pd
from datetime import date
import yagmail
from io import BytesIO
from pathlib import Path

st.set_page_config(layout = 'wide')

def enviar_email_gmail(destinatario, assunto, corpo_html):
    try:
        # ✅ Substitua pelo seu Gmail e senha de app:
        yag = yagmail.SMTP("pvclaudio95@gmail.com", "cner eaea afpi fuyb")
        yag.send(to=destinatario, subject=assunto, contents=corpo_html)
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False
    
# --- Usuários e autenticação simples ---
users = {
    "cvieira": {"name": "Claudio Vieira", "password": "1234"},
    "auditoria": {"name": "Time Auditoria", "password": "auditoria"}
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
    "Enviar Evidências"
])

# --- Conteúdo das páginas ---
if menu == "Dashboard":
    st.title("📊 Painel de KPIs")
    st.info("Aqui você pode exibir gráficos, contadores e indicadores gerais.")

elif menu == "Meus Follow-ups":
    st.title("📁 Meus Follow-ups")
    st.info("Esta seção exibirá os follow-ups atribuídos a você.")
    
    try:
        df = pd.read_csv("followups.csv")
    
        # Pega o username logado
        usuario_logado = st.session_state.username
        nome_usuario = users[usuario_logado]["name"]
    
        # Lista de usuários com acesso completo
        admin_users = ["cvieira", "amendonca", "mathayde"]
    
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
                    df_original = pd.read_csv("followups.csv")
                    df_original.at[indice_selecionado, coluna_escolhida] = novo_valor.strip()
                    df_original.to_csv("followups.csv", index=False)
                    st.success(f"'{coluna_escolhida}' atualizado com sucesso.")
                    st.rerun()
            
            # Exclusão (apenas admin)
            if usuario_logado in admin_users:
                if st.button("🗑️ Excluir este follow-up"):
                    df_original = pd.read_csv("followups.csv")
                    df_original = df_original.drop(index=indice_selecionado)
                    df_original.to_csv("followups.csv", index=False)
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
            df = pd.read_csv("followups.csv")
        except FileNotFoundError:
            df = pd.DataFrame()

        df = pd.concat([df, pd.DataFrame([novo])], ignore_index=True)
        df.to_csv("followups.csv", index=False)

        st.success("✅ Follow-up salvo com sucesso!")


    # Envia e-mail
    if email:
        corpo = f"""
        <p>Olá <b>{responsavel}</b>,</p>
        <p>Um novo follow-up foi cadastrado com os seguintes dados:</p>
        <ul>
            <li><b>Título:</b> {titulo}</li>
            <li><b>Ambiente:</b> {ambiente}</li>
            <li><b>Ano:</b> {ano}</li>
            <li><b>Prazo:</b> {prazo.strftime('%d/%m/%Y')}</li>
            <li><b>Status:</b> {status}</li>
        </ul>
        <p>Acesse o sistema para mais detalhes.</p>
        """
        if enviar_email_gmail(email, f"[Follow-up] {titulo}", corpo):
            st.success(f"E-mail enviado para {responsavel}!")

elif menu == "Enviar Evidências":
    st.title("📌 Enviar Evidências")
    st.info("Aqui você poderá enviar comprovantes e observações para follow-ups.")
    
    try:
        df = pd.read_csv("followups.csv")

        usuario_logado = st.session_state.username
        nome_usuario = users[usuario_logado]["name"]

        if usuario_logado not in ["cvieira", "amendonca", "mathayde"]:
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

            from pathlib import Path
            from datetime import datetime
            import os

            pasta_destino = Path(f"evidencias/indice_{idx}")
            pasta_destino.mkdir(parents=True, exist_ok=True)

            nomes_arquivos = []
            for arquivo in arquivos:
                caminho = pasta_destino / arquivo.name
                with open(caminho, "wb") as f:
                    f.write(arquivo.getbuffer())
                nomes_arquivos.append(arquivo.name)

            if observacao.strip():
                with open(pasta_destino / "observacao.txt", "w", encoding="utf-8") as f:
                    f.write(observacao.strip())

            # Registro em log
            log_path = Path("log_evidencias.csv")
            log_data = {
                "indice": idx,
                "titulo": linha["Titulo"],
                "responsavel": linha["Responsavel"],
                "arquivos": "; ".join(nomes_arquivos),
                "observacao": observacao,
                "data_envio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "enviado_por": nome_usuario
            }
            log_df = pd.DataFrame([log_data])
            if log_path.exists():
                log_df.to_csv(log_path, mode='a', header=False, index=False)
            else:
                log_df.to_csv(log_path, index=False)

            st.success("Evidência enviada com sucesso!")

            # Envia e-mail à auditoria
            try:
                yag = yagmail.SMTP("pvclaudio95@gmail.com", "cner eaea afpi fuyb")

                corpo = f"""
                <p>🕵️ Evidência enviada para o follow-up:</p>
                <ul>
                    <li><b>Índice:</b> {idx}</li>
                    <li><b>Título:</b> {linha['Titulo']}</li>
                    <li><b>Responsável:</b> {linha['Responsavel']}</li>
                    <li><b>Arquivos:</b> {"; ".join(nomes_arquivos)}</li>
                    <li><b>Data:</b> {datetime.now().strftime("%d/%m/%Y %H:%M")}</li>
                </ul>
                <p>Evidências salvas na pasta <b>evidencias/indice_{idx}/</b>.</p>
                """

                yag.send(
                    to="cvieira@prio3.com.br",
                    subject=f"[Evidência] Follow-up #{idx} - {linha['Titulo']}",
                    contents=corpo
                )
                st.success("Notificação enviada ao time de auditoria!")
            except Exception as e:
                st.error(f"Erro ao enviar e-mail: {e}")

    except FileNotFoundError:
        st.warning("Arquivo followups.csv não encontrado.")
