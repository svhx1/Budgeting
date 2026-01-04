import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime
import time
import random

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Budgeting",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ESTILO PROFISSIONAL (CSS) ---
COR_FUNDO = "#000000"
COR_CARD = "#121212"  # Preto mais profundo para cards
COR_KIWI = "#A3E635"  # Verde Neon da marca
COR_VERMELHO = "#CF6679"  # Vermelho mais sóbrio (Material Design Dark)
COR_TEXTO_SEC = "#B0B3B8"

st.markdown(f"""
    <style>
    /* Reset e Fundo */
    .stApp {{
        background-color: {COR_FUNDO};
        color: white;
    }}

    /* Título Budgeting (Logo) */
    .logo-text {{
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 40px !important;
        font-weight: 900;
        color: {COR_KIWI};
        letter-spacing: -1px;
        margin-bottom: 20px;
    }}

    /* Metrics/Cards */
    div[data-testid="stMetric"] {{
        background-color: {COR_CARD};
        border-radius: 8px;
        padding: 15px;
        border-left: 4px solid {COR_KIWI}; /* Detalhe lateral */
        box-shadow: 0 2px 5px rgba(0,0,0,0.5);
    }}
    div[data-testid="stMetricLabel"] {{
        color: {COR_TEXTO_SEC};
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    div[data-testid="stMetricValue"] {{
        color: white !important;
        font-size: 24px !important;
    }}

    /* Inputs e Selects */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div {{
        background-color: {COR_CARD} !important;
        color: white !important;
        border-radius: 6px;
        border: 1px solid #333;
    }}
    .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus {{
        border-color: {COR_KIWI} !important;
    }}

    /* Botões */
    .stButton > button {{
        background-color: transparent;
        color: {COR_KIWI};
        border: 1px solid {COR_KIWI};
        border-radius: 6px;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 12px;
        letter-spacing: 1px;
        transition: all 0.3s;
    }}
    .stButton > button:hover {{
        background-color: {COR_KIWI};
        color: black;
    }}

    /* Abas */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 20px;
        border-bottom: 1px solid #333;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: transparent;
        border: none;
        color: {COR_TEXTO_SEC};
        font-weight: bold;
    }}
    .stTabs [aria-selected="true"] {{
        color: {COR_KIWI} !important;
        border-bottom: 2px solid {COR_KIWI};
    }}
    </style>
""", unsafe_allow_html=True)


# --- 3. BANCO DE DADOS ---
def get_conn():
    return sqlite3.connect("budgeting_pro.db")


def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Tabela Transações
    c.execute("""
              CREATE TABLE IF NOT EXISTS transacoes
              (
                  id
                  INTEGER
                  PRIMARY
                  KEY
                  AUTOINCREMENT,
                  descricao
                  TEXT,
                  valor
                  REAL,
                  categoria
                  TEXT,
                  tipo
                  TEXT,
                  data_str
                  TEXT
              )
              """)

    # Tabela Categorias (NOVA)
    c.execute("""
              CREATE TABLE IF NOT EXISTS categorias
              (
                  id
                  INTEGER
                  PRIMARY
                  KEY
                  AUTOINCREMENT,
                  nome
                  TEXT
                  UNIQUE
              )
              """)

    # Inserir categorias padrão se a tabela estiver vazia
    c.execute("SELECT count(*) FROM categorias")
    if c.fetchone()[0] == 0:
        cats_padrao = ["Alimentação", "Transporte", "Moradia", "Lazer", "Saúde", "Salário", "Investimentos"]
        for cat in cats_padrao:
            c.execute("INSERT INTO categorias (nome) VALUES (?)", (cat,))

    conn.commit()
    conn.close()


# Funções de Transação
def add_transacao(desc, valor, cat, tipo, data_str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO transacoes (descricao, valor, categoria, tipo, data_str) VALUES (?, ?, ?, ?, ?)",
              (desc, valor, cat, tipo, data_str))
    conn.commit()
    conn.close()


def delete_transacao(id_transacao):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM transacoes WHERE id = ?", (id_transacao,))
    conn.commit()
    conn.close()


def get_transacoes():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM transacoes", conn)
    conn.close()
    return df


