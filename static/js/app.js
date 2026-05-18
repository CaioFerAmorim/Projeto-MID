/* ══════════════════════════════════════════════════════════════
   MID TI Dashboard — app.js
══════════════════════════════════════════════════════════════ */

let DATA = null;

const state = {
  page:  'visao',
  visao: { modo: 'unico' },
  sla:   { modo: 'unico' },
  proj:  { modo: 'unico' },
};

/* ── Init ────────────────────────────────────────────────────── */
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

/* ── Navegação ───────────────────────────────────────────────── */
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
  visao:    'Painel de Metas',
  sla:      'SLA por Área',
  projetos: 'Cronograma de Projetos',
};

function renderPage(page) {
  state.page = page;
  document.querySelectorAll('.nav-item').forEach(b =>
    b.classList.toggle('active', b.dataset.page === page));
  document.getElementById('topbar-title').textContent = PAGE_TITLES[page];
  const main = document.getElementById('main-content');
  main.innerHTML = '<div class="page-content" id="page-root"></div>';
  const root = document.getElementById('page-root');
  if (page === 'visao')    renderVisao(root);
  if (page === 'sla')      renderSla(root);
  if (page === 'projetos') renderProjetos(root);
}

/* ═══════════════════════════════════════════════════════
   UTILITÁRIOS GERAIS
═══════════════════════════════════════════════════════ */
const MESES  = () => DATA.ordem_meses;
const ABREV  = () => DATA.meses_abrev;

function getVal(row, modo) {
  return modo === 'acum' ? row.acumulado : row.realizado;
}
function labelStatus(s) {
  if (s === 'J') return 'Na meta';
  if (s === 'L') return 'Fora da meta';
  return s || 'Sem status';
}
function farolHtml(val, meta, infoOnly) {
  if (infoOnly)
    return '<span class="farol farol-x" title="Apenas informativo"></span>';
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
  const el = document.getElementById('periodo-badge');
  if (el) el.textContent = modo === 'acum' ? `Jan – ${mes}` : mes;
}
function updateInfo(infoId, modo, mes) {
  const el = document.getElementById(infoId);
  if (!el) return;
  el.innerHTML = modo === 'acum'
    ? `📅 Jan → <strong>${mes}</strong> · usando <strong>Acumulado</strong>`
    : `📅 <strong>${mes}</strong> · usando <strong>Realizado</strong>`;
}

