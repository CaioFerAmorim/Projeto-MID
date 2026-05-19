"""
sync_jira.py — Extrai dados de SLA do Jira Service Management
e salva em data/sla.xlsx no formato esperado pelo dashboard.

Uso:
    python sync_jira.py              # extrai ano atual (2026)
    python sync_jira.py --mes 4      # extrai só abril
    python sync_jira.py --full       # reextrai todos os meses

Agendamento sugerido (Task Scheduler):
    Diariamente às 7h antes de abrir o dashboard.
"""
import os, sys, argparse, math
from datetime import datetime, date
import requests
import pandas as pd
from dotenv import load_dotenv

# ── Configuração ──────────────────────────────────────────────────────────────
load_dotenv('api.env')

EMAIL = os.getenv('JIRA_EMAIL')
TOKEN = os.getenv('JIRA_TOKEN')
URL   = os.getenv('JIRA_URL', '').rstrip('/')
AUTH  = (EMAIL, TOKEN)
HEADERS = {'Accept': 'application/json', 'Content-Type': 'application/json'}

ANO_BASE   = 2026
EXCEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sla.xlsx')

MESES_PT = {
    1:'Janeiro', 2:'Fevereiro', 3:'Março',    4:'Abril',
    5:'Maio',    6:'Junho',     7:'Julho',     8:'Agosto',
    9:'Setembro',10:'Outubro', 11:'Novembro', 12:'Dezembro'
}

# ── Campos SLA (descobertos via explorar_jira.py) ─────────────────────────────
# Resolução é o campo relevante para cálculo de SLA (não triagem)
CAMPOS_SLA = {
    'customfield_10272': 'SLA Incidente de Infraestrutura - Resolução',
    'customfield_10438': 'SLA Incidente de Sistemas - Resolução',
    'customfield_10317': 'SLA Requisição de Infraestrutura - Resolução',
    'customfield_10274': 'SLA Requisição de Sistemas - Resolução',
    'customfield_10315': 'SLA Requisição de Serviços Administrativos - Resolução',
}
CAMPO_FILA = 'customfield_10268'
CAMPO_SAT  = 'customfield_10075'

# ── Mapeamento de área (baseado na query SQL do BI) ───────────────────────────
FILAS_SISTEMAS = {
    'Funcional Comercial', 'Funcional Operações', 'Funcional Contábil',
    'Funcional Financeiro', 'Funcional Fiscal', 'Funcional Planejamento',
    'Funcional Acesso', 'Funcional Administrativo', 'Funcional Compliance',
    'Funcional Comunicação', 'Funcional Jurídico', 'Funcional RH',
    'Funcional Suprimentos', 'Funcional Sustentabilidade',
}
RESPONSAVEL_REL_ARREC = 'Ana Paula Cunha Pacheco de Oliveira'

def classificar_area(tipo_issue: str, fila: str, responsavel: str) -> str:
    tipo  = (tipo_issue or '').strip()
    fila  = (fila or '').strip()
    resp  = (responsavel or '').strip()

    if 'Sistemas de Apoio ao Negócio' in tipo:
        if fila == 'Funcional Comercial' and resp == RESPONSAVEL_REL_ARREC:
            return 'Relacionamento e Arrecadação'
        if fila == 'Funcional Comercial':
            return 'Comercial e Inovação'
        if fila == 'Funcional Operações':
            return 'Operações e Engenharia'
        if fila in {'Funcional Contábil','Funcional Financeiro',
                    'Funcional Fiscal','Funcional Planejamento'}:
            return 'Finanças e Planejamento'
        if fila in {'Funcional Acesso','Funcional Administrativo','Funcional Compliance',
                    'Funcional Comunicação','Funcional Jurídico','Funcional RH',
                    'Funcional Suprimentos','Funcional Sustentabilidade'}:
            return 'Suprimentos e Apoio'

    if 'Data Center' in fila:        return 'Data Center'
    if 'Redes' in fila:              return 'Redes'
    if 'Segurança da Informação' in fila: return 'Cybersegurança'
    if 'Estação de Trabalho' in tipo: return 'Estação de Trabalho'
    if 'Business Intelligence' in tipo: return 'Business Intelligence'

    return 'Outras Áreas / Não Mapeado'

# ── Mapeamento área → Área + Subárea do dashboard ────────────────────────────
AREA_DASH = {
    'Data Center':               ('Infraestrutura', 'DATA CENTER'),
    'Redes':                     ('Infraestrutura', 'REDES'),
    'Estação de Trabalho':       ('Infraestrutura', 'SERVIÇOS (EST. TRABALHO)'),
    'Cybersegurança':            ('Cybersegurança', 'GERAL'),
    'Comercial e Inovação':      ('Sistemas', 'COMERCIAL & INOVAÇÃO'),
    'Relacionamento e Arrecadação': ('Sistemas', 'COMERCIAL & INOVAÇÃO'),
    'Operações e Engenharia':    ('Sistemas', 'OPERAÇÕES & ENGENHARIA'),
    'Finanças e Planejamento':   ('Sistemas', 'FINANÇAS & PLANEJAMENTO'),
    'Suprimentos e Apoio':       ('Sistemas', 'SUPRIMENTOS & APOIO'),
    'Business Intelligence':     ('Sistemas', 'BI'),
}

