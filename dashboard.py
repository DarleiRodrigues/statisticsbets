import streamlit as st
import os
import psycopg2
import pandas as pd
import datetime
import plotly.express as px

# =============================================================================
# Funções de Conexão e Criação de Tabelas no PostgreSQL
# =============================================================================

def get_db_connection():
    try:
        db_url = st.secrets["DATABASE_URL"]
    except Exception as e:
        st.error("A variável de ambiente DATABASE_URL não está configurada!")
        st.stop()
    # Opcional: exiba (ou log) parte do valor para debug (cuidado para não expor dados sensíveis)
    st.write("Conectando com URL: ", db_url[:30] + "...")
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        st.error("Erro na conexão com o banco de dados: " + str(e))
        st.stop()

def criar_tabelas():
    conn = get_db_connection()
    cur = conn.cursor()
    # Tabela de usuários (usando o email como chave primária)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            email TEXT PRIMARY KEY
        );
    """)
    # Tabela de apostas (cada aposta é associada a um usuário por meio do email)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS apostas (
            id SERIAL PRIMARY KEY,
            email TEXT REFERENCES usuarios(email),
            metodo TEXT,
            data DATE,
            campeonato TEXT,
            time_mandante TEXT,
            time_visitante TEXT,
            mercado TEXT,
            tipo_aposta TEXT,
            odd REAL,
            stake REAL,
            resultado TEXT,
            lucro REAL
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

criar_tabelas()

# =============================================================================
# Sistema de Login Simples utilizando apenas o email
# =============================================================================

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'email' not in st.session_state:
    st.session_state.email = None

if not st.session_state.logged_in:
    st.subheader("Login")
    email_input = st.text_input("Email")
    if st.button("Entrar"):
        conn = get_db_connection()
        cur = conn.cursor()
        # Verifica se o email já está cadastrado
        cur.execute("SELECT * FROM usuarios WHERE email = %s", (email_input,))
        user = cur.fetchone()
        if not user:
            # Se não existir, insere o novo email no banco
            cur.execute("INSERT INTO usuarios (email) VALUES (%s)", (email_input,))
            conn.commit()
        cur.close()
        conn.close()
        st.session_state.logged_in = True
        st.session_state.email = email_input
        st.success("Login realizado com sucesso!")
    st.stop()  # Impede que o app continue sem login

# =============================================================================
# Dashboard – Após o Login
# =============================================================================

st.title("⚽📊 Dashboard de Apostas Esportivas")
st.write(f"Bem-vindo, **{st.session_state.email}**!")

tabs = st.tabs(["🏆 Cadastro de Apostas", "📊 Métricas & Análises", "📈 Estatísticas Detalhadas"])

# -----------------------------------------------------------------------------
# Aba 1: Cadastro de Apostas
# -----------------------------------------------------------------------------
with tabs[0]:
    st.subheader("📝 Inserir Nova Aposta")
    metodo = st.text_input("Nome do Método", value="Método Padrão")
    
    col1, col2 = st.columns(2)
    with col1:
        data_aposta = st.date_input("📅 Data da Aposta", value=datetime.date.today())
        campeonato = st.text_input("🏆 Campeonato")
        time_mandante = st.text_input("🏠 Time Mandante")
    with col2:
        time_visitante = st.text_input("🚀 Time Visitante")
        mercado = st.selectbox("🎯 Mercado", ["Over 1.5", "Lay Visitante", "Lay 0x1", "Target Futebol", "Target Basquete"])
    
    tipo_aposta = st.selectbox("💰 Tipo de Aposta", ["Back (A Favor)", "Lay (Contra)"])
    odd = st.number_input("📈 Odd", min_value=1.0, format="%.2f")
    stake = st.number_input("💵 Stake", min_value=1.0, format="%.2f")
    resultado = st.selectbox("🎲 Resultado", ["Green ✅", "Red ❌"])
    
    if st.button("✅ Adicionar Aposta"):
        if tipo_aposta == "Back (A Favor)":
            lucro = (odd - 1) * stake if resultado == "Green ✅" else -stake
        else:
            lucro = stake if resultado == "Green ✅" else -((odd - 1) * stake)
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO apostas (email, metodo, data, campeonato, time_mandante, time_visitante, mercado, tipo_aposta, odd, stake, resultado, lucro)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            st.session_state.email,
            metodo,
            data_aposta,
            campeonato,
            time_mandante,
            time_visitante,
            mercado,
            tipo_aposta,
            odd,
            stake,
            resultado,
            lucro
        ))
        conn.commit()
        cur.close()
        conn.close()
        st.success("✅ Aposta adicionada com sucesso!")

# -----------------------------------------------------------------------------
# Aba 2: Métricas & Análises
# -----------------------------------------------------------------------------
with tabs[1]:
    st.subheader("📊 Desempenho das Apostas")
    conn = get_db_connection()
    query = "SELECT * FROM apostas WHERE email = %s"
    df = pd.read_sql_query(query, conn, params=(st.session_state.email,))
    conn.close()
    
    if not df.empty:
        df["data"] = pd.to_datetime(df["data"])
        st.markdown("### Filtros")
        col1, col2, col3 = st.columns(3)
        data_min = df["data"].min().date()
        data_max = df["data"].max().date()
        data_inicio = col1.date_input("Data Início", value=data_min, min_value=data_min, max_value=data_max)
        data_fim = col2.date_input("Data Fim", value=data_max, min_value=data_min, max_value=data_max)
        agrupamento = col3.selectbox("Agrupar por", options=["Dia", "Semana", "Mês", "Ano"])
        
        # Filtro por Mercado
        mercados_unicos = df["mercado"].unique().tolist()
        mercado_opcoes = ["Todos"] + mercados_unicos
        mercado_selecionado = st.selectbox("Filtrar por Mercado", options=mercado_opcoes)
        
        df_filtrado = df[(df["data"].dt.date >= data_inicio) & (df["data"].dt.date <= data_fim)]
        if mercado_selecionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado["mercado"] == mercado_selecionado]
        
        if not df_filtrado.empty:
            df_filtrado = df_filtrado.sort_values("data")
            if agrupamento == "Dia":
                df_filtrado["Periodo"] = df_filtrado["data"].dt.date
            elif agrupamento == "Semana":
                df_filtrado["Periodo"] = df_filtrado["data"].dt.to_period("W").apply(lambda r: r.start_time)
            elif agrupamento == "Mês":
                df_filtrado["Periodo"] = df_filtrado["data"].dt.to_period("M").dt.to_timestamp()
            elif agrupamento == "Ano":
                df_filtrado["Periodo"] = df_filtrado["data"].dt.to_period("Y").dt.to_timestamp()

            # Preparar DataFrame para exibição com as colunas desejadas
            df_exibicao = df_filtrado.copy()
            df_exibicao["data"] = df_exibicao["data"].dt.date
            df_exibicao = df_exibicao[["data", "campeonato", "time_mandante", "time_visitante", "odd", "resultado", "lucro"]]
            df_exibicao = df_exibicao.rename(columns={
                "data": "Data",
                "time_mandante": "Mandante",
                "time_visitante": "Visitante"
            })

            df_exibicao = df_exibicao.reset_index(drop=True)
            df_exibicao.index = df_exibicao.index + 1  # começa em 1

            # Agora o DataFrame terá índice de 1 até N
            # Mas 'st.dataframe' ainda mostrará essa coluna.
            if len(df_exibicao) > 6:
                st.dataframe(df_exibicao, height=200)
            else:
                st.dataframe(df_exibicao)
            
            total_apostas = len(df_filtrado)
            green_apostas = len(df_filtrado[df_filtrado["resultado"] == "Green ✅"])
            taxa_acerto = (green_apostas / total_apostas) * 100 if total_apostas > 0 else 0
            
            colA, colB = st.columns(2)
            colA.metric("📊 Taxa de Acerto", f"{taxa_acerto:.2f}%")
            colB.metric("💵 Lucro Acumulado", f"{df_filtrado['lucro'].sum():.2f} unidades")
            
            df_agrupado = df_filtrado.groupby("Periodo")["lucro"].sum().reset_index()
            df_agrupado["Lucro Acumulado"] = df_agrupado["lucro"].cumsum()
            fig = px.line(df_agrupado, x="Periodo", y="Lucro Acumulado", title="📈 Lucro Acumulado por Período")
            st.plotly_chart(fig)
        else:
            st.warning("Nenhuma aposta encontrada com os filtros selecionados.")
    else:
        st.info("Nenhuma aposta registrada ainda.")

# -----------------------------------------------------------------------------
# Aba 3: Estatísticas Detalhadas
# -----------------------------------------------------------------------------
with tabs[2]:
    st.subheader("📊 Estatísticas Detalhadas")
    conn = get_db_connection()
    query = "SELECT * FROM apostas WHERE email = %s"
    df_total = pd.read_sql_query(query, conn, params=(st.session_state.email,))
    conn.close()
    
    if not df_total.empty:
        total_investido = df_total["stake"].sum()
        lucro_total = df_total["lucro"].sum()
        # Corrigindo: usar total_investido na condição ou definir total_apostas
        ROI = (lucro_total / total_investido) * 100 if total_investido > 0 else 0
        st.metric("📊 ROI (Retorno sobre Investimento)", f"{ROI:.2f}%")
        
        lucro_por_campeonato = df_total.groupby("campeonato")["lucro"].sum().reset_index()
        fig1 = px.bar(lucro_por_campeonato, x="campeonato", y="lucro", title="📊 Lucro por Campeonato")
        st.plotly_chart(fig1)
        
        lucro_por_metodo = df_total.groupby("metodo")["lucro"].sum().reset_index()
        fig2 = px.bar(lucro_por_metodo, x="metodo", y="lucro", title="📊 Lucro por Método")
        st.plotly_chart(fig2)
    else:
        st.warning("Nenhuma aposta registrada ainda.")

# Excluir todas as apostas de um usuario

st.subheader("❌ Excluir todas as apostas")
if st.button("Excluir minhas apostas"):
    confirm = st.checkbox("Confirmo que desejo excluir todas as minhas apostas.")
    if confirm:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM apostas WHERE email = %s", (st.session_state.email,))
        conn.commit()
        cur.close()
        conn.close()
        st.success("Todas as apostas foram excluídas com sucesso!")
    else:
        st.warning("Marque a caixa para confirmar a exclusão.")

