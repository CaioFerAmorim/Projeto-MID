/* ══════════════════════════════════════════════════════════════
   MID TI Dashboard — app.js
   Carrega dados via /api/dados e renderiza as 3 páginas
══════════════════════════════════════════════════════════════ */

let DATA = null;

const state = {
  page: 'visao',
  visao: { modo: 'unico' },
  sla:   { modo: 'unico' },
  proj:  { modo: 'unico' },
};

/* ── Inicialização ──────────────────────────────────────────── */
async function init() {
  await loadData();
  setupNav();
  renderPage('visao');
}

async function loadData() {
  try {
    const res = await fetch('/api/dados');
    if (!res.ok) throw new Error(await res.text());
    DATA = await res.json();
    document.getElementById('last-update').textContent =
      'Atualizado: ' + new Date().toLocaleTimeString('pt-BR');
  } catch (e) {
    document.getElementById('main-content').innerHTML =
      `<div class="loading-state" style="color:#dc2626">
        ❌ Erro ao carregar dados<br>
        <small style="color:#8394a8">${e.message}</small>
      </div>`;
    throw e;
  }
}

/* ── Navegação ──────────────────────────────────────────────── */
function setupNav() {
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => renderPage(btn.dataset.page));
  });
  document.getElementById('btn-reload').addEventListener('click', async () => {
    document.getElementById('btn-reload').textContent = '⟳ Carregando…';
    await loadData();
    renderPage(state.page);
    document.getElementById('btn-reload').textContent = '⟳ Recarregar dados';
  });
}

const PAGE_TITLES = {
  visao:    'Painel de Metas – TI',
  sla:      'SLA por Área',
  projetos: 'Cronograma de Projetos',
};

function renderPage(page) {
  state.page = page;
  document.querySelectorAll('.nav-item').forEach(b => {
    b.classList.toggle('active', b.dataset.page === page);
  });
  document.getElementById('topbar-title').textContent = PAGE_TITLES[page];

  const main = document.getElementById('main-content');
  main.innerHTML = '<div class="page-content" id="page-root"></div>';
  const root = document.getElementById('page-root');

  if (page === 'visao')    renderVisao(root);
  if (page === 'sla')      renderSla(root);
  if (page === 'projetos') renderProjetos(root);
}

/* ═══════════════════════════════════════════════════════
   UTILITÁRIOS
═══════════════════════════════════════════════════════ */
const MESES      = () => DATA.ordem_meses;
const ABREV      = () => DATA.meses_abrev;
const MCOLS      = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];

function getVal(row, modo) {
  return modo === 'acum' ? row.acumulado : row.realizado;
}

function labelStatus(s) {
  if (s === 'J') return 'Em dia';
  if (s === 'L') return 'Atrasado';
  return s || 'Sem status';
}

function farolHtml(val, meta, infoOnly) {
  if (infoOnly) return '<span class="farol farol-x" title="Apenas informativo"></span>';
  if (meta === null || meta === undefined)
    return '<span class="farol farol-x" title="Meta não definida"></span>';
  return val >= meta
    ? '<span class="farol farol-g"></span>'
    : '<span class="farol farol-r"></span>';
}

function badgeStatus(sl) {
  const map = { 'Em dia': 'badge-ok', 'Atrasado': 'badge-bad' };
  return `<span class="badge ${map[sl] || 'badge-nd'}">${sl}</span>`;
}

function setPeriodoBadge(modo, mes) {
  document.getElementById('periodo-badge').textContent =
    modo === 'acum' ? `Jan – ${mes}` : mes;
}