/* ── Filtro bar builder ─────────────────────────────────────── */
function buildFilterBar(pgKey, extraHtml = '') {
  const modo  = state[pgKey].modo;
  const mesId = `${pgKey}-mes`;
  return `
    <div class="filter-bar">
      <div class="filter-group">
        <span class="filter-label">Modo</span>
        <div class="toggle-wrap">
          <button class="toggle-btn ${modo === 'unico' ? 'active' : ''}"
            onclick="setModo('${pgKey}','unico',this)">Mês único</button>
          <button class="toggle-btn ${modo === 'acum' ? 'active' : ''}"
            onclick="setModo('${pgKey}','acum',this)">Acumulado</button>
        </div>
      </div>
      <div class="filter-group">
        <span class="filter-label" id="${pgKey}-mes-label">
          ${modo === 'acum' ? 'Até o mês' : 'Mês'}
        </span>
        <select class="filter-select" id="${mesId}" onchange="onMesChange('${pgKey}')">
          ${MESES().map(m => `<option value="${m}">${m}</option>`).join('')}
        </select>
      </div>
      ${extraHtml}
      <div class="filter-info" id="${pgKey}-info">–</div>
    </div>`;
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

function initChoices(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  return new Choices(el, {
    searchEnabled: false,
    itemSelectText: '',
    shouldSort: false,
    allowHTML: false,
  });
}

/* ═══════════════════════════════════════════════════════
   VISÃO GERAL
═══════════════════════════════════════════════════════ */
let evolResizeObs = null;

// Mapeamento área → subáreas (deve bater com MAPA_AREAS do server.py)
const AREA_MAP = {
  'Infraestrutura': ['DATA CENTER','REDES','SERVIÇOS (EST. TRABALHO)'],
  'Sistemas':       ['COMERCIAL & INOVAÇÃO','SUPRIMENTOS & APOIO','FINANÇAS & PLANEJAMENTO','OPERAÇÕES & ENGENHARIA'],
  'BI':             ['BI'],
  'Cybersegurança': ['GERAL'],
};

// Agrupa linhas SLA de um mês por área definida acima
function linhasPorArea(sla, area) {
  const subs = AREA_MAP[area] || [];
  const result = [];
  Object.entries(sla).forEach(([sub, bloco]) => {
    if (subs.includes(sub)) bloco.linhas.forEach(l => result.push(l));
  });
  return result;
}

function renderVisao(root) {
  root.innerHTML = `
    <div id="vg-kpis" class="kpi-grid-vg"></div>
    <div class="section-header" style="margin-top:22px">
      <span class="section-title">Evolução Anual — Realizado</span>
      <div class="section-line"></div>
    </div>
    <div class="charts-row">
      <div class="chart-card">
        <div class="chart-title">Trajetória por área (%)</div>
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

  reRenderVisao();

  if (evolResizeObs) evolResizeObs.disconnect();
  const svg = document.getElementById('chart-evol');
  if (svg && window.ResizeObserver) {
    evolResizeObs = new ResizeObserver(() => drawEvolVisao());
    evolResizeObs.observe(svg.parentElement);
  }
}

function reRenderVisao() {
  const avg = (arr, fn) => arr.length ? arr.reduce((a,b) => a + fn(b), 0) / arr.length : null;

  // Descobrir último mês com dados de SLA
  let ultimoMes = null, ultimoIdx = -1;
  MESES().forEach((m, i) => {
    const sla = DATA.sla[m] || {};
    const linhas = Object.values(sla).flatMap(b => b.linhas);
    const temDados = linhas.some(l => l.realizado > 0 && l.meta !== null);
    if (temDados) { ultimoMes = m; ultimoIdx = i; }
  });

  if (!ultimoMes) {
    document.getElementById('vg-kpis').innerHTML =
      `<div style="grid-column:1/-1;text-align:center;color:#a0aec0;padding:40px">Sem dados disponíveis</div>`;
    return;
  }

  const sla    = DATA.sla[ultimoMes] || {};
  const slaAnt = ultimoIdx > 0 ? (DATA.sla[MESES()[ultimoIdx-1]] || {}) : {};

  // Calcular métricas para uma área no último mês com dados
  function calcArea(area) {
    const linhas    = linhasPorArea(sla, area);
    const linhasAnt = linhasPorArea(slaAnt, area);
    const comMeta   = linhas.filter(l => l.meta !== null);
    const sup       = comMeta.filter(l => l.tipo === 'Suporte');
    const sat       = comMeta.filter(l => l.tipo === 'Satisfação');
    const incReal   = avg(sup, l => l.realizado);
    const satReal   = avg(sat, l => l.realizado);
    const incMeta   = avg(sup, l => l.meta);
    const satMeta   = avg(sat, l => l.meta);
    // Tendência vs mês anterior
    const supAnt = linhasPorArea(slaAnt, area).filter(l => l.tipo === 'Suporte'    && l.meta !== null);
    const satAnt = linhasPorArea(slaAnt, area).filter(l => l.tipo === 'Satisfação' && l.meta !== null);
    const dInc   = incReal !== null && supAnt.length ? incReal - avg(supAnt, l => l.realizado) : 0;
    const dSat   = satReal !== null && satAnt.length ? satReal - avg(satAnt, l => l.realizado) : 0;
    const risco  = comMeta.filter(l => l.status === 'L').length;
    return { incReal, satReal, incMeta, satMeta, dInc, dSat, risco, comMeta };
  }

  // Sparkline de todos os meses até o último com dados
  function getSparkPts(area, tipo) {
    return MESES().slice(0, ultimoIdx + 1).map(m => {
      const ls = linhasPorArea(DATA.sla[m]||{}, area)
        .filter(l => l.tipo === tipo && l.meta !== null);
      const v = ls.length ? avg(ls, l => l.realizado) : null;
      return (v !== null && v > 0) ? v : null;
    });
  }

  function sparkline(pontos, color) {
    const valid = pontos.filter(v => v !== null);
    if (valid.length < 2) return '';
    const W=80, H=30, pad=3;
    const min = Math.min(...valid), max = Math.max(...valid);
    const range = max - min || 1;
    const xStep = (W - pad*2) / (pontos.length - 1);
    let d = '', first = true;
    pontos.forEach((v, i) => {
      if (v === null) { first=true; return; }
      const x = pad + i * xStep;
      const y = H - pad - ((v - min) / range) * (H - pad*2);
      d += first ? `M${x},${y}` : `L${x},${y}`; first=false;
    });
    return `<svg width="${W}" height="${H}" style="display:block">
      <path d="${d}" fill="none" stroke="${color}" stroke-width="1.8"
        stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`;
  }

  function cardArea(area, label, icon) {
    const c = calcArea(area);
    const saudavel = c.risco === 0;

    const fmtVal = (v) => {
      if (v === null) return '<span style="color:#c0cad8;font-size:0.95rem">–</span>';
      return `<span style="font-size:1.6rem;font-weight:700;font-variant-numeric:tabular-nums;
        color:${v > 0 ? '#1c2b45' : '#a0aec0'}">${v.toFixed(1)}%</span>`;
    };

    const fmtDelta = (d) => {
      if (d === 0) return '';
      const cor = d > 0 ? '#16a34a' : '#dc2626';
      return `<span style="font-size:0.72rem;color:${cor};font-weight:600">
        ${d > 0 ? '↑' : '↓'} ${Math.abs(d).toFixed(1)} p.p.</span>`;
    };

    const statusDot = saudavel
      ? `<span style="background:#dcfce7;color:#166534;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:600">✓ Na meta</span>`
      : `<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:10px;font-size:0.68rem;font-weight:600">⚠ ${c.risco} fora</span>`;

    const spkInc = getSparkPts(area, 'Suporte');
    const spkSat = getSparkPts(area, 'Satisfação');
    const corInc = c.incReal !== null && c.incMeta !== null && c.incReal >= c.incMeta ? '#16a34a' : '#ef4444';
    const corSat = c.satReal !== null && c.satMeta !== null ? (c.satReal >= c.satMeta ? '#16a34a' : '#ef4444') : '#94a3b8';

    return `
      <div class="kpi-card-vg">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
          <div style="font-size:0.65rem;font-weight:700;color:#8394a8;text-transform:uppercase;letter-spacing:.7px">${icon} ${label}</div>
          ${statusDot}
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
          <div style="border-right:1px solid #f0f3f8;padding-right:12px">
            <div style="font-size:0.62rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px">Incidentes</div>
            <div style="display:flex;align-items:flex-end;justify-content:space-between">
              <div>${fmtVal(c.incReal)}<div style="margin-top:2px">${fmtDelta(c.dInc)}</div></div>
              <div style="opacity:.75">${sparkline(spkInc, corInc)}</div>
            </div>
          </div>
          <div>
            <div style="font-size:0.62rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px">Satisfação</div>
            <div style="display:flex;align-items:flex-end;justify-content:space-between">
              <div>${fmtVal(c.satReal)}<div style="margin-top:2px">${fmtDelta(c.dSat)}</div></div>
              <div style="opacity:.75">${sparkline(spkSat, corSat)}</div>
            </div>
          </div>
        </div>
        <div style="margin-top:10px;font-size:0.68rem;color:#b0beca">
          Referência: ${ultimoMes}
        </div>
      </div>`;
  }

  // Card Áreas em Risco
  const todasLinhas = Object.values(sla).flatMap(b => b.linhas).filter(l => l.meta !== null);
  const totalRisco  = todasLinhas.filter(l => l.status === 'L').length;
  const cardRisco   = `
    <div class="kpi-card-vg kpi-card-risco ${totalRisco === 0 ? 'risco-ok' : 'risco-alerta'}">
      <div style="font-size:0.65rem;font-weight:700;color:#8394a8;text-transform:uppercase;letter-spacing:.7px;margin-bottom:10px">⚠ Áreas em Risco</div>
      <div style="font-size:3rem;font-weight:700;line-height:1;margin-bottom:8px;
        color:${totalRisco===0?'#16a34a':'#dc2626'}">${totalRisco}</div>
      <div style="font-size:0.78rem;color:${totalRisco===0?'#16a34a':'#dc2626'}">
        ${totalRisco === 0 ? '✅ Todas dentro da meta' : `${totalRisco} indicador(es) fora`}
      </div>
      <div style="margin-top:8px;font-size:0.68rem;color:#b0beca">Ref: ${ultimoMes}</div>
    </div>`;

  document.getElementById('vg-kpis').innerHTML =
    cardArea('Infraestrutura', 'Infraestrutura', '🖥') +
    cardArea('Sistemas',       'Sistemas',        '⚙') +
    cardArea('BI',             'BI',              '📊') +
    cardRisco;

  drawEvolVisao();

  const acima  = todasLinhas.filter(l => l.realizado >= l.meta).length;
  const abaixo = todasLinhas.length - acima;
  drawDonut(acima, abaixo, todasLinhas.length);
}

