import streamlit as st
import pandas as pd
from utils.loader import carregar_dados

# Configuração da página
st.set_page_config(layout="wide", page_title="SLA por Área")

# --- STREAMING_CHUNK: Definindo Estilos CSS ---
st.markdown("""
    <style>
    .area-container {
        margin-bottom: 25px;
        border: 1px solid #004a8d;
    }
    .area-header-top {
        background-color: #cce0f1;
        color: #002b5b;
        text-align: center;
        padding: 8px;
        font-weight: bold;
        font-size: 1.2em;
        text-transform: uppercase;
        border-bottom: 2px solid #004a8d;
    }
    .subarea-header {
        background-color: #004a8d;
        color: white;
        text-align: center;
        padding: 6px;
        font-weight: bold;
        font-size: 1.1em;
        text-transform: uppercase;
    }
    .table-row-header {
        display: flex;
        background-color: #e3effa;
        color: #002b5b;
        font-weight: bold;
        text-align: center;
        border-bottom: 1px solid #004a8d;
    }
    .table-row {
        display: flex;
        background-color: white;
        border-bottom: 1px solid #cce0f1;
        align-items: center;
    }
    .col-indicador { flex: 2; padding: 10px; border-right: 2px solid #004a8d; font-weight: bold; }
    .col-meta { flex: 1; text-align: center; padding: 10px; border-right: 2px solid #004a8d; }
    .col-resultado { flex: 1.5; text-align: center; padding: 10px; border-right: 2px solid #004a8d; }
    .col-status { flex: 0.8; text-align: center; padding: 10px; display: flex; justify-content: center; }
    
    .dot {
        height: 18px;
        width: 18px;
        border-radius: 50%;
        display: inline-block;
    }
    .dot-green { background-color: #8bc34a; box-shadow: 0 0 5px #8bc34a; }
    .dot-red { background-color: #ff0000; box-shadow: 0 0 5px #ff0000; }
    .dot-gray { background-color: #ccc; }
    </style>
""", unsafe_allow_html=True)

# --- Função para Gerar a Tabela de Subárea ---
def criar_tabela_subarea(subarea, dados):
    """Gera o HTML para uma subárea com múltiplos indicadores."""
    html = f'<div class="subarea-header">{subarea}</div>'
    html += """
    <div class="table-row-header">
        <div class="col-indicador">Indicador</div>
        <div class="col-meta">Meta</div>
        <div class="col-resultado">Resultado Apurado</div>
        <div class="col-status">Status</div>
    </div>
    """
    
    for item in dados:
        indicador = item['indicador']
        meta = item['meta']
        real = item['resultado']
        is_info_only = item.get('info_only', False)
        
        # Lógica do Farol
        if is_info_only:
            status_class = "dot-gray"
        else:
            status_class = "dot-green" if real >= meta else "dot-red"
            
        meta_str = f"{meta:.1f}%" if meta else "--"
        
        html += f"""
        <div class="table-row">
            <div class="col-indicador">{indicador}</div>
            <div class="col-meta">{meta_str}</div>
            <div class="col-resultado">{real:.1f}%</div>
            <div class="col-status"><span class="dot {status_class}"></span></div>
        </div>
        """
    return html

# --- Carregar dados ---
df = carregar_dados()

# Verificar se o DataFrame está vazio
if df.empty:
    st.error("❌ Nenhum dado encontrado. Verifique o arquivo de dados.")
    st.stop()

# --- Cabeçalho ---
st.markdown("<h3 style='color: #002b5b; margin-bottom: 0;'>MID TI - 2026</h3>", unsafe_allow_html=True)
st.markdown("<p style='color: #004a8d; font-weight: bold;'>SLA de Incidentes/Solicitação e Satisfação por Área</p>", unsafe_allow_html=True)

# --- Filtro de Mês ---
meses = sorted(df['Mês'].unique())
mes_ref = st.selectbox("📅 Mês Referência", meses, index=len(meses)-1)

# Filtrar dados pelo mês selecionado
df_filtrado = df[df['Mês'] == mes_ref]