/* ── Filtro bar builder ──────────────────────────────────────── */
function buildFilterBar(pgKey, extraHtml = '') {
  const modeState = state[pgKey].modo;
  const mesId     = `${pgKey}-mes`;
  const infoId    = `${pgKey}-info`;

  const html = `
    <div class="filter-bar">
      <div class="filter-group">
        <span class="filter-label">Modo</span>
        <div class="toggle-wrap">
          <button class="toggle-btn ${modeState === 'unico' ? 'active' : ''}"
            onclick="setModo('${pgKey}','unico',this)">Mês único</button>
          <button class="toggle-btn ${modeState === 'acum' ? 'active' : ''}"
            onclick="setModo('${pgKey}','acum',this)">Acumulado</button>
        </div>
      </div>
      <div class="filter-group">
        <span class="filter-label" id="${pgKey}-mes-label">
          ${modeState === 'acum' ? 'Até o mês' : 'Mês'}
        </span>
        <select class="filter-select" id="${mesId}" onchange="onMesChange('${pgKey}')">
          ${MESES().map(m => `<option value="${m}">${m}</option>`).join('')}
        </select>
      </div>
      ${extraHtml}
      <div class="filter-info" id="${infoId}">–</div>
    </div>`;

  return html;
}

function setModo(pgKey, modo, btn) {
  state[pgKey].modo = modo;
  btn.closest('.toggle-wrap').querySelectorAll('.toggle-btn')
    .forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const lbl = document.getElementById(`${pgKey}-mes-label`);
  if (lbl) lbl.textContent = modo === 'acum' ? 'Até o mês' : 'Mês';
  onMesChange(pgKey);
}

function onMesChange(pgKey) {
  if (pgKey === 'visao')    reRenderVisao();
  if (pgKey === 'sla')      reRenderSla();
  if (pgKey === 'projetos') reRenderProjetos();
}

function setLastMes(id) {
  const sel = document.getElementById(id);
  if (sel) sel.value = MESES()[MESES().length - 1];
}

function updateInfo(infoId, modo, mes) {
  const el = document.getElementById(infoId);
  if (!el) return;
  el.innerHTML = modo === 'acum'
    ? `📅 Jan → <strong>${mes}</strong> · usando <strong>Acumulado</strong>`
    : `📅 <strong>${mes}</strong> · usando <strong>Realizado</strong>`;
}

/* ═══════════════════════════════════════════════════════
   VISÃO GERAL
═══════════════════════════════════════════════════════ */
let chartEvolResizeObs = null;

function renderVisao(root) {
  root.innerHTML = buildFilterBar('visao');
  root.innerHTML += `
    <div id="vg-kpis" class="kpi-grid"></div>
    <div class="section-header">
      <span class="section-title">Indicadores SLA</span>
      <div class="section-line"></div>
    </div>
    <div class="card-table" id="vg-tabela"></div>
    <div class="section-header" style="margin-top:22px">
      <span class="section-title">Evolução Mensal</span>
      <div class="section-line"></div>
    </div>
    <div class="charts-row">
      <div class="chart-card">
        <div class="chart-title">Realizado por mês (%)</div>
        <svg id="chart-evol" style="width:100%;overflow:visible"></svg>
      </div>
      <div class="chart-card">
        <div class="chart-title">Status dos indicadores</div>
        <div class="donut-wrap">
          <div class="donut-center">
            <svg id="chart-donut" width="170" height="170"></svg>
            <div class="donut-label">
              <div class="donut-num" id="donut-num">–</div>
              <div class="donut-sub">Total</div>
            </div>
          </div>
          <div class="donut-legend" id="donut-legend"></div>
        </div>
      </div>
    </div>`;

  setLastMes('visao-mes');
  reRenderVisao();

  // Redimensionar chart quando janela mudar
  if (chartEvolResizeObs) chartEvolResizeObs.disconnect();
  const svg = document.getElementById('chart-evol');
  if (svg && window.ResizeObserver) {
    chartEvolResizeObs = new ResizeObserver(() => drawEvol(state.visao.modo));
    chartEvolResizeObs.observe(svg.parentElement);
  }
}