# ── Funções de API ────────────────────────────────────────────────────────────
def buscar_chamados(mes: int) -> list:
    """Busca todos os chamados resolvidos num mês específico."""
    ano       = ANO_BASE
    inicio    = f"{ano}-{mes:02d}-01"
    # Último dia do mês
    if mes == 12:
        fim = f"{ano+1}-01-01"
    else:
        fim = f"{ano}-{mes+1:02d}-01"

    jql = (f'project in (INC,SOL) '
           f'AND statusCategory = Done '
           f'AND resolved >= "{inicio}" '
           f'AND resolved < "{fim}"')

    campos = list(CAMPOS_SLA.keys()) + [
        CAMPO_FILA, CAMPO_SAT,
        'summary', 'issuetype', 'status',
        'assignee', 'resolutiondate', 'created'
    ]

    todos = []
    next_token = None
    page = 100

    while True:
        body = {
            'jql':        jql,
            'fields':     campos,
            'maxResults': page,
        }
        if next_token:
            body['nextPageToken'] = next_token

        r = requests.post(
            f"{URL}/rest/api/3/search/jql",
            auth=AUTH, headers=HEADERS,
            json=body
        )
        if not r.ok:
            print(f"\nErro {r.status_code}: {r.text[:500]}")
        r.raise_for_status()

        data   = r.json()
        issues = data.get('issues', [])
        todos.extend(issues)

        total = data.get('total', len(todos))
        print(f"  Buscando... {len(todos)}/{total}", end='\r')

        next_token = data.get('nextPageToken')
        if not next_token or not issues:
            break

    print(f"  Total: {len(todos)} chamados encontrados.     ")
    return todos


def extrair_sla_breached(fields: dict) -> bool | None:
    """
    Retorna True se SLA foi violado, False se cumprido, None se não aplicável.
    Usa o mesmo critério da query SQL: greatest() de todos os campos de resolução.
    """
    resultados = []
    for campo in CAMPOS_SLA:
        v = fields.get(campo)
        if not v: continue
        cycles = v.get('completedCycles', [])
        if cycles:
            # Último ciclo completado
            resultados.append(cycles[-1].get('breached', None))

    if not resultados:
        return None
    # Se qualquer campo de resolução foi violado → violado
    return any(b is True for b in resultados if b is not None)


def extrair_avaliacao(fields: dict) -> float | None:
    """Retorna a nota de satisfação (1-5) ou None."""
    v = fields.get(CAMPO_SAT)
    if v is None: return None
    if isinstance(v, dict): return v.get('rating')
    try: return float(v)
    except Exception: return None


def processar_mes(mes: int) -> pd.DataFrame:
    """Extrai e agrega os dados de um mês em DataFrame."""
    print(f"\n{'='*50}")
    print(f"Processando: {MESES_PT[mes]}/{ANO_BASE}")
    print(f"{'='*50}")

    chamados = buscar_chamados(mes)
    if not chamados:
        print("  Nenhum chamado encontrado.")
        return pd.DataFrame()

    linhas = []
    for issue in chamados:
        f    = issue['fields']
        tipo = (f.get('issuetype') or {}).get('name', '')
        fila = ((f.get(CAMPO_FILA) or {}).get('value', '')
                if isinstance(f.get(CAMPO_FILA), dict)
                else str(f.get(CAMPO_FILA) or ''))
        resp = ((f.get('assignee') or {}).get('displayName', ''))
        area = classificar_area(tipo, fila, resp)

        breached   = extrair_sla_breached(f)
        avaliacao  = extrair_avaliacao(f)

        linhas.append({
            'key':       issue['key'],
            'area':      area,
            'breached':  breached,   # True=fora, False=dentro, None=sem SLA
            'avaliacao': avaliacao,  # 1-5 ou None
        })

    df = pd.DataFrame(linhas)

    # ── Agregação por área ────────────────────────────────────────────────────
    rows = []
    for area, grp in df.groupby('area'):
        if area not in AREA_DASH: continue

        area_dash, subarea_dash = AREA_DASH[area]
        total    = len(grp)
        com_sla  = grp['breached'].notna()
        dentro   = (grp['breached'] == False).sum()
        fora     = (grp['breached'] == True).sum()
        sem_sla  = (~com_sla).sum()
        pct_sla  = round(dentro / com_sla.sum(), 4) if com_sla.sum() > 0 else 0

        # Satisfação: % de avaliações >= 4 (promotores) sobre total com avaliação
        avals    = grp['avaliacao'].dropna()
        promotor = (avals >= 4).sum()
        pct_sat  = round(promotor / len(avals), 4) if len(avals) > 0 else None

        rows.append({
            'Mês':          MESES_PT[mes],
            'Tipo':         'Suporte',
            'Indicador':    f'SLA de Suporte: Infraestrutura de TI/{area}',
            'Área':         area_dash,
            'Subárea':      subarea_dash,
            'Meta':         '',           # preenchido manualmente no Excel
            'Realizado':    pct_sla,
            'Acumulado':    '',           # calculado depois de ter todos os meses
            'Status':       '',           # J/L — calculado ao salvar
            'Total':        total,
            'Dentro_SLA':   int(dentro),
            'Fora_SLA':     int(fora),
            'Sem_SLA':      int(sem_sla),
            'Qtd_Aval':     int(len(avals)),
            'Pct_Satisfacao': pct_sat,
        })

        # Linha de satisfação (se tiver avaliações)
        if pct_sat is not None:
            rows.append({
                'Mês':          MESES_PT[mes],
                'Tipo':         'Satisfação',
                'Indicador':    f'Satisfação: Infraestrutura de TI/{area}',
                'Área':         area_dash,
                'Subárea':      subarea_dash,
                'Meta':         '',
                'Realizado':    pct_sat,
                'Acumulado':    '',
                'Status':       '',
                'Total':        int(len(avals)),
                'Dentro_SLA':   '',
                'Fora_SLA':     '',
                'Sem_SLA':      '',
                'Qtd_Aval':     int(len(avals)),
                'Pct_Satisfacao': pct_sat,
            })

    return pd.DataFrame(rows)


