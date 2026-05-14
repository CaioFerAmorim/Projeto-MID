import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from utils.loader import carregar_dados, ORDEM_MESES


def render():
    df_raw = carregar_dados()

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="header-bar">
        <h1>PAINEL DE METAS – TI</h1>
        <p>Incidentes e Satisfação</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Filtro de Mês ─────────────────────────────────────────────────────────
    meses_disp = [m for m in ORDEM_MESES if m in df_raw['Mês'].unique()]
    if not meses_disp:
        meses_disp = sorted(df_raw['Mês'].dropna().unique().tolist())

    col_esp, col_mes = st.columns([4, 1])
    with col_mes:
        mes_sel = st.selectbox("📅 Período", meses_disp,
                               index=len(meses_disp) - 1,
                               key="vg_mes")

    df = df_raw[df_raw['Mês'] == mes_sel].copy()

    # ── Detectar colunas disponíveis ──────────────────────────────────────────
    # Colunas de incidentes e satisfação (aceita variações de nome)
    def find_col(df, candidates):
        for c in candidates:
            if c in df.columns:
                return c
        return None

    col_tipo      = find_col(df, ['Tipo', 'tipo'])
    col_area      = find_col(df, ['Área', 'Area', 'área'])
    col_meta_inc  = find_col(df, ['Meta_INC', 'Meta_Inc', 'Meta INC', 'Meta'])
    col_real_inc  = find_col(df, ['Realizado_INC', 'Realizado_Inc', 'Realizado INC', 'Realizado'])
    col_meta_sat  = find_col(df, ['Meta_SAT', 'Meta_Sat', 'Meta SAT'])
    col_real_sat  = find_col(df, ['Realizado_SAT', 'Realizado_Sat', 'Realizado SAT'])
    col_inc_total = find_col(df, ['Total_INC', 'Total INC', 'TotalINC', 'Total_Incidentes'])
    col_inc_ok    = find_col(df, ['Dentro_INC', 'Dentro INC', 'DentroINC', 'Dentro_Prazo'])
    col_status    = find_col(df, ['Status_Label', 'Status'])

    # Filtrar por tipo SLA (se coluna Tipo existir)
    df_sla = df.copy()
    if col_tipo:
        mask = df_sla[col_tipo].astype(str).str.contains('SLA|Incidente|Satisfa', case=False, na=False)
        if mask.any():
            df_sla = df_sla[mask]

    # ── KPIs globais ──────────────────────────────────────────────────────────
    def safe_mean(series):
        try:
            vals = pd.to_numeric(series, errors='coerce').dropna()
            return vals.mean() if len(vals) else 0
        except Exception:
            return 0

    inc_pct  = safe_mean(df_sla[col_real_inc]) * 100  if col_real_inc  else 0
    sat_pct  = safe_mean(df_sla[col_real_sat]) * 100  if col_real_sat  else 0
    meta_inc = safe_mean(df_sla[col_meta_inc]) * 100  if col_meta_inc  else 90
    meta_sat = safe_mean(df_sla[col_meta_sat]) * 100  if col_meta_sat  else 90

    # Áreas em risco
    areas_risco = 0
    if col_area and col_real_inc and col_meta_inc:
        for _, row in df_sla.groupby(col_area):
            pass  # calculado abaixo

    # Calcular tendência (mês anterior)
    idx_mes = ORDEM_MESES.index(mes_sel) if mes_sel in ORDEM_MESES else -1
    delta_inc = delta_sat = 0
    if idx_mes > 0:
        mes_ant = ORDEM_MESES[idx_mes - 1]
        df_ant  = df_raw[df_raw['Mês'] == mes_ant]
        if not df_ant.empty:
            inc_ant = safe_mean(df_ant[col_real_inc]) * 100 if col_real_inc else 0
            sat_ant = safe_mean(df_ant[col_real_sat]) * 100 if col_real_sat else 0
            delta_inc = inc_pct - inc_ant
            delta_sat = sat_pct - sat_ant

    # Saúde geral
    saudavel = inc_pct >= meta_inc and sat_pct >= meta_sat

    # Calcular áreas em risco
    if col_area and col_real_inc and col_meta_inc:
        areas_risco = 0
        for area, grp in df_sla.groupby(col_area):
            r_inc = safe_mean(grp[col_real_inc]) * 100
            m_inc = safe_mean(grp[col_meta_inc]) * 100
            if r_inc < m_inc:
                areas_risco += 1

    # ── Linha de KPI Cards ────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        saude_icon  = "🟢" if saudavel else "🔴"
        saude_texto = "Saudável" if saudavel else "Em Alerta"
        st.markdown(f"""
        <div class="kpi-card {'kpi-green' if saudavel else 'kpi-red'}">
            <div class="kpi-label">Visão Geral TI</div>
            <div class="kpi-value" style="font-size:1.4rem">{saude_icon} {saude_texto}</div>
            <div class="kpi-sub">Todas as áreas {'dentro' if saudavel else 'fora'} da meta</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        sinal = "↑" if delta_inc >= 0 else "↓"
        cor   = "#16a34a" if delta_inc >= 0 else "#dc2626"
        ok    = inc_pct >= meta_inc
        st.markdown(f"""
        <div class="kpi-card {'kpi-green' if ok else 'kpi-red'}">
            <div class="kpi-label">Incidentes dentro da Meta</div>
            <div class="kpi-value">{inc_pct:.1f}%</div>
            <div class="kpi-delta" style="color:{cor}">{sinal} {abs(delta_inc):.1f} p.p. vs mês ant.</div>
            <div class="kpi-sub">Meta: ≥ {meta_inc:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        sinal2 = "↑" if delta_sat >= 0 else "↓"
        cor2   = "#16a34a" if delta_sat >= 0 else "#dc2626"
        ok2    = sat_pct >= meta_sat
        st.markdown(f"""
        <div class="kpi-card {'kpi-green' if ok2 else 'kpi-red'}">
            <div class="kpi-label">Satisfação</div>
            <div class="kpi-value">{sat_pct:.1f}%</div>
            <div class="kpi-delta" style="color:{cor2}">{sinal2} {abs(delta_sat):.1f} p.p. vs mês ant.</div>
            <div class="kpi-sub">Meta: ≥ {meta_sat:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        cor_risco = "#16a34a" if areas_risco == 0 else "#dc2626"
        st.markdown(f"""
        <div class="kpi-card {'kpi-green' if areas_risco == 0 else 'kpi-red'}">
            <div class="kpi-label">Áreas em Risco</div>
            <div class="kpi-value" style="color:{cor_risco}">{areas_risco}</div>
            <div class="kpi-sub">{'Todas dentro da meta ✅' if areas_risco == 0 else f'{areas_risco} área(s) abaixo da meta'}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Tabela Desempenho por Área ─────────────────────────────────────────────
    st.markdown('<div class="section-title">Desempenho por Área</div>', unsafe_allow_html=True)

    if col_area and col_real_inc and col_meta_inc:
        rows_html = ""
        for area, grp in df_sla.groupby(col_area):
            r_inc = safe_mean(grp[col_real_inc]) * 100
            m_inc = safe_mean(grp[col_meta_inc]) * 100
            r_sat = safe_mean(grp[col_real_sat]) * 100 if col_real_sat else 0
            m_sat = safe_mean(grp[col_meta_sat]) * 100 if col_meta_sat else 0

            ok_inc = r_inc >= m_inc
            ok_sat = r_sat >= m_sat if col_real_sat else True

            # Tendência (mês anterior)
            t_inc = t_sat = "→"
            if idx_mes > 0:
                mes_ant = ORDEM_MESES[idx_mes - 1]
                grp_ant = df_raw[(df_raw['Mês'] == mes_ant) & (df_raw.get(col_area, pd.Series()) == area if col_area else True)]
                if col_area:
                    grp_ant = df_raw[(df_raw['Mês'] == mes_ant) & (df_raw[col_area] == area)]
                if not grp_ant.empty and col_real_inc:
                    prev_inc = safe_mean(grp_ant[col_real_inc]) * 100
                    t_inc = "↑" if r_inc > prev_inc else ("↓" if r_inc < prev_inc else "→")
                if not grp_ant.empty and col_real_sat:
                    prev_sat = safe_mean(grp_ant[col_real_sat]) * 100
                    t_sat = "↑" if r_sat > prev_sat else ("↓" if r_sat < prev_sat else "→")

            cls_inc = "val-green" if ok_inc else "val-red"
            cls_sat = "val-green" if ok_sat else "val-red"
            t_cls_i = "trend-up" if t_inc == "↑" else ("trend-down" if t_inc == "↓" else "trend-flat")
            t_cls_s = "trend-up" if t_sat == "↑" else ("trend-down" if t_sat == "↓" else "trend-flat")
            saude_cls   = "badge-green" if (ok_inc and ok_sat) else "badge-red"
            saude_label = "♥ SAUDÁVEL" if (ok_inc and ok_sat) else "⚠ ATENÇÃO"

            # Total incidentes
            tot_str = ""
            if col_inc_total and col_inc_ok:
                tot = grp[col_inc_total].sum()
                ok_n = grp[col_inc_ok].sum()
                tot_str = f"{int(ok_n):,} / {int(tot):,}".replace(",", ".")

            rows_html += f"""
            <tr>
              <td class="left">{'🖥' if 'Infra' in str(area) else '🏢' if 'Data' in str(area) else '🔗' if 'Rede' in str(area) else '🔒' if 'Cyber' in str(area) else '⚙'} {area}</td>
              <td class="{cls_inc}">{r_inc:.0f}%</td>
              <td>≥ {m_inc:.0f}%</td>
              <td class="{t_cls_i}">{t_inc}</td>
              <td>{tot_str if tot_str else '–'}</td>
              <td class="{cls_sat}">{r_sat:.0f}%</td>
              <td>≥ {m_sat:.0f}%</td>
              <td class="{t_cls_s}">{t_sat}</td>
              <td><span class="{saude_cls}">{saude_label}</span></td>
            </tr>"""

        st.markdown(f"""
        <table class="perf-table">
          <thead>
            <tr>
              <th class="left" rowspan="2">Área</th>
              <th colspan="4">INCIDENTES</th>
              <th colspan="3">SATISFAÇÃO</th>
              <th rowspan="2">Saúde</th>
            </tr>
            <tr>
              <th>Resultado</th><th>Meta</th><th>Tend.</th><th>Dentro/Total</th>
              <th>Resultado</th><th>Meta</th><th>Tend.</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
        """, unsafe_allow_html=True)
    else:
        st.info("Configure as colunas **Área**, **Realizado_INC**, **Meta_INC** no Excel para ver esta tabela.")

    # ── Gráficos inferiores ───────────────────────────────────────────────────
    st.markdown('<div class="section-title">Análise Gráfica</div>', unsafe_allow_html=True)
    g1, g2, g3 = st.columns([2, 1, 2])

    # Evolução últimos 6 meses
    with g1:
        st.markdown("**EVOLUÇÃO (ÚLTIMOS 6 MESES)**")
        idx_m = ORDEM_MESES.index(mes_sel) if mes_sel in ORDEM_MESES else len(ORDEM_MESES) - 1
        ultimos_6 = ORDEM_MESES[max(0, idx_m - 5): idx_m + 1]
        evol_inc, evol_sat, evol_meses = [], [], []
        for m in ultimos_6:
            sub = df_raw[df_raw['Mês'] == m]
            if not sub.empty:
                evol_inc.append(safe_mean(sub[col_real_inc]) * 100 if col_real_inc else 0)
                evol_sat.append(safe_mean(sub[col_real_sat]) * 100 if col_real_sat else 0)
                evol_meses.append(m[:3])

        if evol_meses:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=evol_meses, y=evol_inc, name="Incidentes (%)",
                                     line=dict(color="#3b82f6", width=2), mode="lines+markers"))
            fig.add_trace(go.Scatter(x=evol_meses, y=evol_sat, name="Satisfação (%)",
                                     line=dict(color="#10b981", width=2), mode="lines+markers"))
            fig.add_hline(y=90, line_dash="dot", line_color="#ef4444",
                          annotation_text="Meta: 90%", annotation_position="bottom right")
            fig.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0),
                              yaxis=dict(range=[80, 105]),
                              legend=dict(orientation="h", y=-0.25),
                              plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Dados insuficientes para evolução.")

    # Donut distribuição de incidentes
    with g2:
        st.markdown("**DISTRIBUIÇÃO DOS INCIDENTES**")
        if col_inc_total and col_inc_ok:
            total = int(df_sla[col_inc_total].sum())
            dentro = int(df_sla[col_inc_ok].sum())
            fora   = total - dentro
        else:
            total, dentro, fora = 0, 0, 0

        if total > 0:
            fig2 = go.Figure(data=[go.Pie(
                labels=['Dentro', 'Fora'],
                values=[dentro, fora],
                hole=0.65,
                marker_colors=['#10b981', '#ef4444'],
                textinfo='none'
            )])
            fig2.add_annotation(text=f"<b>{total:,}</b><br>Total".replace(",", "."),
                                 x=0.5, y=0.5, showarrow=False, font_size=14)
            fig2.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0),
                                showlegend=True,
                                legend=dict(orientation="h", y=-0.1),
                                plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Adicione colunas **Total_INC** e **Dentro_INC** para ver este gráfico.")

    # Top incidentes fora da meta
    with g3:
        st.markdown("**TOP 5 – INCIDENTES FORA DA META**")
        col_tipo_inc = find_col(df_sla, ['Tipo_Incidente', 'Tipo_Inc', 'Categoria', 'Tipo_Chamado'])
        col_fora = find_col(df_sla, ['Fora_INC', 'Fora_Meta', 'ForaMeta', 'Fora'])
        if col_tipo_inc and col_fora:
            top5 = (df_sla.groupby(col_tipo_inc)[col_fora]
                    .sum().sort_values(ascending=False).head(5).reset_index())
            top5.columns = ['Tipo', 'Qtde']
            total_fora = top5['Qtde'].sum()
            top5['%'] = top5['Qtde'] / total_fora * 100 if total_fora > 0 else 0

            fig3 = px.bar(top5, x='Qtde', y='Tipo', orientation='h',
                          text=top5['%'].apply(lambda x: f"{x:.1f}%"),
                          color_discrete_sequence=['#ef4444'])
            fig3.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0),
                               yaxis=dict(autorange="reversed"),
                               plot_bgcolor="white", paper_bgcolor="white")
            fig3.update_traces(textposition='outside')
            st.plotly_chart(fig3, use_container_width=True)
        else:
            # Placeholder com dados do próprio df se não tiver coluna específica
            st.info("Adicione colunas **Tipo_Incidente** e **Fora_INC** para ver este gráfico.")

    st.divider()
    st.caption(f"Fonte: Ferramenta de Gestão de Serviços | Metas: Incidentes ≥ 90% | Satisfação ≥ 90%")