/* ── Gráfico de evolução da Visão Geral (uma linha por área) ── */
function drawEvolVisao() {
  const svg = document.getElementById('chart-evol');
  if (!svg) return;
  const W = svg.parentElement.clientWidth - 40 || 500;
  const H = 220;
  const avg = (arr, fn) => arr.length ? arr.reduce((a,b) => a+fn(b), 0)/arr.length : null;

  const AREAS_GRAF = [
    { key: 'Infraestrutura', label: 'Infra',    color: '#1a3a6b' },
    { key: 'Sistemas',       label: 'Sistemas', color: '#16a34a' },
    { key: 'BI',             label: 'BI',       color: '#d97706' },
  ];

  // Para cada área, média do realizado de Suporte por mês
  const series = AREAS_GRAF.map(a => ({
    ...a,
    pts: MESES().map(m => {
      const ls = linhasPorArea(DATA.sla[m]||{}, a.key)
        .filter(l => l.tipo === 'Suporte' && l.meta !== null);
      const v = ls.length ? avg(ls, l => l.realizado) : null;
      return (v !== null && v > 0) ? v * 100 : null;
    })
  }));

  const pad = { l:36, r:24, t:10, b:44 };
  const xW = W - pad.l - pad.r;
  const yH = H - pad.t - pad.b;
  const allV = series.flatMap(s => s.pts).filter(v => v !== null);
  const minY = allV.length ? Math.max(0,  Math.min(...allV) - 5) : 0;
  const maxY = allV.length ? Math.min(105, Math.max(...allV) + 5) : 105;
  const xPos   = i => pad.l + i * (xW / (MESES().length - 1));
  const yScale = v => (yH - (v - minY) / (maxY - minY) * yH) + pad.t;

  let html = '';

  // Grid
  [0, 25, 50, 75, 100].filter(v => v >= minY && v <= maxY).forEach(v => {
    const y = yScale(v);
    html += `<line x1="${pad.l}" y1="${y}" x2="${W-pad.r}" y2="${y}" stroke="#f0f3f8" stroke-width="1"/>`;
    html += `<text x="${pad.l-5}" y="${y+4}" text-anchor="end" font-size="10" fill="#b0beca">${v}</text>`;
  });

  // Eixo X
  ABREV().forEach((ab, i) => {
    html += `<text x="${xPos(i)}" y="${H-pad.b+14}" text-anchor="middle" font-size="10" fill="#b0beca">${ab}</text>`;
  });

  // Linhas por área
  series.forEach(s => {
    let d = '', first = true;
    s.pts.forEach((v, i) => {
      if (v === null) { first=true; return; }
      d += first ? `M${xPos(i)},${yScale(v)}` : `L${xPos(i)},${yScale(v)}`; first=false;
    });
    if (!d) return;
    html += `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2.5"
      stroke-linecap="round" stroke-linejoin="round"/>`;
    s.pts.forEach((v, i) => {
      if (v === null) return;
      html += `<circle cx="${xPos(i)}" cy="${yScale(v)}" r="3.5"
        fill="${s.color}" stroke="#fff" stroke-width="2"/>`;
    });
  });

  // Legenda
  let lx = pad.l;
  series.forEach(s => {
    html += `<circle cx="${lx+5}" cy="${H-8}" r="5" fill="${s.color}"/>`;
    html += `<text x="${lx+14}" y="${H-4}" font-size="10" fill="#6b7d94">${s.label}</text>`;
    lx += 70;
  });

  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('height', H);
  svg.innerHTML = html;
}

