import streamlit as st
import sqlite3
import pandas as pd
import datetime
import plotly.express as px

# =============================================================================
# Funções de conexão e criação de tabelas
# =============================================================================
def get_db_connection():
    conn = sqlite3.connect("apostas.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def criar_tabelas():
    conn = get_db_connection()
    # Tabela de usuários (mantida para estrutura, mesmo que para uso pessoal)
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
    # Tabela de métodos
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metodos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE,
            esporte TEXT,
            mercado TEXT
        )
    """)
    conn.commit()
    conn.close()

criar_tabelas()

# =============================================================================
# Configuração – Uso pessoal (email fixo)
# =============================================================================
user_email = "darleirodriguesalves0@gmail.com"  # Altere se desejar

# =============================================================================
# Barra Lateral – Navegação entre páginas
# =============================================================================
st.sidebar.title("Menu")
page = st.sidebar.radio("Selecione a página:", ["Registro de Aposta", "Relatórios e Estatísticas"])

# =============================================================================
# Custom CSS para melhorar a aparência (caso necessário)
# =============================================================================
st.markdown(
    """
    <style>
    .delete-button {
        background-color: #ff4b4b;
        color: white;
        border: none;
        padding: 5px 10px;
        border-radius: 4px;
    }
    .delete-button:hover {
        background-color: #ff0000;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# Página: Registro de Aposta (com aba para Cadastro de Métodos)
# =============================================================================
if page == "Registro de Aposta":
    st.title("Registro de Aposta")
    st.write("Utilize esta página para registrar novas apostas e cadastrar métodos.")

    # Cria abas para: Nova Aposta e Cadastro de Métodos
    tabs = st.tabs(["Nova Aposta", "Cadastro de Métodos"])
    
    # -------------------------------------------------------------------------
    # Aba: Nova Aposta
    # -------------------------------------------------------------------------
    with tabs[0]:
        st.header("Nova Aposta")
        
        # Consulta os métodos cadastrados e exibe um selectbox
        conn = get_db_connection()
        metodos_df = pd.read_sql_query("SELECT nome FROM metodos ORDER BY nome", conn)
        conn.close()
        if not metodos_df.empty:
            metodo_options = metodos_df["nome"].tolist()
            metodo_selecionado = st.selectbox("Selecione o Método", options=metodo_options)
        else:
            st.warning("Nenhum método cadastrado. Cadastre um método na aba 'Cadastro de Métodos'.")
            metodo_selecionado = None
        
        # Data da aposta
        data_aposta = st.date_input("📅 Data da Aposta", value=datetime.date.today())
        
        # Função para buscar valores únicos já registrados (para autocompletar)
        def get_unique_values(col_name):
            conn = get_db_connection()
            query = f"SELECT DISTINCT {col_name} FROM apostas WHERE email = ? AND {col_name} != ''"
            df_temp = pd.read_sql_query(query, conn, params=(user_email,))
            conn.close()
            valores = df_temp[col_name].dropna().unique().tolist()
            return sorted(valores)
        
        # Campeonato – permite selecionar um valor já usado ou digitar um novo
        camp_options = get_unique_values("campeonato")
        camp_choice = st.selectbox("🏆 Campeonato", options=["-- Selecione --", "Outro"] + camp_options)
        if camp_choice in ["-- Selecione --", "Outro"]:
            campeonato = st.text_input("Digite o Campeonato")
        else:
            campeonato = camp_choice
        
        # Time Mandante
        time_mandante_options = get_unique_values("time_mandante")
        time_mandante_choice = st.selectbox("🏠 Time Mandante", options=["-- Selecione --", "Outro"] + time_mandante_options)
        if time_mandante_choice in ["-- Selecione --", "Outro"]:
            time_mandante = st.text_input("Digite o Time Mandante")
        else:
            time_mandante = time_mandante_choice
        
        # Time Visitante
        time_visitante_options = get_unique_values("time_visitante")
        time_visitante_choice = st.selectbox("🚀 Time Visitante", options=["-- Selecione --", "Outro"] + time_visitante_options)
        if time_visitante_choice in ["-- Selecione --", "Outro"]:
            time_visitante = st.text_input("Digite o Time Visitante")
        else:
            time_visitante = time_visitante_choice
        
        # Mercado: adiciona a opção "Bingo" aos mercados já existentes
        mercados = ["Over 1.5", "Lay Visitante", "Lay 0x1", "Target Futebol", "Target Basquete", "Bingo"]
        mercado = st.selectbox("🎯 Mercado", options=mercados)
        
        tipo_aposta = st.selectbox("💰 Tipo de Aposta", ["Back (A Favor)", "Lay (Contra)"])
        odd = st.number_input("📈 Odd", min_value=1.0, format="%.2f")
        stake = st.number_input("💵 Stake", min_value=0.01, format="%.2f")
        resultado = st.selectbox("🎲 Resultado", ["Green ✅", "Red ❌"])
        
        if st.button("✅ Adicionar Aposta"):
            if metodo_selecionado is None:
                st.error("Por favor, cadastre um método antes de adicionar uma aposta.")
            else:
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
                    metodo_selecionado,
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
    
    # -------------------------------------------------------------------------
    # Aba: Cadastro de Métodos
    # -------------------------------------------------------------------------
    with tabs[1]:
        st.header("Cadastro de Métodos")
        st.write("Cadastre aqui um novo método para ser utilizado no registro das apostas.")
        with st.form("form_metodo"):
            nome_metodo = st.text_input("Nome do Método")
            esporte = st.selectbox("Esporte", options=["Futebol", "Basquete", "Outros"])
            mercado_metodo = st.selectbox("Mercado", options=mercados)
            submitted = st.form_submit_button("Cadastrar Método")
            if submitted:
                if nome_metodo.strip() == "":
                    st.error("O nome do método não pode ser vazio.")
                else:
                    conn = get_db_connection()
                    try:
                        conn.execute("""
                            INSERT INTO metodos (nome, esporte, mercado)
                            VALUES (?, ?, ?)
                        """, (nome_metodo, esporte, mercado_metodo))
                        conn.commit()
                        st.success("Método cadastrado com sucesso!")
                    except sqlite3.IntegrityError:
                        st.error("Método já cadastrado.")
                    conn.close()

# =============================================================================
# Página: Relatórios e Estatísticas
# =============================================================================
elif page == "Relatórios e Estatísticas":
    st.title("Relatórios e Estatísticas")
    
    # Consulta as apostas do usuário
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM apostas WHERE email = ?", conn, params=(user_email,))
    conn.close()
    
    if not df.empty:
        df["data"] = pd.to_datetime(df["data"])
        
        st.markdown("### Filtros")
        col1, col2, col3, col4 = st.columns(4)
        data_min = df["data"].min().date()
        data_max = df["data"].max().date()
        data_inicio = col1.date_input("Data Início", value=data_min, min_value=data_min, max_value=data_max)
        data_fim = col2.date_input("Data Fim", value=data_max, min_value=data_min, max_value=data_max)
        agrupamento = col3.selectbox("Agrupar por", options=["Dia", "Semana", "Mês", "Ano"])
        # Filtro por Mercado
        mercados_unicos = sorted(df["mercado"].dropna().unique().tolist())
        mercado_opcoes = ["Todos"] + mercados_unicos
        mercado_selecionado = col4.selectbox("Filtrar por Mercado", options=mercado_opcoes)
        
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
            
            # Cálculo de métricas
            total_apostas = len(df_filtrado)
            green_apostas = len(df_filtrado[df_filtrado["resultado"] == "Green ✅"])
            taxa_acerto = (green_apostas / total_apostas) * 100 if total_apostas > 0 else 0
            winrate_fraction = (green_apostas / total_apostas) if total_apostas > 0 else 0
            odd_minima = round(1 / winrate_fraction, 2) if winrate_fraction > 0 else None
            
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
            
            st.markdown("### Apostas Registradas")
            # Preparar DataFrame para exibição (incluindo o ID para facilitar a exclusão)
            df_exibicao = df_filtrado[["id", "data", "campeonato", "time_mandante", "time_visitante", "odd", "resultado", "lucro"]].copy()
            df_exibicao["data"] = df_exibicao["data"].dt.date
            df_exibicao = df_exibicao.rename(columns={
                "id": "ID",
                "data": "Data",
                "campeonato": "Campeonato",
                "time_mandante": "Mandante",
                "time_visitante": "Visitante",
                "odd": "Odd",
                "resultado": "Resultado",
                "lucro": "Lucro"
            })
            st.dataframe(df_exibicao)
            
            # Opção para excluir apostas
            # Cria uma lista de opções descritivas para exclusão, utilizando o ID
            options_for_deletion = df_exibicao.apply(
                lambda row: f"ID {row['ID']} - {row['Data']} - {row['Campeonato']} - {row['Mandante']} vs {row['Visitante']}", axis=1
            ).tolist()
            selected_deletions = st.multiselect("Selecione as apostas para excluir", options=options_for_deletion)
            if st.button("❌ Excluir Apostas Selecionadas"):
                for item in selected_deletions:
                    try:
                        # Extrai o ID a partir da string (assumindo que está no formato "ID {id} - ...")
                        id_val = int(item.split(" ")[1])
                        conn = get_db_connection()
                        conn.execute("DELETE FROM apostas WHERE id = ?", (id_val,))
                        conn.commit()
                        conn.close()
                    except Exception as e:
                        st.error(f"Erro ao excluir aposta {item}: {e}")
                st.success("Apostas excluídas com sucesso!")
                st.experimental_rerun()
        else:
            st.warning("Nenhuma aposta encontrada com os filtros selecionados.")
    else:
        st.info("Nenhuma aposta registrada ainda.")
