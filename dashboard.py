import streamlit as st
import sqlite3
import pandas as pd
import datetime
import plotly.express as px

# =============================================================================
# Funções para conexão e criação das tabelas
# =============================================================================
def get_db_connection():
    conn = sqlite3.connect("apostas.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def criar_tabelas():
    conn = get_db_connection()
    # Tabela de usuários (mesmo que para uso pessoal, mantemos a estrutura)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            email TEXT PRIMARY KEY
        )
    """)
    # Tabela de apostas
    conn.execute("""
        CREATE TABLE IF NOT EXISTS apostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            metodo TEXT,
            data TEXT,
            campeonato TEXT,
            time_mandante TEXT,
            time_visitante TEXT,
            mercado TEXT,
            tipo_aposta TEXT,
            odd REAL,
            stake REAL,
            resultado TEXT,
            lucro REAL,
            FOREIGN KEY(email) REFERENCES usuarios(email)
        )
    """)
    conn.commit()
    conn.close()

criar_tabelas()

# =============================================================================
# Configuração: Para uso pessoal, definimos um email fixo.
# =============================================================================
user_email = "darleirodriguesalves0@gmail.com"  # Substitua pelo seu email, se desejar

# =============================================================================
# Dashboard Principal
# =============================================================================
st.title("⚽📊 Dashboard de Apostas Esportivas")
st.write("Bem-vindo ao seu dashboard de apostas!")

# =============================================================================
# Aba 1: Cadastro de Apostas
# =============================================================================
st.header("📝 Inserir Nova Aposta")
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
# Permite inserir stake com valores menores que 1 (ex.: 0.25)
stake = st.number_input("💵 Stake", min_value=0.01, format="%.2f")
resultado = st.selectbox("🎲 Resultado", ["Green ✅", "Red ❌"])

if st.button("✅ Adicionar Aposta"):
    # Cálculo do lucro conforme o tipo de aposta
    if tipo_aposta == "Back (A Favor)":
        lucro = (odd - 1) * stake if resultado == "Green ✅" else -stake
    else:
        lucro = stake if resultado == "Green ✅" else -((odd - 1) * stake)
    
    conn = get_db_connection()
    # Insere o usuário (se ainda não existir)
    conn.execute("INSERT OR IGNORE INTO usuarios (email) VALUES (?)", (user_email,))
    # Insere a aposta
    conn.execute("""
        INSERT INTO apostas (email, metodo, data, campeonato, time_mandante, time_visitante, mercado, tipo_aposta, odd, stake, resultado, lucro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_email,
        metodo,
        data_aposta.strftime("%Y-%m-%d"),
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
    conn.close()
    st.success("✅ Aposta adicionada com sucesso!")

# =============================================================================
# Seção: Exclusão de Apostas
# =============================================================================
st.header("❌ Excluir Aposta")

# Recupera as apostas do usuário
conn = get_db_connection()
query = """
    SELECT id, data, campeonato, time_mandante, time_visitante, lucro 
    FROM apostas 
    WHERE email = ?
    ORDER BY data DESC
"""
df_excluir = pd.read_sql_query(query, conn, params=(user_email,))
conn.close()

if not df_excluir.empty:
    # Converte a coluna 'data' para o formato de data
    df_excluir["data"] = pd.to_datetime(df_excluir["data"]).dt.date
    # Cria uma coluna para exibição das apostas
    df_excluir["exibir"] = df_excluir.apply(
        lambda row: f"ID {row['id']} - {row['data']} - {row['campeonato']} - {row['time_mandante']} x {row['time_visitante']} - Lucro: {row['lucro']}", 
        axis=1
    )
    opcoes = df_excluir["exibir"].tolist()
    aposta_selecionada = st.selectbox("Selecione a aposta para excluir", opcoes)
    # Mapeia a string exibida para o ID correspondente
    id_mapping = dict(zip(df_excluir["exibir"], df_excluir["id"]))
    aposta_id = id_mapping[aposta_selecionada]
    if st.button("Excluir Aposta"):
        conn = get_db_connection()
        conn.execute("DELETE FROM apostas WHERE id = ?", (aposta_id,))
        conn.commit()
        conn.close()
        st.success("Aposta excluída com sucesso!")
else:
    st.info("Nenhuma aposta registrada para exclusão.")

# =============================================================================
# Aba 2: Métricas & Análises
# =============================================================================
st.header("📊 Desempenho das Apostas")

conn = get_db_connection()
query = "SELECT * FROM apostas WHERE email = ?"
df = pd.read_sql_query(query, conn, params=(user_email,))
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
        
        # Exibição dos dados filtrados
        df_exibicao = df_filtrado.copy()
        df_exibicao["data"] = df_exibicao["data"].dt.date
        df_exibicao = df_exibicao[["data", "campeonato", "time_mandante", "time_visitante", "odd", "resultado", "lucro"]]
        df_exibicao = df_exibicao.rename(columns={
            "data": "Data",
            "time_mandante": "Mandante",
            "time_visitante": "Visitante"
        })
        st.dataframe(df_exibicao)
        
        total_apostas = len(df_filtrado)
        green_apostas = len(df_filtrado[df_filtrado["resultado"] == "Green ✅"])
        # Taxa de acerto em porcentagem
        taxa_acerto = (green_apostas / total_apostas) * 100 if total_apostas > 0 else 0
        
        # Cálculo da Odd Mínima de Entrada:
        winrate_fraction = (green_apostas / total_apostas) if total_apostas > 0 else 0
        if winrate_fraction > 0:
            odd_minima = round(1 / winrate_fraction, 2)
        else:
            odd_minima = None

        colA, colB, colC = st.columns(3)
        colA.metric("📊 Taxa de Acerto", f"{taxa_acerto:.2f}%")
        colB.metric("💵 Lucro Acumulado", f"{df_filtrado['lucro'].sum():.2f} unidades")
        if odd_minima is not None:
            colC.metric("🎯 Odd Mínima", f"{odd_minima:.2f}")
        else:
            colC.metric("🎯 Odd Mínima", "N/A")
        
        # Gráfico do Lucro Acumulado por Período
        df_agrupado = df_filtrado.groupby("Periodo")["lucro"].sum().reset_index()
        df_agrupado["Lucro Acumulado"] = df_agrupado["lucro"].cumsum()
        fig = px.line(df_agrupado, x="Periodo", y="Lucro Acumulado", title="📈 Lucro Acumulado por Período")
        st.plotly_chart(fig)
    else:
        st.warning("Nenhuma aposta encontrada com os filtros selecionados.")
else:
    st.info("Nenhuma aposta registrada ainda.")

# =============================================================================
# Aba 3: Estatísticas Detalhadas
# =============================================================================
st.header("📊 Estatísticas Detalhadas")

conn = get_db_connection()
query = "SELECT * FROM apostas WHERE email = ?"
df_total = pd.read_sql_query(query, conn, params=(user_email,))
conn.close()

if not df_total.empty:
    total_investido = df_total["stake"].sum()
    lucro_total = df_total["lucro"].sum()
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
