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

# --- 2. ESTILO VISUAL (PRETO + KIWI) ---
COR_FUNDO = "#000000"
COR_CARD = "#121212"
COR_KIWI = "#A3E635"
COR_VERMELHO = "#FF3333"  # Vermelho Neon
COR_TEXTO_SEC = "#B0B3B8"

st.markdown(f"""
    <style>
    /* Reset Geral */
    .stApp {{ background-color: {COR_FUNDO}; color: white; }}

    /* --- 1. CONFIGURAÇÃO DAS ABAS (TABS) --- */
    /* Cor do texto padrão */
    .stTabs [data-baseweb="tab"] {{
        color: {COR_TEXTO_SEC};
        border: none;
        font-weight: bold;
    }}

    /* Cor ao passar o mouse (HOVER) -> VERDE */
    .stTabs [data-baseweb="tab"]:hover {{
        color: {COR_KIWI} !important;
    }}

    /* Cor da aba selecionada -> VERDE */
    .stTabs [aria-selected="true"] {{
        color: {COR_KIWI} !important;
        border-bottom: 2px solid {COR_KIWI} !important;
    }}

    /* --- 2. BARRA DE CARREGAMENTO (LOADING RUNNER) --- */
    /* Aquela barrinha que corre no topo da tela */
    .stDecoration {{
        background-image: linear-gradient(90deg, {COR_KIWI}, {COR_VERMELHO});
        height: 3px;
    }}

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

    /* CARDS PERSONALIZADOS (Entradas/Saídas) */
    .card-box {{
        background-color: {COR_CARD};
        border-radius: 8px;
        padding: 20px;
        border: 1px solid #333;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }}

    /* Bordas Laterais Coloridas */
    .border-green {{ border-left: 5px solid {COR_KIWI}; }}
    .border-red {{ border-left: 5px solid {COR_VERMELHO}; }}

    /* Barra Inferior Dinâmica (Saldo) */
    .border-bottom-green {{ border-bottom: 5px solid {COR_KIWI}; }}
    .border-bottom-red {{ border-bottom: 5px solid {COR_VERMELHO}; }}

    .card-label {{ color: {COR_TEXTO_SEC}; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }}
    .card-value {{ font-size: 28px; font-weight: bold; color: white; }}

    /* Inputs */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div, .stDateInput>div>div>input {{ 
        background-color: {COR_CARD} !important; 
        color: white !important; 
        border: 1px solid #333; 
        border-radius: 4px; 
    }}
    .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus {{ border-color: {COR_KIWI} !important; }}

    /* Expander */
    .streamlit-expanderHeader {{
        background-color: {COR_CARD};
        border: 1px solid #333;
        color: {COR_TEXTO_SEC};
        font-size: 14px;
        font-weight: 600;
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

    /* Tooltip do Gráfico */
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
    c.execute("""
              CREATE TABLE IF NOT EXISTS metas
              (
                  id
                  INTEGER
                  PRIMARY
                  KEY
                  AUTOINCREMENT,
                  categoria
                  TEXT
                  UNIQUE,
                  valor_teto
                  REAL
              )
              """)
    c.execute("SELECT count(*) FROM categorias")
    if c.fetchone()[0] == 0:
        cats_padrao = [("Alimentação", "#FF5733"), ("Transporte", "#33FF57"), ("Moradia", "#3357FF"),
                       ("Lazer", "#FF33A8"), ("Saúde", "#33FFF5"), ("Salário", "#A3E635"), ("Outros", "#B0B3B8")]
        c.executemany("INSERT INTO categorias (nome, cor) VALUES (?, ?)", cats_padrao)
    conn.commit()
    conn.close()


# --- FUNÇÕES CORE ---
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


# --- Funções Categoria ---
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
            c.execute("UPDATE metas SET categoria = ? WHERE categoria = ?", (novo_nome, nome_antigo))
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


# --- Funções Metas ---
def add_meta(categoria, valor_teto):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO metas (categoria, valor_teto) VALUES (?, ?)", (categoria, valor_teto))
        conn.commit()
        sucesso = True
    except:
        sucesso = False
    conn.close()
    return sucesso


def update_meta(id_meta, novo_valor):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE metas SET valor_teto = ? WHERE id = ?", (novo_valor, id_meta))
    conn.commit()
    conn.close()


def get_metas_df():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM metas", conn)
    conn.close()
    return df


def delete_meta(id_meta):
    conn = get_conn()
    conn.execute("DELETE FROM metas WHERE id = ?", (id_meta,))
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
    if "Alimentação" in cats_nomes: add_meta("Alimentação", 1000.0)


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

receitas_mes = df_filtrado[df_filtrado['tipo'] == 'Receita']['valor'].sum() if not df_filtrado.empty else 0.0
despesas_mes = df_filtrado[df_filtrado['tipo'] == 'Despesa']['valor'].sum() if not df_filtrado.empty else 0.0
saldo_mes = receitas_mes - despesas_mes

# --- 7. INTERFACE PRINCIPAL ---
tab_dash, tab_add, tab_ext, tab_conf = st.tabs(["DASHBOARD", "LANÇAMENTOS", "EXTRATO", "CONFIGURAÇÕES"])

# === ABA 1: DASHBOARD ===
with tab_dash:
    # SALDO
    cor_saldo = COR_KIWI if saldo_mes >= 0 else COR_VERMELHO
    classe_barra_saldo = "border-bottom-green" if saldo_mes >= 0 else "border-bottom-red"

    st.markdown(f"""
    <div class="card-box {classe_barra_saldo}" style="text-align:center;">
        <div class="card-label">SALDO DISPONÍVEL (MÊS)</div>
        <div class="card-value" style="color: {cor_saldo}; font-size: 40px;">{fmt_moeda(saldo_mes)}</div>
    </div>
    """, unsafe_allow_html=True)

    # ENTRADAS E SAÍDAS
    c_in, c_out = st.columns(2)
    with c_in:
        st.markdown(f"""
        <div class="card-box border-green">
            <div class="card-label">ENTRADAS</div>
            <div class="card-value">{fmt_moeda(receitas_mes)}</div>
        </div>
        """, unsafe_allow_html=True)
    with c_out:
        st.markdown(f"""
        <div class="card-box border-red">
            <div class="card-label">SAÍDAS</div>
            <div class="card-value">{fmt_moeda(despesas_mes)}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # METAS
    st.caption("LIMITES DE GASTOS")
    df_metas = get_metas_df()

    if not df_metas.empty:
        cols_metas = st.columns(3)
        for index, row in df_metas.iterrows():
            with cols_metas[index % 3]:
                categoria_meta = row['categoria']
                teto = row['valor_teto']

                gasto_atual = 0.0
                df_cat_mes = pd.DataFrame()
                if not df_filtrado.empty:
                    df_cat_mes = df_filtrado[
                        (df_filtrado['categoria'] == categoria_meta) & (df_filtrado['tipo'] == 'Despesa')]
                    gasto_atual = df_cat_mes['valor'].sum()

                progresso = max(0.0, min(gasto_atual / teto, 1.0))
                pct = (gasto_atual / teto) * 100
                cor_barra = cats_cores.get(categoria_meta, "#FFFFFF")
                cor_texto = "#FFFFFF"
                aviso = ""

                if gasto_atual > teto:
                    cor_barra = COR_VERMELHO
                    cor_texto = COR_VERMELHO
                    aviso = "LIMITE EXCEDIDO"

                st.markdown(f"""
                <div style="background-color: #121212; padding: 15px; border-radius: 8px; border: 1px solid #333; margin-bottom: 5px;">
                    <div style="font-weight: bold; font-size: 14px; margin-bottom: 5px; color:{cor_barra}">{categoria_meta}</div>
                    <div style="font-size: 12px; color: #999; display: flex; justify-content: space-between;">
                        <span>Gasto: {fmt_moeda(gasto_atual)}</span>
                        <span>Teto: {fmt_moeda(teto)}</span>
                    </div>
                    <div style="width: 100%; background-color: #333; height: 8px; border-radius: 4px; margin-top: 8px;">
                        <div style="width: {progresso * 100}%; background-color: {cor_barra}; height: 8px; border-radius: 4px;"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-top:4px;">
                        <span style="font-size: 10px; color: {cor_texto}; font-weight:bold;">{aviso}</span>
                        <span style="font-size: 11px; color: #999;">{pct:.1f}%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                with st.expander("Ver Detalhes"):
                    if not df_cat_mes.empty:
                        df_sorted = df_cat_mes.sort_values(by="data_dt", ascending=False)
                        for _, item in df_sorted.iterrows():
                            st.markdown(f"""
                            <div style="border-bottom: 1px solid #333; padding: 5px 0;">
                                <div style="display:flex; justify-content:space-between;">
                                    <span style="font-size:13px; font-weight:500;">{item['descricao']}</span>
                                    <span style="font-size:13px; color:{COR_VERMELHO}; font-weight:bold;">{fmt_moeda(item['valor'])}</span>
                                </div>
                                <div style="font-size:11px; color:#666;">{item['data_fmt']} • {item['hora_fmt']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.caption("Sem gastos.")
                st.markdown("<div style='margin-bottom:20px'></div>", unsafe_allow_html=True)
    else:
        st.info("Sem limites definidos.")

    st.markdown("---")

    # GRÁFICO
    if not df_filtrado.empty and despesas_mes > 0:
        c_graf, c_list = st.columns([1, 1])
        df_desp = df_filtrado[df_filtrado['tipo'] == 'Despesa'].copy()
        df_grouped = df_desp.groupby('categoria', as_index=False)['valor'].sum().sort_values(by='valor',
                                                                                             ascending=False)

        with c_graf:
            st.caption("VISÃO GERAL")
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
            st.caption("DETALHAMENTO")
            st.markdown("<br>", unsafe_allow_html=True)
            for _, row in df_grouped.iterrows():
                cat_nome = row['categoria']
                cat_valor = row['valor']
                cor = cats_cores.get(cat_nome, '#FFF')
                percentual = (cat_valor / despesas_mes) * 100 if despesas_mes > 0 else 0

                c_inf, c_val = st.columns([3, 1])
                with c_inf:
                    st.markdown(
                        f"<span style='color:{cor}; font-size:16px'>●</span> <span style='font-size:15px; font-weight:bold'>{cat_nome}</span>",
                        unsafe_allow_html=True)
                    st.progress(int(percentual))
                with c_val:
                    st.markdown(
                        f"<div style='text-align:right; color:{COR_VERMELHO}; font-weight:bold; font-size:15px; padding-top:5px'>{fmt_moeda(cat_valor)}</div>",
                        unsafe_allow_html=True)

                with st.expander("Ver transações"):
                    df_cat_items = df_desp[df_desp['categoria'] == cat_nome].sort_values(by='data_dt', ascending=False)
                    for _, item in df_cat_items.iterrows():
                        col_desc, col_val = st.columns([3, 1])
                        with col_desc:
                            st.write(f"**{item['descricao']}**")
                            st.caption(f"{item['data_fmt']} • {item['hora_fmt']}")
                        with col_val:
                            st.markdown(
                                f"<div style='text-align:right; color:{COR_VERMELHO}; font-weight:500'>{fmt_moeda(item['valor'])}</div>",
                                unsafe_allow_html=True)
                        st.markdown("<hr style='margin: 5px 0; border-color: #333;'>", unsafe_allow_html=True)
                st.markdown("<div style='margin-bottom:25px'></div>", unsafe_allow_html=True)
    else:
        st.info("Sem despesas neste período.")

# === ABA 2: LANÇAMENTOS (COM CALLBACK) ===
with tab_add:
    st.subheader("Novo Registro")

    if "lanc_valor" not in st.session_state: st.session_state.lanc_valor = 0.0
    if "lanc_desc" not in st.session_state: st.session_state.lanc_desc = ""


    def salvar_lancamento():
        v_val = st.session_state.lanc_valor
        v_desc = st.session_state.lanc_desc
        v_cat = st.session_state.lanc_cat
        v_tipo = st.session_state.lanc_tipo
        v_data = st.session_state.lanc_data
        v_rec = st.session_state.lanc_rec
        v_qtd = st.session_state.get("lanc_qtd", 1)

        if v_val > 0 and v_desc:
            add_transacao_complexa(v_desc, v_val, v_cat, v_tipo, v_data, v_rec, v_qtd)
            st.session_state.lanc_valor = 0.0
            st.session_state.lanc_desc = ""
            st.toast("Salvo com sucesso")
        else:
            st.toast("⚠️ Preencha valor e descrição.")


    col_esq, col_dir = st.columns(2)
    with col_esq:
        st.date_input("Data", value=datetime.now(), key="lanc_data")
        st.selectbox("Tipo", ["Despesa", "Receita"], key="lanc_tipo")
        rec = st.selectbox("Recorrência", ["Único", "Parcelado", "Fixo (Mensal)"], key="lanc_rec")
        if rec == "Parcelado":
            st.number_input("Nº Parcelas", min_value=2, max_value=60, value=2, key="lanc_qtd")

    with col_dir:
        st.number_input("Valor (R$)", min_value=0.0, step=0.01, format=None, key="lanc_valor")
        st.selectbox("Categoria", list(cats_cores.keys()), key="lanc_cat")
        st.text_input("Descrição", placeholder="Ex: Supermercado", key="lanc_desc")

    st.markdown("<br>", unsafe_allow_html=True)
    st.button("SALVAR REGISTRO", type="primary", on_click=salvar_lancamento)

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
    st.subheader("Limites de Gastos")
    with st.expander("CADASTRAR NOVO LIMITE"):
        c_m_cat, c_m_val = st.columns([2, 1])
        m_cat = c_m_cat.selectbox("Categoria", list(cats_cores.keys()), key="sel_new_meta_cat")
        m_val = c_m_val.number_input("Teto Mensal (R$)", min_value=1.0, step=50.0, key="num_new_meta_val")
        if st.button("DEFINIR LIMITE"):
            if add_meta(m_cat, m_val):
                st.success(f"Limite para {m_cat} definido!"); st.rerun()
            else:
                st.error("Limite já existe. Edite abaixo.")

    st.write("Limites Ativos:")
    df_metas_list = get_metas_df()
    for _, row in df_metas_list.iterrows():
        label_meta = f"{row['categoria']} — Teto atual: {fmt_moeda(row['valor_teto'])}"
        with st.expander(label_meta):
            with st.container():
                novo_teto = st.number_input("Novo Valor Teto (R$)", value=row['valor_teto'], step=50.0,
                                            key=f"edit_val_meta_{row['id']}")
                col_save, col_del = st.columns(2)
                if col_save.button("ATUALIZAR LIMITE", key=f"save_meta_{row['id']}"):
                    update_meta(row['id'], novo_teto);
                    st.success("Atualizado!");
                    time.sleep(0.5);
                    st.rerun()
                if col_del.button("REMOVER LIMITE", key=f"del_meta_{row['id']}"):
                    delete_meta(row['id']);
                    st.rerun()

    st.markdown("---")
    st.subheader("Categorias")
    with st.expander("CADASTRAR NOVA CATEGORIA"):
        c_n, c_c = st.columns([3, 1])
        n_nome = c_n.text_input("Nome da Categoria")
        n_cor = c_c.color_picker("Cor", "#A3E635")
        if st.button("CRIAR CATEGORIA"):
            if n_nome and add_categoria(n_nome, n_cor): st.success("Criado!"); st.rerun()

    df_cats = get_categorias_df()
    for _, row in df_cats.iterrows():
        with st.expander(f"{row['nome']}", expanded=False):
            with st.container():
                e_nm = st.text_input("Nome", value=row['nome'], key=f"en_{row['id']}")
                e_cr = st.color_picker("Cor", value=row['cor'], key=f"ec_{row['id']}")
                c_s, c_d = st.columns(2)
                if c_s.button("SALVAR ALTERAÇÃO", key=f"sv_{row['id']}"): update_categoria(row['id'], e_nm, e_cr,
                                                                                           row['nome']); st.rerun()
                if c_d.button("EXCLUIR CATEGORIA", key=f"dl_{row['id']}"): delete_categoria(row['id']); st.rerun()

    st.markdown("---")
    cf, cr = st.columns(2)
    with cf:
        if st.button("GERAR DADOS FICTÍCIOS"): gerar_fake_data(); st.success("Feito!"); time.sleep(1); st.rerun()
    with cr:
        if st.button("RESETAR SISTEMA"): limpar_transacoes(); st.warning("Limpo!"); time.sleep(1); st.rerun()