function drawEvol(modo) {
  const svg = document.getElementById('chart-evol');
  if (!svg) return;
  const W   = svg.parentElement.clientWidth - 40 || 500;
  const H   = 200;
  const col = modo === 'acum' ? 'acumulado' : 'realizado';

  const pts_inc = [], pts_sat = [];
  MESES().forEach(m => {
    const sla = DATA.sla[m] || {};
    const all = [];
    Object.values(sla).forEach(b => b.linhas.forEach(l => all.push(l)));
    const avg = (arr, fn) => arr.length ? arr.reduce((a,b) => a+fn(b), 0)/arr.length : null;
    pts_inc.push(avg(all.filter(l => l.tipo === 'Suporte'    && l.meta !== null), l => l[col]));
    pts_sat.push(avg(all.filter(l => l.tipo === 'Satisfação' && l.meta !== null), l => l[col]));
  });

  const pad = { l:36, r:24, t:10, b:36 };
  const xW = W - pad.l - pad.r, yH = H - pad.t - pad.b;
  const allV = [...pts_inc, ...pts_sat].filter(v => v !== null);
  const minY = allV.length ? Math.max(0,  Math.min(...allV) - 5) : 0;
  const maxY = allV.length ? Math.min(105, Math.max(...allV) + 5) : 105;
  const xPos   = i => pad.l + i * (xW / (MESES().length - 1));
  const yScale = v => (yH - (v - minY) / (maxY - minY) * yH) + pad.t;

  let html = '';
  [0, 25, 50, 75, 100].filter(v => v >= minY && v <= maxY).forEach(v => {
    const y = yScale(v);
    html += `<line x1="${pad.l}" y1="${y}" x2="${W-pad.r}" y2="${y}" stroke="#f0f3f8" stroke-width="1"/>`;
    html += `<text x="${pad.l-5}" y="${y+4}" text-anchor="end" font-size="10" fill="#b0beca">${v}</text>`;
  });
  if (90 >= minY && 90 <= maxY) {
    const y90 = yScale(90);
    html += `<line x1="${pad.l}" y1="${y90}" x2="${W-pad.r}" y2="${y90}" stroke="#dc2626" stroke-width="1" stroke-dasharray="5,4"/>`;
    html += `<text x="${W-pad.r+4}" y="${y90+4}" font-size="9" fill="#dc2626">90%</text>`;
  }
  ABREV().forEach((ab, i) => {
    html += `<text x="${xPos(i)}" y="${H-4}" text-anchor="middle" font-size="10" fill="#b0beca">${ab}</text>`;
  });

  const series = (pts, color) => {
    let d = '', first = true;
    pts.forEach((v, i) => {
      if (v === null) { first = true; return; }
      d += first ? `M${xPos(i)},${yScale(v)}` : `L${xPos(i)},${yScale(v)}`; first = false;
    });
    if (!d) return '';
    return `<path d="${d}" fill="none" stroke="${color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>` +
      pts.map((v, i) => v === null ? '' :
        `<circle cx="${xPos(i)}" cy="${yScale(v)}" r="3.5" fill="${color}" stroke="#fff" stroke-width="2"/>`
      ).join('');
  };

  html += series(pts_inc, '#1a3a6b') + series(pts_sat, '#16a34a');
  html += `<circle cx="${pad.l+6}" cy="${H+20}" r="5" fill="#1a3a6b"/>
    <text x="${pad.l+14}" y="${H+24}" font-size="10" fill="#6b7d94">Incidentes</text>
    <circle cx="${pad.l+90}" cy="${H+20}" r="5" fill="#16a34a"/>
    <text x="${pad.l+98}" y="${H+24}" font-size="10" fill="#6b7d94">Satisfação</text>`;

  svg.setAttribute('viewBox', `0 0 ${W} ${H+28}`);
  svg.setAttribute('height', H+28);
  svg.innerHTML = html;
}