function reRenderVisao() {
  const modo   = state.visao.modo;
  const mes    = document.getElementById('visao-mes')?.value;
  if (!mes) return;
  const mesIdx = MESES().indexOf(mes);
  const col    = modo === 'acum' ? 'acumulado' : 'realizado';

  updateInfo('visao-info', modo, mes);
  setPeriodoBadge(modo, mes);

  // Coletar indicadores do mês com meta
  const sla = DATA.sla[mes] || {};
  const linhas = [];
  Object.values(sla).forEach(b => b.linhas.forEach(l => linhas.push(l)));
  const comMeta = linhas.filter(l => l.meta !== null);

  // Médias
  const avg = (arr, fn) => arr.length ? arr.reduce((a, b) => a + fn(b), 0) / arr.length : null;
  const sup = comMeta.filter(l => l.tipo === 'Suporte');
  const sat = comMeta.filter(l => l.tipo === 'Satisfação');
  const incReal = avg(sup, l => getVal(l, modo));
  const satReal = avg(sat, l => getVal(l, modo));
  const incMeta = avg(sup, l => l.meta) ?? 90;
  const satMeta = avg(sat, l => l.meta) ?? 90;

  // Tendência
  let dInc = 0, dSat = 0;
  if (mesIdx > 0) {
    const ant  = MESES()[mesIdx - 1];
    const sla2 = DATA.sla[ant] || {};
    const l2   = []; Object.values(sla2).forEach(b => b.linhas.forEach(l => l2.push(l)));
    const s2 = l2.filter(l => l.tipo === 'Suporte' && l.meta !== null);
    const t2 = l2.filter(l => l.tipo === 'Satisfação' && l.meta !== null);
    const pr = arr => avg(arr, l => l.realizado);
    if (incReal !== null && pr(s2) !== null) dInc = incReal - pr(s2);
    if (satReal !== null && pr(t2) !== null) dSat = satReal - pr(t2);
  }

  const atrasados = comMeta.filter(l => l.status === 'L').length;

  // KPIs
  const mkDelta = d => d !== 0
    ? `<span class="${d > 0 ? 'up' : 'dn'}">${d > 0 ? '↑' : '↓'} ${Math.abs(d).toFixed(1)} p.p.</span> vs mês ant.`
    : '';

  const kpis = [
    { label: 'Visão Geral TI',
      value: atrasados === 0 ? 'Saudável' : 'Em Alerta',
      sub:   atrasados === 0 ? 'Todos os indicadores em dia' : `${atrasados} indicador(es) com status L`,
      cls:   atrasados === 0 ? 'green' : 'red', delta: '' },
    { label: 'SLA Incidentes',
      value: incReal !== null ? `${incReal.toFixed(1)}%` : '–',
      sub:   `Meta: ≥ ${incMeta.toFixed(0)}%`,
      cls:   incReal !== null && incReal >= incMeta ? 'green' : 'red',
      delta: mkDelta(dInc) },
    { label: 'SLA Satisfação',
      value: satReal !== null ? `${satReal.toFixed(1)}%` : '–',
      sub:   `Meta: ≥ ${satMeta.toFixed(0)}%`,
      cls:   satReal !== null && satReal >= satMeta ? 'green' : 'red',
      delta: mkDelta(dSat) },
    { label: 'Indicadores em Risco',
      value: String(atrasados),
      sub:   atrasados === 0 ? 'Todos dentro da meta ✅' : `${atrasados} abaixo da meta`,
      cls:   atrasados === 0 ? 'green' : 'red', delta: '' },
  ];

  document.getElementById('vg-kpis').innerHTML = kpis.map((k, i) => `
    <div class="kpi-card ${k.cls}" style="animation-delay:${i * 0.07}s">
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-value">${k.value}</div>
      <div class="kpi-delta">${k.delta}</div>
      <div class="kpi-sub">${k.sub}</div>
    </div>`).join('');

  // Tabela
  const rows = comMeta.map(l => {
    const val = getVal(l, modo);
    const ok  = val >= l.meta;
    const vc  = ok ? 'v-ok' : 'v-bad';
    const tipo = l.tipo === 'Suporte'
      ? '<span class="badge badge-sup">Suporte</span>'
      : '<span class="badge badge-sat">Satisfação</span>';
    const sl = labelStatus(l.status);
    return `<tr>
      <td>${l.nome}</td>
      <td>${tipo}</td>
      <td class="${vc}">${val.toFixed(1)}%</td>
      <td class="v-meta">≥ ${l.meta.toFixed(0)}%</td>
      <td>${farolHtml(val, l.meta, l.info_only)}</td>
      <td>${badgeStatus(sl)}</td>
    </tr>`;
  }).join('');

  document.getElementById('vg-tabela').innerHTML = `
    <table class="data-table">
      <thead><tr>
        <th>Indicador</th><th>Tipo</th>
        <th>${col === 'acumulado' ? 'Acumulado' : 'Realizado'}</th>
        <th>Meta</th><th>Farol</th><th>Status</th>
      </tr></thead>
      <tbody>${rows || '<tr><td colspan="6" style="text-align:center;color:#a0aec0;padding:24px">Sem dados com meta preenchida para este mês</td></tr>'}</tbody>
    </table>`;

  drawEvol(modo);

  // Donut
  const acima  = comMeta.filter(l => getVal(l, modo) >= l.meta).length;
  const abaixo = comMeta.length - acima;
  drawDonut(acima, abaixo, comMeta.length);
}

