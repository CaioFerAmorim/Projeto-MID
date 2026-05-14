import streamlit as st
import pandas as pd
import os

MESES_PT = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}
ORDEM_MESES = list(MESES_PT.values())


def normalizar_mes(valor):
    """Converte qualquer formato de mês para texto padronizado."""
    if valor is None:
        return None
    try:
        if pd.isna(valor):
            return None
    except Exception:
        pass

    if hasattr(valor, 'month'):
        return MESES_PT[valor.month]

    try:
        num = int(float(str(valor)))
        if 1 <= num <= 12:
            return MESES_PT[num]
    except (ValueError, TypeError):
        pass

    s = str(valor).strip()
    if '/' in s:
        try:
            data = pd.to_datetime(s, dayfirst=True)
            return MESES_PT[data.month]
        except Exception:
            pass

    s_lower = s.lower()
    for num, nome in MESES_PT.items():
        if s_lower == nome.lower() or s_lower == nome.lower()[:3]:
            return nome

    return s.capitalize()


def normalizar_percentual(serie):
    """Converte coluna percentual para float 0–1."""
    s = (serie.astype(str)
         .str.replace('%', '', regex=False)
         .str.replace(',', '.', regex=False)
         .str.strip()
         .replace({'': '0', 'nan': '0', 'none': '0', '-': '0',
                   'None': '0', 'NaN': '0'}))
    num = pd.to_numeric(s, errors='coerce').fillna(0)
    return num.apply(lambda x: x / 100 if x > 1 else x)


def mapear_status(val):
    v = str(val).upper().strip()
    if v == 'J':
        return 'Em dia'
    if v == 'L':
        return 'Atrasado'
    return 'Sem status'


@st.cache_data
def carregar_dados():
    """Carrega mid.xlsx da pasta data/ e normaliza colunas essenciais."""
    base = os.path.dirname(os.path.abspath(__file__))
    caminhos = [
        os.path.join(base, '..', 'data', 'mid.xlsx'),
        os.path.join(base, '..', 'dados', 'mid.xlsx'),
        'data/mid.xlsx',
        'dados/mid.xlsx',
    ]

    df = None
    for p in caminhos:
        p = os.path.normpath(p)
        if os.path.exists(p):
            df = pd.read_excel(p)
            break

    if df is None:
        st.error("❌ Arquivo **mid.xlsx** não encontrado. Coloque-o em `data/mid.xlsx`.")
        st.stop()

    # Normalizar nomes de colunas
    df.columns = [str(c).strip() for c in df.columns]

    # Normalizar mês
    if 'Mês' in df.columns:
        df['Mês'] = df['Mês'].apply(normalizar_mes)

    # Normalizar colunas percentuais se existirem
    for col in ['Meta', 'Realizado', 'Acumulado',
                'Meta_INC', 'Realizado_INC', 'Meta_SAT', 'Realizado_SAT']:
        if col in df.columns:
            df[col] = normalizar_percentual(df[col])

    # Normalizar status
    if 'Status' in df.columns:
        df['Status_Label'] = df['Status'].apply(mapear_status)

    return df