function drawDonut(acima, abaixo, total) {
  const svg = document.getElementById('chart-donut');
  if (!svg) return;
  document.getElementById('donut-num').textContent = total;
  if (total === 0) { svg.innerHTML = ''; return; }

  const cx = 85, cy = 85, ro = 68, ri = 48;
  function arc(cx, cy, r, s, e, lg) {
    return `M${cx+r*Math.cos(s)},${cy+r*Math.sin(s)} A${r},${r},0,${lg},1,${cx+r*Math.cos(e)},${cy+r*Math.sin(e)}`;
  }
  const t2   = (acima + abaixo) || 1;
  const ang1 = (acima / t2) * 2 * Math.PI;
  const st   = -Math.PI / 2, mid = st + ang1, en = st + 2 * Math.PI - 0.001;

  let html = '';
  if (acima > 0) {
    const lg = ang1 > Math.PI ? 1 : 0;
    html += `<path d="${arc(cx,cy,ro,st,mid,lg)} L${cx+ri*Math.cos(mid)},${cy+ri*Math.sin(mid)} ${arc(cx,cy,ri,mid,st,lg).replace('M','L')} Z" fill="#22c55e" opacity=".9"/>`;
  }
  if (abaixo > 0) {
    const lg = (2*Math.PI-ang1) > Math.PI ? 1 : 0;
    html += `<path d="${arc(cx,cy,ro,mid,en,lg)} L${cx+ri*Math.cos(en)},${cy+ri*Math.sin(en)} ${arc(cx,cy,ri,en,mid,lg).replace('M','L')} Z" fill="#ef4444" opacity=".9"/>`;
  }
  svg.innerHTML = html;

  document.getElementById('donut-legend').innerHTML = `
    <div class="legend-item"><span class="legend-dot" style="background:#22c55e"></span>Acima <strong>${acima}</strong></div>
    <div class="legend-item"><span class="legend-dot" style="background:#ef4444"></span>Abaixo <strong>${abaixo}</strong></div>`;
}

/* ═══════════════════════════════════════════════════════
   SLA POR ÁREA
═══════════════════════════════════════════════════════ */
function mesesComDados() {
  // Retorna Set com os meses que têm pelo menos um realizado > 0
  const com = new Set();
  MESES().forEach(m => {
    const sla = DATA.sla[m] || {};
    const linhas = Object.values(sla).flatMap(b => b.linhas);
    if (linhas.some(l => l.realizado > 0)) com.add(m);
  });
  return com;
}

