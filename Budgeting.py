import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
import random

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Budgeting Pro",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ESTILO VISUAL (PRETO + KIWI - SEM EMOJIS) ---
COR_FUNDO = "#000000"
COR_CARD = "#121212"
COR_KIWI = "#A3E635"
COR_VERMELHO = "#CF6679"
COR_TEXTO_SEC = "#B0B3B8"

st.markdown(f"""
    <style>
    /* Reset Geral */
    .stApp {{ background-color: {COR_FUNDO}; color: white; }}

    /* LOGO */
    .logo-text {{ 
        font-family: 'Helvetica Neue', sans-serif; 
        font-size: 36px !important; 
        font-weight: 900; 
        color: {COR_KIWI}; 
        letter-spacing: -1px; 
        margin-bottom: 20px; 
        text-transform: uppercase;
    }}

    /* Cards */
    div[data-testid="stMetric"] {{ 
        background-color: {COR_CARD}; 
        border-radius: 6px; 
        padding: 15px; 
        border-left: 4px solid {COR_KIWI}; 
    }}
    div[data-testid="stMetricLabel"] {{ color: {COR_TEXTO_SEC}; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }}
    div[data-testid="stMetricValue"] {{ color: white !important; font-size: 24px !important; }}

    /* Inputs */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input {{ 
        background-color: {COR_CARD} !important; 
        color: white !important; 
        border: 1px solid #333; 
        border-radius: 4px; 
    }}
    .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus {{ border-color: {COR_KIWI} !important; }}

    /* Expander (A "Setinha") */
    .streamlit-expanderHeader {{
        background-color: {COR_CARD};
        border: 1px solid #333;
        border-radius: 4px;
        color: white;
    }}

    /* Botões */
    .stButton > button {{ 
        background-color: transparent; 
        color: {COR_KIWI}; 
        border: 1px solid {COR_KIWI}; 
        border-radius: 4px; 
        font-weight: 600; 
        text-transform: uppercase; 
        font-size: 11px; 
        letter-spacing: 1px; 
        transition: all 0.3s;
    }}
    .stButton > button:hover {{ background-color: {COR_KIWI}; color: black; }}

    /* Abas */
    .stTabs [data-baseweb="tab-list"] {{ gap: 20px; border-bottom: 1px solid #333; }}
    .stTabs [data-baseweb="tab"] {{ background-color: transparent; border: none; color: {COR_TEXTO_SEC}; font-weight: bold; }}
    .stTabs [aria-selected="true"] {{ color: {COR_KIWI} !important; border-bottom: 2px solid {COR_KIWI}; }}

    /* Tooltip Plotly */
    .plotly .hoverlayer .hovertext {{ 
        background-color: {COR_CARD} !important; 
        border: 1px solid {COR_KIWI} !important; 
        font-family: sans-serif; 
        color: white !important;
    }}
    </style>
""", unsafe_allow_html=True)


# --- 3. BANCO DE DADOS ---
def get_conn():
    return sqlite3.connect("budgeting_pro.db")


def init_db():
    conn = get_conn()
    c = conn.cursor()
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
                  TEXT,
                  group_id
                  TEXT,
                  parcela_info
                  TEXT
              )
              """)
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
                  UNIQUE,
                  cor
                  TEXT
              )
              """)
    c.execute("SELECT count(*) FROM categorias")
    if c.fetchone()[0] == 0:
        cats_padrao = [("Alimentação", "#FF5733"), ("Transporte", "#33FF57"), ("Moradia", "#3357FF"),
                       ("Lazer", "#FF33A8"), ("Saúde", "#33FFF5"), ("Salário", "#A3E635"), ("Outros", "#B0B3B8")]
        c.executemany("INSERT INTO categorias (nome, cor) VALUES (?, ?)", cats_padrao)
    conn.commit()
    conn.close()