def limpar_transacoes():
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM transacoes")
    conn.commit()
    conn.close()


# Funções de Categoria
def get_categorias():
    conn = get_conn()
    df = pd.read_sql_query("SELECT nome FROM categorias ORDER BY nome ASC", conn)
    conn.close()
    return df['nome'].tolist()


def add_categoria(nova_cat):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO categorias (nome) VALUES (?)", (nova_cat,))
        conn.commit()
        sucesso = True
    except:
        sucesso = False
    conn.close()
    return sucesso


def delete_categoria(nome_cat):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM categorias WHERE nome = ?", (nome_cat,))
    conn.commit()
    conn.close()


# Gerador de Dados Fake
def gerar_fake_data():
    limpar_transacoes()
    cats = get_categorias()
    if not cats:
        cats = ["Geral"]

    # Gerar Receitas
    add_transacao("Salário Mensal", 4000.0, "Salário", "Receita", datetime.now().strftime("%Y-%m-05"))

    # Gerar Despesas
    for _ in range(12):
        cat = random.choice([c for c in cats if c != "Salário"])
        val = random.uniform(20.0, 300.0)
        desc = f"Pagamento {cat}"
        dt = datetime.now().strftime(f"%Y-%m-{random.randint(1, 28):02d}")
        add_transacao(desc, val, cat, "Despesa", dt)


init_db()

# --- 4. CONFIGURAÇÕES DE VISUALIZAÇÃO ---
if 'privacy' not in st.session_state:
    st.session_state.privacy = False


def fmt_moeda(valor):
    if st.session_state.privacy:
        return "R$ ••••"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# --- 5. SIDEBAR (LOGO E FILTROS) ---
with st.sidebar:
    # LOGO (Texto estilizado)
    st.markdown('<div class="logo-text">BUDGETING</div>', unsafe_allow_html=True)

    st.markdown("### FILTROS")
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year

    meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
             7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}

    sel_mes = st.selectbox("Mês", list(meses.values()), index=mes_atual - 1)
    sel_ano = st.number_input("Ano", value=ano_atual, step=1)

    mes_num = list(meses.keys())[list(meses.values()).index(sel_mes)]
    filtro_data = f"{sel_ano}-{mes_num:02d}"

    st.divider()
    if st.button("Privacidade (ON/OFF)"):
        st.session_state.privacy = not st.session_state.privacy
        st.rerun()

# --- 6. PROCESSAMENTO DE DADOS ---
df_full = get_transacoes()
lista_categorias = get_categorias()

if not df_full.empty:
    df_full['data_dt'] = pd.to_datetime(df_full['data_str'])
    df_full['periodo'] = df_full['data_dt'].dt.strftime('%Y-%m')
    df = df_full[df_full['periodo'] == filtro_data].copy()
else:
    df = pd.DataFrame(columns=['id', 'descricao', 'valor', 'categoria', 'tipo', 'data_str'])

receitas = df[df['tipo'] == 'Receita']['valor'].sum() if not df.empty else 0.0
despesas = df[df['tipo'] == 'Despesa']['valor'].sum() if not df.empty else 0.0
saldo = receitas - despesas

# --- 7. INTERFACE ---
tab_dash, tab_add, tab_ext, tab_config = st.tabs(["DASHBOARD", "LANÇAMENTOS", "EXTRATO", "CONFIGURAÇÕES"])

# === ABA 1: DASHBOARD ===
with tab_dash:
    # Cards minimalistas
    col1, col2, col3 = st.columns(3)
    col1.metric("Entradas", fmt_moeda(receitas))
    col2.metric("Saídas", fmt_moeda(despesas))
    col3.metric("Saldo", fmt_moeda(saldo), delta_color="normal")

    st.markdown("---")

    if not df.empty and despesas > 0:
        col_chart1, col_chart2 = st.columns([2, 1])
        with col_chart1:
            st.caption("DISTRIBUIÇÃO DE GASTOS")
            df_desp = df[df['tipo'] == 'Despesa']
            fig = px.pie(df_desp, values='valor', names='categoria', hole=0.7,
                         color_discrete_sequence=px.colors.sequential.Tealgrn)
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={'color': "white"},
                showlegend=False,
                margin=dict(t=20, b=20, l=20, r=20)
            )
            # Adiciona texto no meio do gráfico
            fig.add_annotation(text=f"{sel_mes}", x=0.5, y=0.5, font_size=20, showarrow=False, font_color="white")
            st.plotly_chart(fig, use_container_width=True)

        with col_chart2:
            st.caption("TOP CATEGORIAS")
            top_cats = df_desp.groupby('categoria')['valor'].sum().sort_values(ascending=False).head(5)
            for cat, val in top_cats.items():
                st.markdown(f"**{cat}**")
                st.markdown(f"{fmt_moeda(val)}")
                st.progress(min(val / despesas, 1.0))
    else:
        st.info("Sem dados para análise neste período.")