function mesesComDados() {
  const com = new Set();
  MESES().forEach(m => {
    const sla = DATA.sla[m] || {};
    const linhas = Object.values(sla).flatMap(b => b.linhas);
    if (linhas.some(l => l.realizado > 0)) com.add(m);
  });
  return com;
}

function aplicarMesesNoSelect(selectId) {
  const comDados = mesesComDados();
  const sel = document.getElementById(selectId);
  if (!sel) return;
  sel.innerHTML = MESES().map(m =>
    comDados.has(m)
      ? `<option value="${m}">${m}</option>`
      : `<option value="${m}" disabled style="color:#c0cad8">${m}</option>`
  ).join('');
  // Selecionar o último mês com dados
  const ultimo = [...comDados].pop();
  if (ultimo) sel.value = ultimo;
}

function renderSla(root) {
  root.innerHTML = buildFilterBar('sla') + `<div class="sla-grid" id="sla-grid"></div>`;
  setTimeout(() => {
    const comDados = mesesComDados();
    const el = document.getElementById('sla-mes');
    if (!el) return;
    // Limpar options geradas pelo buildFilterBar antes do Choices inicializar
    el.innerHTML = '';
    new Choices(el, {
      searchEnabled: false,
      itemSelectText: '',
      shouldSort: false,
      allowHTML: false,
      choices: MESES().map(m => ({
        value: m,
        label: m,
        disabled: !comDados.has(m),
        selected: m === [...comDados].pop(),
      })),
    });
  }, 0);
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
          <thead><tr><th>Indicador</th><th>Meta</th><th>Resultado</th><th>Status</th></tr></thead>
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
  const dir  = ['Sistemas', 'Outros'].map(buildArea).join('');
  document.getElementById('sla-grid').innerHTML =
    `<div class="sla-col">${esq}</div><div class="sla-col">${dir}</div>`;
}

/* ═══════════════════════════════════════════════════════
   PROJETOS
═══════════════════════════════════════════════════════ */
function renderProjetos(root) {
  const resps = [...new Set(DATA.projetos.map(p => p.responsavel).filter(Boolean))].sort();
  const inds  = [...new Set(DATA.projetos.map(p => p.indicador).filter(Boolean))].sort();

  root.innerHTML = `
    <div class="proj-sticky-top">
      <div class="filter-bar" style="flex-wrap:wrap;gap:12px">
        <div class="filter-group">
          <span class="filter-label">Indicador</span>
          <select class="filter-select" id="proj-f-ind">
            <option value="">Todos</option>
            ${inds.map(i => `<option value="${i}">${i}</option>`).join('')}
          </select>
        </div>
        <div class="filter-group">
          <span class="filter-label">Responsável</span>
          <select class="filter-select" id="proj-f-resp">
            <option value="">Todos</option>
            ${resps.map(r => `<option value="${r}">${r}</option>`).join('')}
          </select>
        </div>
        <div class="filter-group">
          <span class="filter-label">Compartilhado</span>
          <select class="filter-select" id="proj-f-comp" onchange="reRenderProjetos()" style="min-width:120px">
            <option value="">Todos</option>
            <option value="Não">Não</option>
            <option value="Sim">Sim</option>
          </select>
        </div>
        <div class="filter-group">
          <span class="filter-label">Status</span>
          <select class="filter-select" id="proj-f-sta" onchange="reRenderProjetos()" style="min-width:120px">
            <option value="">Todos</option>
            <option value="J">🟢 Em dia</option>
            <option value="L">🔴 Atrasado</option>
          </select>
        </div>
      </div>

      <div class="kpi-grid" id="proj-kpis"></div>

      <div class="section-header">
        <span class="section-title">Cronograma Anual</span>
        <div class="section-line"></div>
      </div>
    </div>
    <div class="proj-wrapper" id="proj-tabela"></div>`;

  reRenderProjetos();
  setTimeout(() => {
    initChoices('proj-f-comp');
    initChoices('proj-f-sta');
    const cInd = new Choices(document.getElementById('proj-f-ind'), {
      searchEnabled: true,
      searchPlaceholderValue: 'Buscar…',
      itemSelectText: '',
      shouldSort: false,
      allowHTML: false,
    });
    cInd.containerOuter.element.classList.add('choices--lg');
    const cResp = new Choices(document.getElementById('proj-f-resp'), {
      searchEnabled: true,
      searchPlaceholderValue: 'Buscar…',
      itemSelectText: '',
      shouldSort: false,
      allowHTML: false,
    });
    cResp.containerOuter.element.classList.add('choices--lg');
  }, 0);
}

/* Estado de ordenação da tabela de projetos */
const projSort = { col: null, dir: 1 };