# --- FUNÇÕES DE LÓGICA ---
def add_transacao_complexa(desc, valor, cat, tipo, data_obj, recorrencia, qtd_parcelas=1):
    conn = get_conn()
    c = conn.cursor()
    group_id = f"{int(time.time())}_{random.randint(1000, 9999)}"

    if recorrencia == "Único":
        dt_str = datetime.now().strftime(f"{data_obj} %H:%M:%S")
        c.execute(
            "INSERT INTO transacoes (descricao, valor, categoria, tipo, data_str, group_id, parcela_info) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (desc, valor, cat, tipo, dt_str, group_id, None))

    elif recorrencia == "Parcelado":
        valor_parcela = valor / qtd_parcelas
        for i in range(qtd_parcelas):
            data_futura = data_obj + relativedelta(months=i)
            dt_str = datetime.now().strftime(f"{data_futura} %H:%M:%S")
            info = f"{i + 1}/{qtd_parcelas}"
            desc_final = f"{desc} ({info})"
            c.execute(
                "INSERT INTO transacoes (descricao, valor, categoria, tipo, data_str, group_id, parcela_info) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (desc_final, valor_parcela, cat, tipo, dt_str, group_id, info))

    elif recorrencia == "Fixo (Mensal)":
        for i in range(12):
            data_futura = data_obj + relativedelta(months=i)
            dt_str = datetime.now().strftime(f"{data_futura} %H:%M:%S")
            c.execute(
                "INSERT INTO transacoes (descricao, valor, categoria, tipo, data_str, group_id, parcela_info) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (desc, valor, cat, tipo, dt_str, group_id, "Fixo"))
    conn.commit()
    conn.close()


def delete_transacao(id_transacao, delete_group=False, group_id=None):
    conn = get_conn()
    c = conn.cursor()
    if delete_group and group_id:
        c.execute("DELETE FROM transacoes WHERE group_id = ?", (group_id,))
    else:
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
    conn.execute("DELETE FROM transacoes")
    conn.commit()
    conn.close()


def get_categorias_dict():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT nome, cor FROM categorias ORDER BY nome ASC")
    data = c.fetchall()
    conn.close()
    return {nome: cor for nome, cor in data}


def get_categorias_df():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM categorias ORDER BY nome ASC", conn)
    conn.close()
    return df


def add_categoria(nova_cat, nova_cor):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO categorias (nome, cor) VALUES (?, ?)", (nova_cat, nova_cor))
        conn.commit()
        sucesso = True
    except:
        sucesso = False
    conn.close()
    return sucesso


def update_categoria(id_cat, novo_nome, nova_cor, nome_antigo):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("UPDATE categorias SET nome = ?, cor = ? WHERE id = ?", (novo_nome, nova_cor, id_cat))
        if novo_nome != nome_antigo:
            c.execute("UPDATE transacoes SET categoria = ? WHERE categoria = ?", (novo_nome, nome_antigo))
        conn.commit()
        sucesso = True
    except:
        sucesso = False
    conn.close()
    return sucesso


def delete_categoria(id_cat):
    conn = get_conn()
    conn.execute("DELETE FROM categorias WHERE id = ?", (id_cat,))
    conn.commit()
    conn.close()


def gerar_fake_data():
    limpar_transacoes()
    cats_dict = get_categorias_dict()
    cats_nomes = list(cats_dict.keys())
    if not cats_nomes: cats_nomes = ["Geral"]
    add_transacao_complexa("Salário", 4500.0, "Salário", "Receita", datetime.now().date(), "Único")
    for _ in range(20):
        cat = random.choice([c for c in cats_nomes if c != "Salário"])
        val = random.uniform(50.0, 500.0)
        desc = f"Gasto {cat}"
        dia = random.randint(1, 28)
        dt_obj = datetime.now().date().replace(day=dia)
        add_transacao_complexa(desc, val, cat, "Despesa", dt_obj, "Único")


init_db()

# --- 4. UTILITÁRIOS ---
if 'privacy' not in st.session_state: st.session_state.privacy = False


def fmt_moeda(valor):
    if st.session_state.privacy: return "R$ ••••"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# --- 5. SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="logo-text">BUDGETING</div>', unsafe_allow_html=True)
    st.markdown("### FILTROS")
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
             9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
    sel_mes = st.selectbox("Mês", list(meses.values()), index=mes_atual - 1, label_visibility="collapsed")
    sel_ano = st.number_input("Ano", value=ano_atual, step=1, label_visibility="collapsed")
    mes_num = list(meses.keys())[list(meses.values()).index(sel_mes)]
    filtro_periodo = f"{sel_ano}-{mes_num:02d}"

    st.divider()
    col_eye, col_void = st.columns([2, 1])
    with col_eye:
        label_btn = "MOSTRAR VALORES" if st.session_state.privacy else "OCULTAR VALORES"
        if st.button(label_btn):
            st.session_state.privacy = not st.session_state.privacy
            st.rerun()

# --- 6. PROCESSAMENTO ---
df_full = get_transacoes()
cats_cores = get_categorias_dict()

if not df_full.empty:
    df_full['data_dt'] = pd.to_datetime(df_full['data_str'], format='mixed')
    df_full['periodo'] = df_full['data_dt'].dt.strftime('%Y-%m')
    df_full['data_fmt'] = df_full['data_dt'].dt.strftime('%d/%m/%Y')
    df_full['hora_fmt'] = df_full['data_dt'].dt.strftime('%H:%M')
    df_filtrado = df_full[df_full['periodo'] == filtro_periodo].copy()
else:
    df_filtrado = pd.DataFrame(
        columns=['id', 'descricao', 'valor', 'categoria', 'tipo', 'group_id', 'parcela_info', 'data_dt'])

receitas = df_filtrado[df_filtrado['tipo'] == 'Receita']['valor'].sum() if not df_filtrado.empty else 0.0
despesas = df_filtrado[df_filtrado['tipo'] == 'Despesa']['valor'].sum() if not df_filtrado.empty else 0.0
saldo = receitas - despesas

# --- 7. INTERFACE PRINCIPAL ---
tab_dash, tab_add, tab_ext, tab_conf = st.tabs(["DASHBOARD", "LANÇAMENTOS", "EXTRATO", "CONFIGURAÇÕES"])

# === ABA 1: DASHBOARD (ALTERNATIVA SETINHAS/EXPANDER) ===
with tab_dash:
    c1, c2, c3 = st.columns(3)
    c1.metric("Entradas", fmt_moeda(receitas))
    c2.metric("Saídas", fmt_moeda(despesas))
    c3.metric("Saldo", fmt_moeda(saldo))

    st.markdown("---")

    if not df_filtrado.empty and despesas > 0:
        c_graf, c_list = st.columns([1, 1])

        # Agrupamento
        df_desp = df_filtrado[df_filtrado['tipo'] == 'Despesa'].copy()
        df_grouped = df_desp.groupby('categoria', as_index=False)['valor'].sum().sort_values(by='valor',
                                                                                             ascending=False)

        with c_graf:
            st.caption("VISÃO GERAL (GRÁFICO)")
            cores_ord = [cats_cores.get(c, '#FFF') for c in df_grouped['categoria']]
            textos = [fmt_moeda(v) for v in df_grouped['valor']]

            fig = go.Figure(data=[go.Pie(
                labels=df_grouped['categoria'], values=df_grouped['valor'], hole=0.65, sort=False,
                marker=dict(colors=cores_ord), textinfo='percent', hoverinfo='text',
                hovertemplate="<b>%{label}</b><br>%{customdata}<extra></extra>", customdata=textos
            )])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                              margin=dict(t=10, b=10, l=10, r=10), height=350)
            st.plotly_chart(fig, use_container_width=True)

        with c_list:
            st.caption("DETALHAMENTO (CLIQUE NA SETA PARA ABRIR)")

            # AQUI ESTÁ A SOLUÇÃO "SETINHA" (EXPANDER)
            # Cria uma lista onde cada categoria é um botão expansível
            for _, row in df_grouped.iterrows():
                cat_nome = row['categoria']
                cat_valor = row['valor']
                cor = cats_cores.get(cat_nome, '#FFF')

                # Título do Expander com nome e valor total
                label_expander = f"{cat_nome}  —  {fmt_moeda(cat_valor)}"

                with st.expander(label_expander):
                    # Filtra apenas as compras dessa categoria
                    df_cat_items = df_desp[df_desp['categoria'] == cat_nome].sort_values(by='data_dt', ascending=False)

                    # Mostra lista limpa
                    for _, item in df_cat_items.iterrows():
                        col_desc, col_val = st.columns([3, 1])
                        with col_desc:
                            st.write(f"**{item['descricao']}**")
                            st.caption(f"{item['data_fmt']} • {item['hora_fmt']}")
                        with col_val:
                            st.markdown(f"<div style='text-align:right; color:{cor}'>{fmt_moeda(item['valor'])}</div>",
                                        unsafe_allow_html=True)
                        st.markdown("<hr style='margin: 5px 0; border-color: #333;'>", unsafe_allow_html=True)

    else:
        st.info("Sem dados neste período.")

# === ABA 2: LANÇAMENTOS ===
with tab_add:
    st.subheader("Novo Registro")
    col_esq, col_dir = st.columns(2)
    with col_esq:
        data_sel = st.date_input("Data", value=datetime.now())
        tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
        recorrencia = st.selectbox("Recorrência", ["Único", "Parcelado", "Fixo (Mensal)"])
        qtd_parcelas = 1
        if recorrencia == "Parcelado":
            qtd_parcelas = st.number_input("Nº Parcelas", min_value=2, max_value=60, value=2)
    with col_dir:
        val = st.number_input("Valor (R$)", min_value=0.0, step=0.01, format=None)
        cat = st.selectbox("Categoria", list(cats_cores.keys()))
        desc = st.text_input("Descrição", placeholder="Ex: Supermercado")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("SALVAR REGISTRO", type="primary"):
        if val > 0 and desc:
            add_transacao_complexa(desc, val, cat, tipo, data_sel, recorrencia, qtd_parcelas)
            st.success("Salvo!");
            time.sleep(0.5);
            st.rerun()
        else:
            st.error("Preencha o valor e a descrição.")

# === ABA 3: EXTRATO ===
with tab_ext:
    st.subheader(f"Extrato: {sel_mes}/{sel_ano}")
    if not df_filtrado.empty:
        df_ord = df_filtrado.sort_values(by="data_dt", ascending=False)
        for _, row in df_ord.iterrows():
            with st.container():
                c_icon, c_info, c_val, c_del = st.columns([0.5, 4, 2, 1])
                sinal = "+" if row['tipo'] == 'Receita' else "-"
                cor_sinal = COR_KIWI if row['tipo'] == 'Receita' else COR_VERMELHO

                with c_icon:
                    st.markdown(f"<span style='color:{cor_sinal}; font-size:20px; font-weight:bold'>{sinal}</span>",
                                unsafe_allow_html=True)
                with c_info:
                    st.markdown(f"**{row['descricao']}**")
                    meta_txt = f"{row['data_fmt']} {row['hora_fmt']} • {row['categoria']}"
                    if row[
                        'parcela_info']: meta_txt += f" • <span style='color:{COR_KIWI}'>({row['parcela_info']})</span>"
                    st.markdown(f"<span style='color:#666; font-size:12px'>{meta_txt}</span>", unsafe_allow_html=True)
                with c_val:
                    st.markdown(
                        f"<div style='text-align:right; font-weight:bold; color:{cor_sinal}'>{fmt_moeda(row['valor'])}</div>",
                        unsafe_allow_html=True)
                with c_del:
                    with st.popover("Excluir"):
                        if st.button("Este item", key=f"d1_{row['id']}"): delete_transacao(row['id']); st.rerun()
                        if row['group_id'] and ("/" in str(row['parcela_info']) or row['parcela_info'] == "Fixo"):
                            if st.button("Série Completa", key=f"dall_{row['id']}"): delete_transacao(row['id'], True,
                                                                                                      row[
                                                                                                          'group_id']); st.rerun()
                st.divider()
    else:
        st.write("Nenhum registro encontrado.")

# === ABA 4: CONFIGURAÇÕES ===
with tab_conf:
    st.subheader("Gerenciar Categorias")
    with st.expander("Nova Categoria"):
        c_n, c_c = st.columns([3, 1])
        n_nome = c_n.text_input("Nome")
        n_cor = c_c.color_picker("Cor", "#A3E635")
        if st.button("CRIAR"):
            if n_nome and add_categoria(n_nome, n_cor):
                st.success("Criado!"); st.rerun()
            else:
                st.error("Erro.")

    st.divider()
    st.write("Categorias Atuais:")
    df_cats = get_categorias_df()
    for _, row in df_cats.iterrows():
        with st.expander(f"{row['nome']}", expanded=False):
            with st.container():
                e_nm = st.text_input("Nome", value=row['nome'], key=f"en_{row['id']}")
                e_cr = st.color_picker("Cor", value=row['cor'], key=f"ec_{row['id']}")
                c_s, c_d = st.columns(2)
                if c_s.button("SALVAR", key=f"sv_{row['id']}"): update_categoria(row['id'], e_nm, e_cr,
                                                                                 row['nome']); st.rerun()
                if c_d.button("EXCLUIR", key=f"dl_{row['id']}"): delete_categoria(row['id']); st.rerun()

    st.divider()
    cf, cr = st.columns(2)
    with cf:
        if st.button("GERAR DADOS FICTÍCIOS"): gerar_fake_data(); st.success("Feito!"); time.sleep(1); st.rerun()
    with cr:
        if st.button("RESETAR SISTEMA"): limpar_transacoes(); st.warning("Limpo!"); time.sleep(1); st.rerun()