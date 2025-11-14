import io
from typing import Optional, Tuple

import pandas as pd
import streamlit as st


st.set_page_config(page_title="Base Campanha", page_icon=":bar_chart:", layout="centered")
st.image("Logo-Ejabrasil-sem-fundo.png.webp", width=260)
st.title("Base Campanha")
st.markdown("Organize e limpe suas bases de campanha de forma automática :rocket:")

# Upload dos arquivos
kpi_file = st.file_uploader("Importar KPI", type=["xls", "xlsx", "xlsm", "xlsb", "csv"])
fid_file = st.file_uploader("Importar Fidelizados", type=["xls", "xlsx", "xlsm", "xlsb", "csv"])
painel_file = st.file_uploader("Importar Painel", type=["xls", "xlsx", "xlsm", "xlsb", "csv"])

@st.cache_data
def carregar(arquivo) -> Optional[pd.DataFrame]:
    """Carrega um arquivo enviado pelo usuário para um DataFrame."""

    if arquivo is None:
        return None

    extensao = arquivo.name.split(".")[-1].lower()

    if extensao == "csv":
        return pd.read_csv(arquivo)
    if extensao == "xls":
        return pd.read_excel(arquivo, engine="xlrd")
    if extensao in {"xlsx", "xlsm"}:
        return pd.read_excel(arquivo, engine="openpyxl")
    if extensao == "xlsb":
        return pd.read_excel(arquivo, engine="pyxlsb")

    return None


def _normalizar_telefone(coluna: pd.Series) -> pd.Series:
    """Remove caracteres não numéricos da coluna informada."""

    return coluna.astype(str).str.replace(r"\D", "", regex=True)


def limpeza_e_processamento(
    kpi: Optional[pd.DataFrame],
    fidelizados: Optional[pd.DataFrame],
    painel: Optional[pd.DataFrame],
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Executa a limpeza das bases e prepara os dados finais."""

    if kpi is None or kpi.empty:
        return None, None

    kpi = kpi.copy()

    if "Whatsapp Principal" not in kpi.columns:
        return None, None

    # --- Limpeza KPI ---
    kpi["Whatsapp Principal"] = _normalizar_telefone(kpi["Whatsapp Principal"])

    if "Observação" in kpi.columns:
        kpi = kpi[
            kpi["Observação"].astype(str).str.contains(
                "Médio|Fundamental", case=False, na=False
            )
        ]

    # Limpeza Fidelizados
    if fidelizados is not None and not fidelizados.empty:
        fidelizados = fidelizados.copy()
        if "Whatsapp Principal" in fidelizados.columns:
            fidelizados["Whatsapp Principal"] = _normalizar_telefone(
                fidelizados["Whatsapp Principal"]
            )
            kpi = kpi[~kpi["Whatsapp Principal"].isin(fidelizados["Whatsapp Principal"])]

    # Limpeza Painel
    if painel is not None and not painel.empty:
        painel = painel.copy()
        if "Telefone (cobrança)" in painel.columns:
            painel["Telefone (cobrança)"] = _normalizar_telefone(
                painel["Telefone (cobrança)"]
            )
            kpi = kpi[~kpi["Whatsapp Principal"].isin(painel["Telefone (cobrança)"])]

    if kpi.empty:
        return None, None

    # Manter apenas as colunas principais
    keep_cols = [
        coluna
        for coluna in ["Contato", "Observação", "Whatsapp Principal"]
        if coluna in kpi.columns
    ]

    kpi = kpi[keep_cols].drop_duplicates(subset=["Whatsapp Principal"]).reset_index(drop=True)

    if kpi.empty:
        return None, None

    # Renomear colunas
    kpi = kpi.rename(
        columns={
            "Contato": "Nome",
            "Whatsapp Principal": "Numero",
            "Observação": "Tipo",
        }
    )

    if "Numero" not in kpi.columns:
        return None, None

    if "Nome" in kpi.columns:
        nomes = kpi["Nome"].astype(str).str.split().str[0].str.upper()
        kpi["Nome"] = nomes.mask(nomes.str.len().between(1, 3), "CANDIDATO")
    else:
        kpi["Nome"] = "CANDIDATO"

    # Criar aba nome
    aba_nome = kpi[["Nome", "Numero"]].drop_duplicates(subset=["Nome"]).rename(
        columns={"Numero": "Telefone"}
    )

    return kpi, aba_nome

if st.button("Gerar Base"):
    with st.spinner("Processando, aguarde..."):
        kpi = carregar(kpi_file)
        fidelizados = carregar(fid_file)
        painel = carregar(painel_file)
        kpi_final, aba_nome = limpeza_e_processamento(kpi, fidelizados, painel)
        if kpi_final is None:
            st.error("Base KPI inválida ou não carregada!")
        else:
            # Gera Excel em memória
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                if kpi_final is not None:
                    kpi_final.to_excel(writer, sheet_name="kpi", index=False)
                if aba_nome is not None:
                    aba_nome.to_excel(writer, sheet_name="nome", index=False)
                if fidelizados is not None:
                    fidelizados.to_excel(writer, sheet_name="fidelizados", index=False)
                if painel is not None:
                    painel.to_excel(writer, sheet_name="painel", index=False)
            st.success("Processamento finalizado!")
            st.download_button("Baixar Excel Final", output.getvalue(), file_name="base_campanha_final.xlsx")

st.markdown("---")
st.caption("Desenvolvido por Base Campanha - Gratuito para sempre.")