/* ── Gráfico evolução ────────────────────────────────────────── */
function drawEvol(modo) {
  const svg = document.getElementById('chart-evol');
  if (!svg) return;
  const W  = svg.parentElement.clientWidth - 40 || 500;
  const H  = 200;
  const col = modo === 'acum' ? 'acumulado' : 'realizado';

  const pts_inc = [], pts_sat = [];
  MESES().forEach(m => {
    const sla = DATA.sla[m] || {};
    const all = []; Object.values(sla).forEach(b => b.linhas.forEach(l => all.push(l)));
    const sup = all.filter(l => l.tipo === 'Suporte'    && l.meta !== null);
    const sat = all.filter(l => l.tipo === 'Satisfação' && l.meta !== null);
    const avg = (arr, fn) => arr.length ? arr.reduce((a, b) => a + fn(b), 0) / arr.length : null;
    pts_inc.push(avg(sup, l => l[col]));
    pts_sat.push(avg(sat, l => l[col]));
  });

  const pad = { l: 36, r: 24, t: 10, b: 36 };
  const xW = W - pad.l - pad.r;
  const yH = H - pad.t - pad.b;
  const allVals = [...pts_inc, ...pts_sat].filter(v => v !== null);
  const minY = allVals.length ? Math.max(0,  Math.min(...allVals) - 5) : 0;
  const maxY = allVals.length ? Math.min(105, Math.max(...allVals) + 5) : 105;
  const xStep  = xW / (MESES().length - 1);
  const yScale = v => (yH - (v - minY) / (maxY - minY) * yH) + pad.t;
  const xPos   = i => pad.l + i * xStep;

  let html = '';

  // Gridlines
  [0, 25, 50, 75, 100].filter(v => v >= minY && v <= maxY).forEach(v => {
    const y = yScale(v);
    html += `<line x1="${pad.l}" y1="${y}" x2="${W - pad.r}" y2="${y}"
      stroke="#f0f3f8" stroke-width="1"/>`;
    html += `<text x="${pad.l - 5}" y="${y + 4}" text-anchor="end"
      font-size="10" fill="#b0beca">${v}</text>`;
  });

  // Linha de meta 90%
  if (90 >= minY && 90 <= maxY) {
    const y90 = yScale(90);
    html += `<line x1="${pad.l}" y1="${y90}" x2="${W - pad.r}" y2="${y90}"
      stroke="#dc2626" stroke-width="1" stroke-dasharray="5,4"/>`;
    html += `<text x="${W - pad.r + 4}" y="${y90 + 4}"
      font-size="9" fill="#dc2626">90%</text>`;
  }

  // Eixo X
  ABREV().forEach((ab, i) => {
    html += `<text x="${xPos(i)}" y="${H - 4}" text-anchor="middle"
      font-size="10" fill="#b0beca">${ab}</text>`;
  });

  // Linhas e pontos
  const drawSeries = (pts, color) => {
    let d = '', first = true;
    pts.forEach((v, i) => {
      if (v === null) { first = true; return; }
      const x = xPos(i), y = yScale(v);
      d += first ? `M${x},${y}` : `L${x},${y}`; first = false;
    });
    if (!d) return '';
    let out = `<path d="${d}" fill="none" stroke="${color}" stroke-width="2.5"
      stroke-linecap="round" stroke-linejoin="round"/>`;
    pts.forEach((v, i) => {
      if (v === null) return;
      out += `<circle cx="${xPos(i)}" cy="${yScale(v)}" r="3.5"
        fill="${color}" stroke="#fff" stroke-width="2"/>`;
    });
    return out;
  };

  html += drawSeries(pts_inc, '#1a3a6b');
  html += drawSeries(pts_sat, '#16a34a');

  // Legenda inline
  html += `
    <circle cx="${pad.l + 6}" cy="${H + 20}" r="5" fill="#1a3a6b"/>
    <text x="${pad.l + 14}" y="${H + 24}" font-size="10" fill="#6b7d94">Incidentes</text>
    <circle cx="${pad.l + 90}" cy="${H + 20}" r="5" fill="#16a34a"/>
    <text x="${pad.l + 98}" y="${H + 24}" font-size="10" fill="#6b7d94">Satisfação</text>`;

  svg.setAttribute('viewBox', `0 0 ${W} ${H + 28}`);
  svg.setAttribute('height', H + 28);
  svg.innerHTML = html;
}