function sortProjetos(col) {
  if (projSort.col === col) {
    projSort.dir *= -1;
  } else {
    projSort.col = col;
    projSort.dir = 1;
  }
  reRenderProjetos();
}

function reRenderProjetos() {
  // Filtros
  const fInd  = document.getElementById('proj-f-ind')?.value  || '';
  const fResp = document.getElementById('proj-f-resp')?.value || '';
  const fComp = document.getElementById('proj-f-comp')?.value  || '';
  const fSta  = document.getElementById('proj-f-sta')?.value   || '';

  let projs = [...DATA.projetos];
  if (fInd)  projs = projs.filter(p => p.indicador === fInd);
  if (fResp) projs = projs.filter(p => p.responsavel === fResp);
  if (fComp) projs = projs.filter(p => p.compartilhado === fComp);
  if (fSta)  projs = projs.filter(p => p.status === fSta);

  // Ordenação
  if (projSort.col) {
    projs.sort((a, b) => {
      let va = a[projSort.col] || '';
      let vb = b[projSort.col] || '';
      return va.localeCompare(vb, 'pt-BR') * projSort.dir;
    });
  }

  // KPIs — total Projeto (tipo exato), total Compartilhado, Em dia, Atrasado
  const totalProjeto      = projs.filter(p => p.tipo === 'Projeto').length;
  const totalCompartilhado = projs.filter(p => p.tipo === 'Compartilhado').length;
  const emDia    = projs.filter(p => p.status === 'J').length;
  const atrasado = projs.filter(p => p.status === 'L').length;

  document.getElementById('proj-kpis').innerHTML = [
    { label: 'Projetos',           value: totalProjeto,       cls: 'blue'  },
    { label: 'Compartilhados',     value: totalCompartilhado, cls: 'blue'  },
    { label: '🟢 Dentro da meta', value: emDia,    cls: emDia > 0 ? 'green' : '' },
    { label: '🔴 Fora da meta',   value: atrasado, cls: atrasado > 0 ? 'red' : '' },
  ].map((k, i) => `
    <div class="kpi-card ${k.cls}" style="animation-delay:${i*0.07}s">
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-value">${k.value}</div>
    </div>`).join('');

  if (!projs.length) {
    document.getElementById('proj-tabela').innerHTML =
      `<div style="padding:32px;text-align:center;color:#a0aec0;background:#fff;border-radius:12px;border:0.5px solid #e3e9f2">
        Nenhum projeto encontrado com os filtros selecionados.
      </div>`;
    return;
  }

  // Cabeçalho com colunas ordenáveis
  const sortIcon = col => {
    if (projSort.col !== col) return '<span style="opacity:.3;margin-left:4px">↕</span>';
    return projSort.dir === 1
      ? '<span style="margin-left:4px">↑</span>'
      : '<span style="margin-left:4px">↓</span>';
  };
  const thStyle = `style="cursor:pointer;user-select:none" title="Clique para ordenar"`;
  const thMeses = ABREV().map(ab => `<th>${ab}</th>`).join('');

  let tbody = '';
  projs.forEach(p => {
    const sl   = labelStatus(p.status);
    const isOk = p.status === 'J';
    const dotC = isOk ? '#22c55e' : p.status === 'L' ? '#ef4444' : '#94a3b8';
    const bgSl = isOk ? '#dcfce7' : p.status === 'L' ? '#fee2e2' : '#f1f5f9';
    const fgSl = isOk ? '#166534' : p.status === 'L' ? '#991b1b' : '#475569';

    const slHtml = `
      <span style="display:inline-flex;align-items:center;gap:5px">
        <span style="width:9px;height:9px;border-radius:50%;background:${dotC};flex-shrink:0"></span>
        <span style="font-size:0.72rem;background:${bgSl};color:${fgSl};padding:1px 7px;border-radius:10px">${sl}</span>
      </span>`;

    const marc     = (p.marcos || '').replace(/\n/g,' ').trim();
    const marcHtml = marc.length > 55
      ? `<span class="marco-text">${marc}</span><button onclick="toggleMarco(this)" style="border:none;background:transparent;color:#1a3a6b;font-size:11px;cursor:pointer;padding:2px 3px;display:block;margin-top:2px">▾</button>`
      : `<span class="marco-text" style="height:auto">${marc || '–'}</span>`;

    // Coluna Compartilhado
    const compHtml = p.compartilhado === 'Sim'
      ? `<span style="background:#dbeafe;color:#1e40af;padding:1px 7px;border-radius:10px;font-size:0.72rem;font-weight:500">Sim</span>`
      : `<span style="background:#f1f5f9;color:#64748b;padding:1px 7px;border-radius:10px;font-size:0.72rem">Não</span>`;

    ['Meta', 'Realizado', 'Acumulado'].forEach((metr, mi) => {
      const vals   = p.meses[metr] || Array(12).fill(0);
      const rowCls = metr === 'Meta' ? 'meta-row' : metr === 'Realizado' ? 'real-row' : 'acum-row';
      const cels   = vals.map(v =>
        v > 0
          ? `<td class="has-val">${v.toFixed(0)}%</td>`
          : `<td class="empty">·</td>`
      ).join('');

      if (mi === 0) {
        // Linha separadora de grupo
        tbody += `<tr class="proj-group-row"><td colspan="${6 + 12}">📌 ${p.indicador}<span style="font-weight:400;color:#8394a8;font-size:0.71rem;margin-left:8px">— ${p.responsavel}</span></td></tr>`;
        tbody += `<tr class="${rowCls}">
          <td class="left" rowspan="3" style="max-width:220px;font-size:0.78rem;vertical-align:top">${p.indicador}</td>
          <td rowspan="3" style="max-width:120px;vertical-align:top" data-full="${marc}">
            ${marcHtml}
          </td>
          <td rowspan="3" style="vertical-align:middle;font-size:0.73rem">${p.responsavel || '–'}</td>
          <td rowspan="3" style="text-align:center;vertical-align:middle">${compHtml}</td>
          <td rowspan="3" style="text-align:center;vertical-align:middle">${slHtml}</td>
          <td class="linha-label left">${metr}</td>
          ${cels}
        </tr>`;
      } else {
        tbody += `<tr class="${rowCls}">
          <td class="linha-label left">${metr}</td>
          ${cels}
        </tr>`;
      }
    });
  });

  document.getElementById('proj-tabela').innerHTML = `
    <table class="proj-table">
      <thead><tr>
        <th class="left" ${thStyle} onclick="sortProjetos('indicador')" style="min-width:200px;cursor:pointer;user-select:none">Indicador${sortIcon('indicador')}</th>
        <th ${thStyle} onclick="sortProjetos('marcos')" style="min-width:110px;cursor:pointer;user-select:none">Marcos${sortIcon('marcos')}</th>
        <th ${thStyle} onclick="sortProjetos('responsavel')" style="min-width:120px;cursor:pointer;user-select:none">Responsável${sortIcon('responsavel')}</th>
        <th ${thStyle} onclick="sortProjetos('compartilhado')" style="min-width:100px;cursor:pointer;user-select:none">Compartilhado${sortIcon('compartilhado')}</th>
        <th ${thStyle} onclick="sortProjetos('status')" style="min-width:90px;cursor:pointer;user-select:none">Status${sortIcon('status')}</th>
        <th style="min-width:72px"></th>
        ${thMeses}
      </tr></thead>
      <tbody>${tbody}</tbody>
    </table>`;
}

