"""
explorar_jira.py — Roda UMA VEZ para descobrir os campos de SLA
Execute: python explorar_jira.py
"""
import os, json, requests
from dotenv import load_dotenv

load_dotenv('api.env')

EMAIL = os.getenv('JIRA_EMAIL')
TOKEN = os.getenv('JIRA_TOKEN')
URL   = os.getenv('JIRA_URL')
AUTH  = (EMAIL, TOKEN)

def get(path, params=None):
    r = requests.get(f"{URL}/rest/api/3/{path}",
                     auth=AUTH, params=params,
                     headers={'Accept': 'application/json'})
    r.raise_for_status()
    return r.json()

def post(path, body):
    r = requests.post(f"{URL}/rest/api/3/{path}",
                      auth=AUTH, json=body,
                      headers={'Accept': 'application/json',
                               'Content-Type': 'application/json'})
    r.raise_for_status()
    return r.json()

print("=" * 60)
print("1. PROJETOS DISPONÍVEIS")
print("=" * 60)
projetos = get('project')
for p in projetos:
    print(f"  {p['key']:10} — {p['name']}")

print()
print("=" * 60)
print("2. CAMPOS CUSTOMIZADOS DO JIRA (filtrados por relevância)")
print("=" * 60)
todos_campos = get('field')
campos_relevantes = [c for c in todos_campos
                     if c.get('custom') and any(k in (c.get('name','').lower())
                     for k in ['sla','fila','queue','area','avalia','satisfa',
                               'atendimento','resolucao','resolução'])]
for c in campos_relevantes:
    print(f"  {c['id']:25} — {c['name']}")

if not campos_relevantes:
    print("  Nenhum campo relevante encontrado pelo nome.")
    print("  Listando TODOS os campos customizados:")
    for c in todos_campos:
        if c.get('custom'):
            print(f"  {c['id']:25} — {c['name']}")

print()
print("=" * 60)
print("3. BUSCANDO UM CHAMADO RESOLVIDO RECENTE")
print("=" * 60)

jql = 'project in ("INC","SOL") AND status in (Resolvido,Fechado) AND resolved >= "2026-01-01" AND resolved <= "2026-04-30" ORDER BY created DESC'
campos_buscar = [
    'summary','status','issuetype','assignee','created','resolutiondate',
    'customfield_10268',  # Fila de Atendimento
    'customfield_10075',  # Satisfaction
    'customfield_10190',  # Data da Resolução
    'customfield_10271',  # SLA Incidente Infra - Triagem
    'customfield_10272',  # SLA Incidente Infra - Resolução
    'customfield_10273',  # SLA Requisição Sistemas - Triagem
    'customfield_10274',  # SLA Requisição Sistemas - Resolução
    'customfield_10438',  # SLA Incidente Sistemas - Resolução
    'customfield_10508',  # SLA Incidente Sistemas - Triagem
    'customfield_10316',  # SLA Requisição Infra - Triagem
    'customfield_10317',  # SLA Requisição Infra - Resolução
]
r = requests.post(
    f"{URL}/rest/api/3/search/jql",
    auth=AUTH,
    headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
    json={'jql': jql, 'maxResults': 1, 'fields': campos_buscar}
)
r.raise_for_status()
issues = r.json()

if not issues['issues']:
    print("Nenhum chamado encontrado.")
else:
    issue = issues['issues'][0]
    print(f"Chamado: {issue['key']} — {issue['fields'].get('summary','')[:60]}")
    print()
    print("=" * 60)
    print("4. TODOS OS CAMPOS PREENCHIDOS NESSE CHAMADO")
    print("=" * 60)
    fields = issue['fields']
    for k, v in sorted(fields.items()):
        if v is None: continue
        if k.startswith('customfield_'):
            # Campos de SLA — mostrar estrutura completa
            if isinstance(v, list) and v and isinstance(v[0], dict):
                print(f"\n  {k} (lista):")
                for item in v:
                    nome = item.get('name','')
                    cycles = item.get('completedCycles',[])
                    ongoing = item.get('ongoingCycle',{})
                    print(f"    nome: {nome}")
                    if cycles:
                        for cyc in cycles:
                            print(f"    completedCycle: breached={cyc.get('breached')} "
                                  f"elapsed={cyc.get('elapsedTime',{}).get('friendly','?')} "
                                  f"goal={cyc.get('goalDuration',{}).get('friendly','?')}")
                    if ongoing:
                        print(f"    ongoingCycle: breached={ongoing.get('breached')} "
                              f"elapsed={ongoing.get('elapsedTime',{}).get('friendly','?')}")
            elif isinstance(v, (str, int, float)):
                print(f"  {k}: {str(v)[:80]}")
            elif isinstance(v, dict):
                val = v.get('value') or v.get('name') or v.get('displayName','')
                if val: print(f"  {k}: {val}")
                else: print(f"  {k}: {str(v)[:80]}")
        else:
            if isinstance(v, dict):
                val = v.get('name') or v.get('displayName','')
                if val: print(f"  {k}: {val}")
            elif isinstance(v, str) and v:
                print(f"  {k}: {v[:80]}")

print()
print("Script concluído. Cole o output aqui para eu montar o sync_jira.py.")

# ── TESTE EXTRA: buscar SLA via endpoint Service Management ──────────────────
print()
print("=" * 60)
print("5. TESTE: ENDPOINT SLA DO SERVICE MANAGEMENT")
print("=" * 60)

issue_key = "INC-63518"

# Tentar endpoint de SLA do JSM
try:
    r_sla = requests.get(
        f"{URL}/rest/servicedeskapi/request/{issue_key}/sla",
        auth=AUTH,
        headers={'Accept': 'application/json'}
    )
    print(f"Status: {r_sla.status_code}")
    if r_sla.ok:
        sla_data = r_sla.json()
        print(json.dumps(sla_data, indent=2, ensure_ascii=False)[:2000])
    else:
        print("Erro:", r_sla.text[:200])
except Exception as e:
    print("Erro:", e)

# Tentar pegar o issue com expand=names para ver campos completos
print()
print("=" * 60)
print("6. ISSUE COM EXPAND PARA VER SLA COMPLETO")
print("=" * 60)
try:
    r_issue = requests.get(
        f"{URL}/rest/api/3/issue/{issue_key}",
        auth=AUTH,
        headers={'Accept': 'application/json'},
        params={
            'fields': 'customfield_10272,customfield_10438,customfield_10317,customfield_10274,customfield_10268,customfield_10075',
            'expand': 'names'
        }
    )
    if r_issue.ok:
        data = r_issue.json()
        fields = data.get('fields', {})
        print(json.dumps(fields, indent=2, ensure_ascii=False)[:3000])
    else:
        print("Erro:", r_issue.text[:200])
except Exception as e:
    print("Erro:", e)