/* ── Donut ───────────────────────────────────────────────────── */
function drawDonut(acima, abaixo, total) {
  const svg = document.getElementById('chart-donut');
  if (!svg) return;
  document.getElementById('donut-num').textContent = total;

  if (total === 0) { svg.innerHTML = ''; return; }

  const cx = 85, cy = 85, ro = 68, ri = 48;

  function arc(cx, cy, r, start, end, large) {
    const s = { x: cx + r * Math.cos(start), y: cy + r * Math.sin(start) };
    const e = { x: cx + r * Math.cos(end),   y: cy + r * Math.sin(end) };
    return `M${s.x},${s.y} A${r},${r},0,${large},1,${e.x},${e.y}`;
  }

  const total2 = (acima + abaixo) || 1;
  const ang1   = (acima / total2) * 2 * Math.PI;
  const st     = -Math.PI / 2;
  const mid    = st + ang1;
  const en     = st + 2 * Math.PI - 0.001;

  let html = '';
  if (acima > 0) {
    const lg = ang1 > Math.PI ? 1 : 0;
    html += `<path d="${arc(cx,cy,ro,st,mid,lg)} L${cx+ri*Math.cos(mid)},${cy+ri*Math.sin(mid)}
      ${arc(cx,cy,ri,mid,st,lg).replace('M','L')} Z"
      fill="#22c55e" opacity=".9"/>`;
  }
  if (abaixo > 0) {
    const lg = (2 * Math.PI - ang1) > Math.PI ? 1 : 0;
    html += `<path d="${arc(cx,cy,ro,mid,en,lg)} L${cx+ri*Math.cos(en)},${cy+ri*Math.sin(en)}
      ${arc(cx,cy,ri,en,mid,lg).replace('M','L')} Z"
      fill="#ef4444" opacity=".9"/>`;
  }
  svg.innerHTML = html;

  document.getElementById('donut-legend').innerHTML = `
    <div class="legend-item">
      <span class="legend-dot" style="background:#22c55e"></span>
      Acima da meta <strong>${acima}</strong>
    </div>
    <div class="legend-item">
      <span class="legend-dot" style="background:#ef4444"></span>
      Abaixo <strong>${abaixo}</strong>
    </div>`;
}

/* ═══════════════════════════════════════════════════════
   SLA POR ÁREA
═══════════════════════════════════════════════════════ */
function renderSla(root) {
  root.innerHTML = buildFilterBar('sla') + `<div class="sla-grid" id="sla-grid"></div>`;
  setLastMes('sla-mes');
  reRenderSla();
}

