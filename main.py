import streamlit as st
import pandas as pd
import os
from datetime import datetime
from itertools import combinations
import plotly.express as px

# ===============================
# CONFIGURAÇÃO GERAL
# ===============================
st.set_page_config(
    page_title="Validador de Bases",
    layout="wide"
)

# CSS Power BI Style
st.markdown("""
<style>
    body { background-color: #0e1117; }
    .stMetric {
        background-color: #1f2937;
        padding: 16px;
        border-radius: 14px;
        box-shadow: 0 4px 14px rgba(0,0,0,.4);
    }
</style>
""", unsafe_allow_html=True)

# Pastas
PASTA_RELATORIOS = "relatorios_salvos"
HISTORICO_PATH = "historico.csv"

os.makedirs(PASTA_RELATORIOS, exist_ok=True)

# ===============================
# FUNÇÕES
# ===============================
def detectar_melhor_chave(df, max_comb=3):
    melhores = []
    colunas = df.columns.tolist()

    for r in range(1, max_comb + 1):
        for combo in combinations(colunas, r):
            temp = df[list(combo)].dropna()
            if temp.empty:
                continue

            unicidade = temp.drop_duplicates().shape[0] / len(df)

            if unicidade == 1:
                return list(combo)

            melhores.append((combo, unicidade))

    if melhores:
        melhores.sort(key=lambda x: x[1], reverse=True)
        return list(melhores[0][0])

    return None


def criar_chave_composta(df, colunas):
    return df[colunas].astype(str).agg("|".join, axis=1)


def grafico_historico(hist):
    hist["DATA"] = pd.to_datetime(hist["DATA"])

    fig = px.line(
        hist,
        x="DATA",
        y=["NOVOS", "REMOVIDOS", "ALTERADOS"],
        markers=True,
        title="📈 Histórico de Alterações",
        labels={"value": "Quantidade", "variable": "Tipo"}
    )

    fig.update_layout(
        template="plotly_dark",
        height=450
    )

    st.plotly_chart(fig, use_container_width=True)


def estilo_diff(df):
    return df.style.applymap(
        lambda x: "background-color:#7f1d1d;color:white" if pd.notna(x) else ""
    )

# ===============================
# SIDEBAR
# ===============================
st.sidebar.title("📊 Validador de Integridade")
modo = st.sidebar.radio("Modo:", ["Nova Comparação", "Histórico"])

# ===============================
# NOVA COMPARAÇÃO
# ===============================
if modo == "Nova Comparação":

    st.title("🔎 Comparador de Bases")

    col1, col2 = st.columns(2)
    with col1:
        arq_old = st.file_uploader("📂 Base Antiga", type=["xlsx"])
    with col2:
        arq_new = st.file_uploader("📂 Base Nova", type=["xlsx"])

    if arq_old and arq_new:

        df_old = pd.read_excel(arq_old)
        df_new = pd.read_excel(arq_new)

        df_old.columns = df_old.columns.str.strip()
        df_new.columns = df_new.columns.str.strip()

        st.subheader("🔑 Configuração de Chave")

        colk1, colk2 = st.columns([3, 1])

        with colk1:
            chave = st.multiselect(
                "Selecione a chave (pode ser composta)",
                df_old.columns
            )

        with colk2:
            if st.button("🤖 Detectar Melhor"):
                sugestao = detectar_melhor_chave(df_old)
                if sugestao:
                    chave = sugestao
                    st.success(f"Sugerida: {sugestao}")

        if st.button("🚀 Comparar"):

            if not chave:
                st.error("Selecione ao menos uma coluna como chave.")
                st.stop()

            df_old["CHAVE"] = criar_chave_composta(df_old, chave)
            df_new["CHAVE"] = criar_chave_composta(df_new, chave)

            df_old.set_index("CHAVE", inplace=True)
            df_new.set_index("CHAVE", inplace=True)

            if df_old.index.duplicated().any() or df_new.index.duplicated().any():
                st.error("A chave não é única. Ajuste a seleção.")
                st.stop()

            novos = df_new.loc[~df_new.index.isin(df_old.index)]
            removidos = df_old.loc[~df_old.index.isin(df_new.index)]

            comuns_old = df_old.loc[df_old.index.intersection(df_new.index)]
            comuns_new = df_new.loc[df_old.index.intersection(df_new.index)]

            colunas_comuns = comuns_old.columns.intersection(comuns_new.columns)

            diff = comuns_old[colunas_comuns].compare(
                comuns_new[colunas_comuns]
            )

            # KPIs
            st.markdown("## 📊 Visão Executiva")
            k1, k2, k3 = st.columns(3)

            k1.metric("🆕 Novos", len(novos))
            k2.metric("❌ Removidos", len(removidos))
            k3.metric("✏ Alterados", len(diff))

            st.markdown("---")

            # Diff visual
            st.subheader("🔍 Alterações Detalhadas")
            if not diff.empty:
                st.dataframe(estilo_diff(diff), use_container_width=True)
            else:
                st.success("Nenhuma alteração encontrada.")

            with st.expander("📌 Novos Registros"):
                st.dataframe(novos)

            with st.expander("📌 Registros Removidos"):
                st.dataframe(removidos)

            # Salvar relatório
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            caminho = f"{PASTA_RELATORIOS}/Relatorio_{timestamp}.xlsx"

            with pd.ExcelWriter(caminho) as writer:
                novos.to_excel(writer, "NOVOS")
                removidos.to_excel(writer, "REMOVIDOS")
                diff.to_excel(writer, "ALTERADOS")

            resumo = pd.DataFrame([{
                "DATA": datetime.now(),
                "NOVOS": len(novos),
                "REMOVIDOS": len(removidos),
                "ALTERADOS": len(diff),
                "ARQUIVO": caminho
            }])

            if os.path.exists(HISTORICO_PATH):
                hist = pd.read_csv(HISTORICO_PATH)
                hist = pd.concat([hist, resumo])
            else:
                hist = resumo

            hist.to_csv(HISTORICO_PATH, index=False)

            with open(caminho, "rb") as f:
                st.download_button("⬇ Baixar Relatório", f)

# ===============================
# HISTÓRICO
# ===============================
else:

    st.title("📜 Histórico de Comparações")

    if os.path.exists(HISTORICO_PATH):
        hist = pd.read_csv(HISTORICO_PATH)

        grafico_historico(hist)

        st.markdown("### 📋 Detalhes")
        st.dataframe(hist, use_container_width=True)

    else:
        st.info("Nenhum histórico disponível.")
