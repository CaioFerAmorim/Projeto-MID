"""
MID TI Dashboard — Servidor local
Rode: python server.py
Acesse: http://localhost:5000
"""
import os, json
from flask import Flask, jsonify, send_from_directory, send_file
import pandas as pd

app = Flask(__name__, static_folder='static', template_folder='templates')

BASE   = os.path.dirname(os.path.abspath(__file__))
EXCEL  = os.path.join(BASE, 'data', 'mid.xlsx')

# ── Mapeamento de nomes ──────────────────────────────────────────────────────
MESES_PT = {
    1:'Janeiro',2:'Fevereiro',3:'Março',4:'Abril',5:'Maio',6:'Junho',
    7:'Julho',8:'Agosto',9:'Setembro',10:'Outubro',11:'Novembro',12:'Dezembro'
}
ORDEM_MESES = list(MESES_PT.values())
MESES_ABREV = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
COLS_MESES  = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']

MAPA_AREAS = [
    ('Datacenter',                'Infraestrutura', 'DATA CENTER'),
    ('Redes',                     'Infraestrutura', 'REDES'),
    ('Estação de Trabalho',       'Infraestrutura', 'SERVIÇOS (EST. TRABALHO)'),
    ('Serviços',                  'Infraestrutura', 'SERVIÇOS (EST. TRABALHO)'),
    ('Cybersegurança',            'Cybersegurança', 'GERAL'),
    ('Comercial & Inovação',      'Sistemas',       'COMERCIAL & INOVAÇÃO'),
    ('Comercial (Relacionamento', 'Sistemas',       'COMERCIAL & INOVAÇÃO'),
    ('Suprimentos',               'Sistemas',       'SUPRIMENTOS & APOIO'),
    ('Finanças',                  'Sistemas',       'FINANÇAS & PLANEJAMENTO'),
    ('Planejamento',              'Sistemas',       'FINANÇAS & PLANEJAMENTO'),
    ('Operações',                 'Sistemas',       'OPERAÇÕES & ENGENHARIA'),
    ('BI',                        'Sistemas',       'BI'),
]

def classificar(ind):
    for frag, area, sub in MAPA_AREAS:
        if frag.lower() in str(ind).lower():
            return area, sub
    return 'Outros', 'GERAL'

def norm_mes(v):
    if v is None: return None
    try:
        if pd.isna(v): return None
    except Exception: pass
    if hasattr(v, 'month'): return MESES_PT[v.month]
    try:
        n = int(float(str(v)))
        if 1 <= n <= 12: return MESES_PT[n]
    except Exception: pass
    s = str(v).strip()
    if '/' in s:
        try: return MESES_PT[pd.to_datetime(s, dayfirst=True).month]
        except Exception: pass
    sl = s.lower()
    for n, nome in MESES_PT.items():
        if sl == nome.lower() or sl == nome.lower()[:3]: return nome
    return s.capitalize()

# ── Carrega e processa o Excel ───────────────────────────────────────────────
def carregar_dados():
    if not os.path.exists(EXCEL):
        return None, None

    # ── Aba Report ─────────────────────────────────────────────────────────
    df = pd.read_excel(EXCEL, sheet_name='Report')
    df.columns = [str(c).strip() for c in df.columns]
    df['Mês'] = df['Mês'].apply(norm_mes)
    for c in ['Meta', 'Realizado', 'Acumulado']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    df_sla = df[df['Tipo'].isin(['Suporte', 'Satisfação'])].copy()
    df_sla[['area', 'subarea']] = df_sla['Indicador'].apply(
        lambda x: pd.Series(classificar(x))
    )

    # Montar JSON de SLA: { mes: { subarea: { area, linhas[] } } }
    sla_data = {}
    for mes in ORDEM_MESES:
        d = df_sla[df_sla['Mês'] == mes]
        if d.empty: continue
        sla_data[mes] = {}
        for area in ['Infraestrutura', 'Cybersegurança', 'Sistemas', 'Outros']:
            da = d[d['area'] == area]
            for sub in da['subarea'].unique():
                ds = da[da['subarea'] == sub]
                linhas = []
                for _, row in ds.iterrows():
                    tipo = row['Tipo']
                    meta = round(float(row['Meta']) * 100, 1) if row['Meta'] > 0 else None
                    linhas.append({
                        'nome':       'Incidentes/Solicitação (%)' if tipo == 'Suporte' else 'Satisfação (%)',
                        'tipo':       tipo,
                        'meta':       meta,
                        'realizado':  round(float(row['Realizado'])  * 100, 1),
                        'acumulado':  round(float(row['Acumulado'])  * 100, 1),
                        'status':     str(row['Status']).upper().strip(),
                        'info_only':  tipo == 'Satisfação' and area == 'Sistemas',
                        'area':       area,
                    })
                if linhas:
                    sla_data[mes][sub] = {'area': area, 'linhas': linhas}

    # ── Aba Visão ──────────────────────────────────────────────────────────
    raw = pd.read_excel(EXCEL, sheet_name='Visão', header=None)
    cols = [str(c).strip() if str(c) not in ('nan', 'None') else f'_c{i}'
            for i, c in enumerate(raw.iloc[1])]
    dv = raw.iloc[2:].copy()
    dv.columns = cols
    dv = dv.reset_index(drop=True)
    for c in ['ID', 'Indicador', 'Responsável', 'Marcos', 'Status']:
        if c in dv.columns:
            dv[c] = dv[c].ffill()
    for c in ['Métrica', 'Status', 'Indicador', 'Responsável']:
        if c in dv.columns:
            dv[c] = dv[c].astype(str).str.strip().replace({'nan': '', 'None': ''})
    for m in COLS_MESES:
        if m in dv.columns:
            dv[m] = pd.to_numeric(dv[m], errors='coerce').fillna(0)

    proj_data = []
    for pid in dv['ID'].dropna().unique():
        dp = dv[dv['ID'] == pid]
        if dp.empty: continue
        ref = dp[dp['Métrica'] == 'Meta']
        if ref.empty: ref = dp.iloc[[0]]
        r = ref.iloc[0]
        meses_vals = {}
        for metr in ['Meta', 'Realizado', 'Acumulado']:
            row_m = dp[dp['Métrica'] == metr]
            if row_m.empty: continue
            rv = row_m.iloc[0]
            meses_vals[metr] = [
                round(float(rv[c]) * 100, 1) if c in rv.index else 0
                for c in COLS_MESES
            ]
        proj_data.append({
            'id':          str(pid),
            'indicador':   str(r.get('Indicador', '')),
            'responsavel': str(r.get('Responsável', '')),
            'marcos':      str(r.get('Marcos', '')),
            'status':      str(r.get('Status', '')),
            'meses':       meses_vals,
        })

    return sla_data, proj_data


# ── Rotas ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_file(os.path.join(BASE, 'templates', 'index.html'))

@app.route('/api/dados')
def api_dados():
    """Retorna todos os dados do Excel em JSON. Lê o arquivo a cada chamada."""
    sla, projetos = carregar_dados()
    if sla is None:
        return jsonify({'erro': f'Arquivo não encontrado: {EXCEL}'}), 404
    return jsonify({
        'sla':          sla,
        'projetos':     projetos,
        'ordem_meses':  ORDEM_MESES,
        'meses_abrev':  MESES_ABREV,
    })

@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    print("\n" + "="*50)
    print("  MID TI Dashboard rodando!")
    print("  Acesse: http://localhost:5000")
    print("  Ctrl+C para parar")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)