function reRenderSla() {
  const modo = state.sla.modo;
  const mes  = document.getElementById('sla-mes')?.value;
  if (!mes) return;

  updateInfo('sla-info', modo, mes);
  setPeriodoBadge(modo, mes);

  const sla = DATA.sla[mes] || {};
  const col = modo === 'acum' ? 'acumulado' : 'realizado';

  // Agrupar por área
  const byArea = {};
  Object.entries(sla).forEach(([sub, bloco]) => {
    (byArea[bloco.area] || (byArea[bloco.area] = [])).push({ sub, linhas: bloco.linhas });
  });

  function buildArea(area) {
    const subs = byArea[area] || [];
    if (!subs.length) return '';
    const subsHtml = subs.map(({ sub, linhas }) => {
      const rows = linhas.map(l => {
        const val = l[col];
        const ok  = l.meta !== null && val >= l.meta;
        const vc  = l.meta === null ? 'v-nd' : ok ? 'v-ok' : 'v-bad';
        return `<tr>
          <td>${l.nome}</td>
          <td class="v-meta">${l.meta !== null ? l.meta.toFixed(0) + '%' : '–'}</td>
          <td class="${vc}">${l.meta !== null ? val.toFixed(1) + '%' : '–'}</td>
          <td>${farolHtml(val, l.meta, l.info_only)}</td>
        </tr>`;
      }).join('');
      return `<div class="subarea-block">
        <div class="subarea-title">${sub}</div>
        <table class="sla-table">
          <thead><tr>
            <th>Indicador</th><th>Meta</th><th>Resultado</th><th>Status</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
    }).join('');
    return `<div class="area-block">
      <div class="area-title">${area}</div>
      ${subsHtml}
    </div>`;
  }

  const esq = ['Infraestrutura', 'Cybersegurança'].map(buildArea).join('');
  const dir = ['Sistemas', 'Outros'].map(buildArea).join('');
  document.getElementById('sla-grid').innerHTML =
    `<div class="sla-col">${esq}</div><div class="sla-col">${dir}</div>`;
}

/* ═══════════════════════════════════════════════════════
   PROJETOS
═══════════════════════════════════════════════════════ */
function renderProjetos(root) {
  // Popular responsáveis
  const resps = [...new Set(DATA.projetos.map(p => p.responsavel).filter(Boolean))].sort();
  const respOpts = `<option value="">Todos</option>` +
    resps.map(r => `<option value="${r}">${r}</option>`).join('');

  const extra = `
    <div class="filter-group">
      <span class="filter-label">Responsável</span>
      <select class="filter-select" id="proj-resp" onchange="reRenderProjetos()">
        ${respOpts}
      </select>
    </div>`;

  root.innerHTML = buildFilterBar('proj', extra) + `
    <div class="kpi-grid" id="proj-kpis"></div>
    <div class="section-header">
      <span class="section-title">Cronograma Anual</span>
      <div class="section-line"></div>
    </div>
    <div class="proj-wrapper" id="proj-tabela"></div>`;

  setLastMes('proj-mes');
  reRenderProjetos();
}

function reRenderProjetos() {
  const modo    = state.proj.modo;
  const mes     = document.getElementById('proj-mes')?.value;
  const resp    = document.getElementById('proj-resp')?.value || '';
  if (!mes) return;

  const mesIdx  = MESES().indexOf(mes);
  const colIdx  = mesIdx; // 0=jan … 11=dez
  const colKey  = modo === 'acum' ? 'Acumulado' : 'Realizado';

  updateInfo('proj-info', modo, mes);
  setPeriodoBadge(modo, mes);

  let projs = DATA.projetos;
  if (resp) projs = projs.filter(p => p.responsavel === resp);

  // KPIs
  const n      = projs.length;
  const emdia  = projs.filter(p => labelStatus(p.status) === 'Em dia').length;
  const atras  = projs.filter(p => labelStatus(p.status) === 'Atrasado').length;
  const sem    = n - emdia - atras;

  document.getElementById('proj-kpis').innerHTML = [
    { label: 'Total de Projetos', value: n,     cls: 'blue'  },
    { label: 'Em Dia',            value: emdia, cls: 'green' },
    { label: 'Atrasados',         value: atras, cls: atras > 0 ? 'red' : '' },
    { label: 'Sem Status',        value: sem,   cls: ''      },
  ].map((k, i) => `
    <div class="kpi-card ${k.cls}" style="animation-delay:${i * 0.07}s">
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-value">${k.value}</div>
    </div>`).join('');

  // Tabela
  const thMeses = ABREV().map((ab, i) =>
    `<th ${i === colIdx ? 'class="mes-ativo"' : ''}>${ab}</th>`
  ).join('');

  let tbody = '';
  projs.forEach(p => {
    const sl = labelStatus(p.status);
    const dc = sl === 'Em dia' ? '#22c55e' : sl === 'Atrasado' ? '#ef4444' : '#94a3b8';
    const bgSl = sl === 'Em dia' ? '#dcfce7' : sl === 'Atrasado' ? '#fee2e2' : '#f1f5f9';
    const fgSl = sl === 'Em dia' ? '#166534' : sl === 'Atrasado' ? '#991b1b' : '#475569';
    const slHtml = `<span style="display:inline-flex;align-items:center;gap:5px">
      <span style="width:9px;height:9px;border-radius:50%;background:${dc};flex-shrink:0"></span>
      <span style="font-size:0.72rem;background:${bgSl};color:${fgSl};
        padding:1px 7px;border-radius:10px">${sl}</span></span>`;

    const marc   = (p.marcos || '').replace(/\n/g, ' ').trim();
    const mShort = marc.length > 55 ? marc.slice(0, 55) + '…' : (marc || '–');
    const rShort = (p.responsavel || '').length > 18
      ? p.responsavel.slice(0, 18) + '…' : (p.responsavel || '–');

    // Linha de grupo
    tbody += `<tr class="proj-group-row">
      <td colspan="${5 + 12}">📌 ${p.indicador}
        <span style="font-weight:400;color:#8394a8;font-size:0.71rem"> — ${p.responsavel}</span>
      </td></tr>`;

    ['Meta', 'Realizado', 'Acumulado'].forEach((metr, mi) => {
      const vals = p.meses[metr] || Array(12).fill(0);
      const cels = vals.map((v, i) => {
        const dest = i === colIdx ? 'mes-ativo' : '';
        return v > 0
          ? `<td class="${dest} has-val">${v.toFixed(0)}%</td>`
          : `<td class="${dest} empty">·</td>`;
      }).join('');
      const rowCls = metr === 'Meta' ? 'meta-row' : metr === 'Realizado' ? 'real-row' : 'acum-row';

      if (mi === 0) {
        tbody += `<tr class="${rowCls}">
          <td class="left" rowspan="3" style="max-width:200px;font-size:0.78rem">${p.indicador}</td>
          <td rowspan="3" style="max-width:110px">
            <span title="${marc}" style="cursor:help;font-size:0.73rem;color:#374151">${mShort}</span>
          </td>
          <td rowspan="3" style="text-align:center">${slHtml}</td>
          <td rowspan="3" style="font-size:0.73rem">
            <span title="${p.responsavel}">${rShort}</span>
          </td>
          <td class="linha-label left">${metr}</td>${cels}</tr>`;
      } else {
        tbody += `<tr class="${rowCls}">
          <td class="linha-label left">${metr}</td>${cels}</tr>`;
      }
    });
  });

  document.getElementById('proj-tabela').innerHTML = `
    <table class="proj-table">
      <thead><tr>
        <th class="left">Indicador</th>
        <th>Marcos</th><th>Status</th><th>Resp.</th><th>Linha</th>
        ${thMeses}
      </tr></thead>
      <tbody>${tbody}</tbody>
    </table>`;
}

/* ── Start ── */
window.addEventListener('DOMContentLoaded', init);