# --- Dicionário de configuração das áreas/subáreas/indicadores ---
# Estrutura: Área -> Subárea -> Lista de indicadores (com mapeamento para o DataFrame)
config_areas = {
    "Infraestrutura": {
        "DATA CENTER": {
            "indicadores": [
                {"nome": "Incidentes/Solicitação (%)", "col_meta": "Meta_INC_SOL", "col_resultado": "Resultado_INC_SOL"},
                {"nome": "Satisfação (%)", "col_meta": "Meta_SAT", "col_resultado": "Resultado_SAT"}
            ]
        },
        "REDES": {
            "indicadores": [
                {"nome": "Incidentes/Solicitação (%)", "col_meta": "Meta_INC_SOL", "col_resultado": "Resultado_INC_SOL"},
                {"nome": "Satisfação (%)", "col_meta": "Meta_SAT", "col_resultado": "Resultado_SAT"}
            ]
        }
    },
    "Cybersegurança": {
        "GERAL": {
            "indicadores": [
                {"nome": "Incidentes/Solicitação (%)", "col_meta": "Meta_INC_SOL", "col_resultado": "Resultado_INC_SOL"},
                {"nome": "Satisfação (%)", "col_meta": "Meta_SAT", "col_resultado": "Resultado_SAT"}
            ]
        }
    },
    "Sistemas": {
        "OPERAÇÕES E ENGENHARIA": {
            "info_only_satisfacao": True,  # Satisfação apenas informativa
            "indicadores": [
                {"nome": "Incidentes/Solicitação (%)", "col_meta": "Meta_INC_SOL", "col_resultado": "Resultado_INC_SOL"},
                {"nome": "Satisfação (%)", "col_meta": "Meta_SAT", "col_resultado": "Resultado_SAT"}
            ]
        },
        "COMERCIAL E INOVAÇÃO": {
            "info_only_satisfacao": True,
            "indicadores": [
                {"nome": "Incidentes/Solicitação (%)", "col_meta": "Meta_INC_SOL", "col_resultado": "Resultado_INC_SOL"},
                {"nome": "Satisfação (%)", "col_meta": "Meta_SAT", "col_resultado": "Resultado_SAT"}
            ]
        },
        "FINANÇAS E PLANEJAMENTO": {
            "info_only_satisfacao": True,
            "indicadores": [
                {"nome": "Incidentes/Solicitação (%)", "col_meta": "Meta_INC_SOL", "col_resultado": "Resultado_INC_SOL"},
                {"nome": "Satisfação (%)", "col_meta": "Meta_SAT", "col_resultado": "Resultado_SAT"}
            ]
        }
    }
}

# --- Função para extrair dados do DataFrame ---
def get_dados_subarea(df_filtrado, area, subarea, config_subarea):
    """Extrai os dados do DataFrame para uma subarea específica"""
    # Filtrar linha correspondente à área e subárea
    linha = df_filtrado[(df_filtrado['Área'] == area) & (df_filtrado['Subárea'] == subarea)]
    
    if linha.empty:
        return []
    
    dados = []
    for indicador_config in config_subarea['indicadores']:
        meta_col = indicador_config['col_meta']
        resultado_col = indicador_config['col_resultado']
        
        meta_val = linha[meta_col].values[0] if meta_col in linha.columns else 0
        resultado_val = linha[resultado_col].values[0] if resultado_col in linha.columns else 0
        
        # Verificar se é indicador de satisfação e se deve ser apenas informativo
        is_info_only = False
        if "Satisfação" in indicador_config['nome'] and config_subarea.get('info_only_satisfacao', False):
            is_info_only = True
        
        dados.append({
            "indicador": indicador_config['nome'],
            "meta": meta_val,
            "resultado": resultado_val,
            "info_only": is_info_only
        })
    
    return dados

# --- Renderização do Dashboard ---
col_left, col_right = st.columns(2)

with col_left:
    # INFRAESTRUTURA
    if "Infraestrutura" in config_areas:
        st.markdown('<div class="area-header-top">Infraestrutura</div>', unsafe_allow_html=True)
        with st.container():
            for subarea, config_subarea in config_areas["Infraestrutura"].items():
                dados = get_dados_subarea(df_filtrado, "Infraestrutura", subarea, config_subarea)
                if dados:
                    st.markdown(criar_tabela_subarea(subarea, dados), unsafe_allow_html=True)
                else:
                    st.warning(f"Dados não encontrados para {subarea} em {mes_ref}")
    
    # CYBERSEGURANÇA
    if "Cybersegurança" in config_areas:
        st.markdown('<div class="area-header-top">Cybersegurança</div>', unsafe_allow_html=True)
        for subarea, config_subarea in config_areas["Cybersegurança"].items():
            dados = get_dados_subarea(df_filtrado, "Cybersegurança", subarea, config_subarea)
            if dados:
                st.markdown(criar_tabela_subarea(subarea, dados), unsafe_allow_html=True)
            else:
                st.warning(f"Dados não encontrados para {subarea} em {mes_ref}")

with col_right:
    # SISTEMAS
    if "Sistemas" in config_areas:
        st.markdown('<div class="area-header-top">Sistemas</div>', unsafe_allow_html=True)
        for subarea, config_subarea in config_areas["Sistemas"].items():
            dados = get_dados_subarea(df_filtrado, "Sistemas", subarea, config_subarea)
            if dados:
                st.markdown(criar_tabela_subarea(subarea, dados), unsafe_allow_html=True)
            else:
                st.warning(f"Dados não encontrados para {subarea} em {mes_ref}")

st.divider()
st.caption("⚠️ O cálculo do SLA de Incidentes é a soma dos Incidentes + Solicitações. | Satisfação de Sistemas é informativo.")