def calcular_acumulado(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula o Acumulado de cada indicador mês a mês (Jan → mês atual).
    """
    ordem = list(MESES_PT.values())
    df['_ordem'] = df['Mês'].map({m: i for i, m in enumerate(ordem)})
    df = df.sort_values('_ordem')

    grupos = ['Indicador', 'Tipo']
    df['Acumulado'] = 0.0

    for key, grp in df.groupby(grupos):
        grp_sorted = grp.sort_values('_ordem')
        soma_dentro = 0
        soma_total  = 0
        idxs = grp_sorted.index.tolist()
        for idx in idxs:
            row = df.loc[idx]
            if row['Tipo'] == 'Suporte':
                soma_dentro += row.get('Dentro_SLA', 0) or 0
                soma_total  += (row.get('Dentro_SLA', 0) or 0) + (row.get('Fora_SLA', 0) or 0)
                df.at[idx, 'Acumulado'] = round(soma_dentro / soma_total, 4) if soma_total else 0
            else:  # Satisfação
                # Acumulado de satisfação: média ponderada pelo número de avaliações
                qtd    = row.get('Qtd_Aval', 0) or 0
                val    = row.get('Realizado', 0) or 0
                soma_dentro += val * qtd
                soma_total  += qtd
                df.at[idx, 'Acumulado'] = round(soma_dentro / soma_total, 4) if soma_total else 0

    df = df.drop(columns=['_ordem'])
    return df


def salvar_excel(df: pd.DataFrame):
    """Salva o DataFrame em data/sla.xlsx."""
    os.makedirs(os.path.dirname(EXCEL_PATH), exist_ok=True)

    # Colunas para o dashboard (aba Report do sla.xlsx)
    colunas_dash = [
        'Mês', 'Tipo', 'Indicador', 'Área', 'Subárea',
        'Meta', 'Realizado', 'Acumulado', 'Status',
        'Total', 'Dentro_SLA', 'Fora_SLA', 'Sem_SLA',
        'Qtd_Aval', 'Pct_Satisfacao'
    ]
    df_dash = df[[c for c in colunas_dash if c in df.columns]]

    with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl') as writer:
        df_dash.to_excel(writer, sheet_name='Report', index=False)

    print(f"\n✅ Salvo em: {EXCEL_PATH}")
    print(f"   {len(df_dash)} linhas | {df_dash['Mês'].nunique()} meses")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sincroniza SLA do Jira para sla.xlsx')
    parser.add_argument('--mes',  type=int, help='Extrair só este mês (1-12)')
    parser.add_argument('--full', action='store_true', help='Reextrair todos os meses')
    args = parser.parse_args()

    mes_atual = datetime.now().month

    if args.mes:
        meses = [args.mes]
    elif args.full:
        meses = list(range(1, 13))
    else:
        # Padrão: extrair do mês 1 até o mês atual
        meses = list(range(1, mes_atual + 1))

    print(f"Sincronizando meses: {[MESES_PT[m] for m in meses]}")

    frames = []
    for mes in meses:
        df_mes = processar_mes(mes)
        if not df_mes.empty:
            frames.append(df_mes)

    if not frames:
        print("\n⚠️ Nenhum dado encontrado.")
        sys.exit(0)

    df_total = pd.concat(frames, ignore_index=True)
    df_total = calcular_acumulado(df_total)

    salvar_excel(df_total)

    print("\nResumo por área:")
    for (mes, area), grp in df_total[df_total['Tipo']=='Suporte'].groupby(['Mês','Área']):
        real = grp['Realizado'].mean()
        print(f"  {mes:10} | {area:20} | SLA: {real*100:.1f}%")
