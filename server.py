"""
MID TI Dashboard — Servidor local
Rode: python server.py
Acesse: http://localhost:5000
"""
import os, json
from flask import Flask, jsonify, send_from_directory, send_file
import pandas as pd

app = Flask(__name__, static_folder='static', template_folder='templates')

BASE  = os.path.dirname(os.path.abspath(__file__))
EXCEL     = os.path.join(BASE, 'data', 'mid.xlsx')
EXCEL_SLA = os.path.join(BASE, 'data', 'sla.xlsx')

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

def safe_pct(v):
    try:
        f = float(v)
        return round(f * 100, 1)
    except Exception:
        return 0.0

def carregar_sla_jira():
    """
    Lê o sla.xlsx gerado pelo sync_jira.py e converte para o mesmo
    formato de sla_data usado pelo dashboard.
    Colunas esperadas: Mês, Tipo, Indicador, Área, Subárea,
                       Meta, Realizado, Acumulado, Status
    """
    if not os.path.exists(EXCEL_SLA):
        return {}

    df = pd.read_excel(EXCEL_SLA, sheet_name='Report')
    df.columns = [str(c).strip() for c in df.columns]
    df['Mês'] = df['Mês'].apply(norm_mes)

    for c in ['Meta', 'Realizado', 'Acumulado']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # Só Suporte e Satisfação
    df = df[df['Tipo'].isin(['Suporte', 'Satisfação'])].copy()

    # Mapear subárea para o padrão do dashboard
    SUBAREA_MAP = {
        'Data Center':               'DATA CENTER',
        'Redes':                     'REDES',
        'Estação de Trabalho':       'SERVIÇOS (EST. TRABALHO)',
        'Cybersegurança':            'GERAL',
        'Comercial e Inovação':      'COMERCIAL & INOVAÇÃO',
        'Relacionamento e Arrecadação': 'COMERCIAL & INOVAÇÃO',
        'Operações e Engenharia':    'OPERAÇÕES & ENGENHARIA',
        'Finanças e Planejamento':   'FINANÇAS & PLANEJAMENTO',
        'Suprimentos e Apoio':       'SUPRIMENTOS & APOIO',
        'Business Intelligence':     'BI',
    }

    sla_data = {}
    for mes in ORDEM_MESES:
        d = df[df['Mês'] == mes]
        if d.empty:
            continue
        sla_data[mes] = {}
        for _, row in d.iterrows():
            tipo   = row['Tipo']
            area   = str(row.get('Área', '')).strip()
            subarea_raw = str(row.get('Subárea', '')).strip()
            subarea = SUBAREA_MAP.get(subarea_raw, subarea_raw)

            meta = round(float(row['Meta']) * 100, 1) if (pd.notna(row['Meta']) and row['Meta'] > 0) else None
            real = round(float(row['Realizado']) * 100, 1) if pd.notna(row['Realizado']) else 0.0
            acum = round(float(row['Acumulado']) * 100, 1) if pd.notna(row['Acumulado']) else 0.0
            linha = {
                'nome':      'Incidentes/Solicitação (%)' if tipo == 'Suporte' else 'Satisfação (%)',
                'tipo':      tipo,
                'meta':      meta,
                'realizado': real,
                'acumulado': acum,
                'status':    str(row.get('Status', '')).upper().strip() or 'J',
                'info_only': tipo == 'Satisfação' and area == 'Sistemas',
                'area':      area,
            }

            if subarea not in sla_data[mes]:
                sla_data[mes][subarea] = {'area': area, 'linhas': []}
            sla_data[mes][subarea]['linhas'].append(linha)

    return sla_data


def carregar_dados():
    if not os.path.exists(EXCEL):
        return None, None

    df = pd.read_excel(EXCEL, sheet_name='Report')
    df.columns = [str(c).strip() for c in df.columns]
    df['Mês'] = df['Mês'].apply(norm_mes)
    for c in ['Meta', 'Realizado', 'Acumulado']:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # ── SLA: tenta sla.xlsx primeiro, fallback para mid.xlsx ──────────────
    sla_data = carregar_sla_jira()

    if not sla_data:
        # Fallback: lê SLA do mid.xlsx como antes
        df_sla = df[df['Tipo'].isin(['Suporte', 'Satisfação'])].copy()
        df_sla[['area', 'subarea']] = df_sla['Indicador'].apply(
            lambda x: pd.Series(classificar(x))
        )
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
                            'nome':      'Incidentes/Solicitação (%)' if tipo == 'Suporte' else 'Satisfação (%)',
                            'tipo':      tipo,
                            'meta':      meta,
                            'realizado': round(float(row['Realizado']) * 100, 1),
                            'acumulado': round(float(row['Acumulado']) * 100, 1),
                            'status':    str(row['Status']).upper().strip(),
                            'info_only': tipo == 'Satisfação' and area == 'Sistemas',
                            'area':      area,
                        })
                    if linhas:
                        sla_data[mes][sub] = {'area': area, 'linhas': linhas}

    # ── PROJETOS (Tipo = Projeto ou Compartilhado) ─────────────────────────
    df_proj = df[df['Tipo'].isin(['Projeto', 'Compartilhado'])].copy()

    # Agrupar por indicador: cada indicador tem 12 linhas (uma por mês)
    proj_data = []
    for indicador, grp in df_proj.groupby('Indicador', sort=False):
        ref = grp.iloc[0]
        tipo      = str(ref.get('Tipo', 'Projeto')).strip()
        resp      = str(ref.get('Responsável', '')).strip()
        marcos    = str(ref.get('Marcos', '')).strip() if 'Marcos' in grp.columns else ''
        status    = str(ref.get('Status', '')).upper().strip()
        compartilhado = 'Sim' if tipo == 'Compartilhado' else 'Não'

        # Montar valores por mês (índice 0=jan … 11=dez)
        meta_vals  = [0.0] * 12
        real_vals  = [0.0] * 12
        acum_vals  = [0.0] * 12

        for _, row in grp.iterrows():
            mes = row['Mês']
            if mes not in ORDEM_MESES:
                continue
            idx = ORDEM_MESES.index(mes)
            meta_vals[idx] = safe_pct(row['Meta'])
            real_vals[idx] = safe_pct(row['Realizado'])
            acum_vals[idx] = safe_pct(row['Acumulado'])

        proj_data.append({
            'indicador':     indicador,
            'tipo':          tipo,
            'compartilhado': compartilhado,
            'responsavel':   resp,
            'marcos':        marcos,
            'status':        status,
            'meses': {
                'Meta':      meta_vals,
                'Realizado': real_vals,
                'Acumulado': acum_vals,
            }
        })

    # Ordenar: Projetos primeiro, depois Compartilhados; dentro de cada grupo, por nome
    proj_data.sort(key=lambda p: (0 if p['tipo'] == 'Projeto' else 1, p['indicador']))

    return sla_data, proj_data


# ── Rotas ─────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_file(os.path.join(BASE, 'templates', 'index.html'))

@app.route('/api/dados')
def api_dados():
    sla, projetos = carregar_dados()
    if sla is None:
        return jsonify({'erro': f'Arquivo não encontrado: {EXCEL}'}), 404
    return jsonify({
        'sla':         sla,
        'projetos':    projetos,
        'ordem_meses': ORDEM_MESES,
        'meses_abrev': MESES_ABREV,
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