/* ── Expansão inline de Marcos ─────────────────────────────── */
function toggleMarco(btn) {
  const td       = btn.closest('td');
  const span     = td.querySelector('.marco-text');
  const expanded = span.classList.contains('expanded');

  if (expanded) {
    // Recolher: fixa a altura atual em px, depois anima para 2.4em
    span.style.height = span.scrollHeight + 'px';
    requestAnimationFrame(() => {
      span.style.height = '2.4em';
    });
    span.classList.remove('expanded');
    td.style.maxWidth = '120px';
    td.style.width    = '';
    btn.textContent   = '▾';
    span.addEventListener('transitionend', () => { span.style.height = ''; }, { once: true });
  } else {
  td.style.maxWidth = 'none';
  td.style.width    = '320px';
  // Força reflow para o browser recalcular layout com a nova largura
  void td.offsetHeight;
  const fullH = span.scrollHeight + 'px';
  span.style.height = '2.4em';
  span.classList.add('expanded');
  requestAnimationFrame(() => {
    span.style.height = fullH;
  });
  btn.textContent = '▴';
  span.addEventListener('transitionend', () => { span.style.height = ''; }, { once: true });
}
}

/* ── Zoom ────────────────────────────────────────────────────── */
function applyZoom(val) {
  document.body.style.zoom = val + '%';
  const lbl = document.getElementById('zoom-label');
  if (lbl) lbl.textContent = val + '%';
  const slider = document.getElementById('zoom-slider');
  if (slider) slider.value = val;
}
function adjustZoom(delta) {
  const lbl = document.getElementById('zoom-label');
  const current = lbl ? parseInt(lbl.textContent) || 100 : 100;
  applyZoom(Math.min(150, Math.max(60, current + delta)));
}

/* ── Start ── */
window.addEventListener('DOMContentLoaded', init);