# === ABA 2: LANÇAMENTOS ===
with tab_add:
    st.subheader("Novo Registro")

    with st.form("form_add", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            data_input = st.date_input("Data", value=datetime.now())
            tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
        with col_b:
            val = st.number_input("Valor", min_value=0.0, step=10.0)
            cat = st.selectbox("Categoria", lista_categorias)

        desc = st.text_input("Descrição", placeholder="Detalhe da transação...")

        btn_salvar = st.form_submit_button("CONFIRMAR LANÇAMENTO")

        if btn_salvar:
            add_transacao(desc, val, cat, tipo, data_input.strftime("%Y-%m-%d"))
            st.success("Registro salvo com sucesso.")
            time.sleep(0.5)
            st.rerun()

# === ABA 3: EXTRATO ===
with tab_ext:
    st.subheader("Movimentações")

    if not df.empty:
        df_sorted = df.sort_values(by="data_str", ascending=False)

        for index, row in df_sorted.iterrows():
            with st.container():
                c1, c2, c3, c4 = st.columns([0.5, 4, 2, 1])

                # Indicadores visuais simples (Sem emojis)
                cor_indicador = COR_KIWI if row['tipo'] == 'Receita' else COR_VERMELHO
                sinal = "+" if row['tipo'] == 'Receita' else "-"

                with c1:
                    st.markdown(
                        f"<span style='color:{cor_indicador}; font-size: 20px; font-weight:bold;'>{sinal}</span>",
                        unsafe_allow_html=True)

                with c2:
                    st.markdown(f"<span style='font-weight:600'>{row['descricao']}</span>", unsafe_allow_html=True)
                    st.caption(f"{pd.to_datetime(row['data_str']).strftime('%d/%m')} • {row['categoria']}")

                with c3:
                    st.markdown(f"<span style='color:{cor_indicador}'>{fmt_moeda(row['valor'])}</span>",
                                unsafe_allow_html=True)

                with c4:
                    if st.button("Excluir", key=f"del_{row['id']}"):
                        delete_transacao(row['id'])
                        st.rerun()
                st.divider()
    else:
        st.write("Nenhum registro encontrado.")

# === ABA 4: CONFIGURAÇÕES ===
with tab_config:
    col_geral, col_cats = st.columns(2)

    with col_geral:
        st.subheader("Sistema")
        st.caption("Ferramentas de banco de dados")

        if st.button("GERAR DADOS FICTÍCIOS"):
            gerar_fake_data()
            st.success("Dados gerados.")
            time.sleep(1)
            st.rerun()

        if st.button("RESETAR SISTEMA (APAGAR TUDO)"):
            limpar_transacoes()
            st.warning("Banco de dados limpo.")
            time.sleep(1)
            st.rerun()

    with col_cats:
        st.subheader("Categorias")
        st.caption("Gerencie suas categorias personalizadas")

        # Adicionar Nova
        with st.form("nova_cat"):
            nova_cat_txt = st.text_input("Nova Categoria")
            if st.form_submit_button("CRIAR"):
                if nova_cat_txt:
                    if add_categoria(nova_cat_txt):
                        st.success(f"'{nova_cat_txt}' criada.")
                        st.rerun()
                    else:
                        st.error("Categoria já existe.")

        st.divider()

        # Listar e Excluir
        st.write("Categorias Existentes:")
        for c in lista_categorias:
            c_nome, c_del = st.columns([4, 1])
            c_nome.write(c)
            if c_del.button("X", key=f"cat_{c}"):
                delete_categoria(c)
                st.rerun()