import streamlit as st
import pandas as pd
from utils.loader import carregar_dados

st.set_page_config(layout="wide", page_title="Cronograma de Projetos")

def tratar_mes(valor):
    """Converte datas do Excel ou nomes de meses para texto padrão."""
    meses_pt = {
        1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril',
        5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
        9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
    }
    if hasattr(valor, 'month'):
        return meses_pt[valor.month]
    
    try:
        num = int(float(valor))
        if 1 <= num <= 12:
            return meses_pt[num]
    except:
        pass

    v = str(valor).lower().strip()
    if '/' in v:
        try:
            data = pd.to_datetime(v, dayfirst=True)
            return meses_pt[data.month]
        except:
            pass
    return v

def mapear_status(val):
    """Mapeia status J (verde) e L (vermelho)"""
    v = str(val).upper().strip()
    if v == 'J':
        return "🟢 Em dia"
    elif v == 'L':
        return "🔴 Atrasado"
    return "⚪ Sem status"

# Carregar dados
df_original = carregar_dados()
df = df_original.copy()

# Limpar nomes das colunas
df.columns = [str(c).strip() for c in df.columns]

# Verificar se as colunas existem
colunas_necessarias = ['Meta', 'Realizado', 'Acumulado', 'Mês', 'Tipo', 'Indicador']
for col in colunas_necessarias:
    if col not in df.columns:
        st.error(f"Coluna '{col}' não encontrada no Excel. Colunas disponíveis: {list(df.columns)}")
        st.stop()

# Filtrar apenas Projetos
df = df[df['Tipo'].astype(str).str.contains('Projeto', case=False, na=False)]

if df.empty:
    st.warning("Nenhum projeto encontrado após filtrar por 'Tipo' = Projeto")
    st.stop()

# Tratar valores percentuais
for col in ['Meta', 'Realizado', 'Acumulado']:
    if col in df.columns:
        df[col] = df[col].astype(str).str.replace('%', '').str.replace(',', '.').str.strip()
        df[col] = df[col].replace('', '0').replace('nan', '0')
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        # Converter para decimal (15 -> 0.15)
        df[col] = df[col].apply(lambda x: x/100 if x > 1 else x)

# Tratar meses e status
df['Mês'] = df['Mês'].apply(tratar_mes)
df['Status_Visual'] = df['Status'].apply(mapear_status)

# Limpar strings
for c in ['Indicador', 'Marcos', 'Responsável']:
    if c in df.columns:
        df[c] = df[c].astype(str).str.strip()

st.title("📊 Cronograma Anual de Projetos")
st.markdown("---")

try:
    ordem_meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 
                   'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    
    # ==================== NOVA ABORDAGEM ====================
    # Criar uma lista para armazenar as linhas da tabela final
    linhas_tabela = []
    
    # Para cada projeto único
    for projeto in df['Indicador'].unique():
        # Filtrar dados do projeto
        df_projeto = df[df['Indicador'] == projeto]
        
        # Pegar informações fixas do projeto
        marcos = df_projeto['Marcos'].iloc[0]
        responsavel = df_projeto['Responsável'].iloc[0]
        status = df_projeto['Status_Visual'].iloc[0]
        
        # Para cada métrica (Meta, Realizado, Acumulado)
        for metrica in ['Meta', 'Realizado', 'Acumulado']:
            # Criar dicionário com os dados da linha
            linha = {
                'Métrica': metrica,
                'Indicador': projeto,
                'Marcos': marcos,
                'Responsável': responsavel,
                'Status_Visual': status
            }
            
            # Para cada mês, buscar o valor
            for mes in ordem_meses:
                # Filtrar o valor para este mês e métrica
                valor = df_projeto[(df_projeto['Mês'] == mes)][metrica].values
                
                if len(valor) > 0:
                    # Converter para percentual (multiplicar por 100)
                    linha[mes] = valor[0] * 100
                else:
                    linha[mes] = 0
            
            linhas_tabela.append(linha)
    
    # Criar DataFrame final
    tabela_final = pd.DataFrame(linhas_tabela)
    
    # Reordenar colunas
    colunas_fixas = ['Métrica', 'Indicador', 'Marcos', 'Responsável', 'Status_Visual']
    tabela_final = tabela_final[colunas_fixas + ordem_meses]
    
    # Ordenar por Indicador e Métrica
    tabela_final = tabela_final.sort_values(['Indicador', 'Métrica'])
    
    # ==================== FILTROS ====================
    st.sidebar.header("🔍 Filtros")
    
    # Filtro por Indicador (Projeto)
    indicadores = ['Todos'] + sorted(tabela_final['Indicador'].unique().tolist())
    filtro_indicador = st.sidebar.selectbox("📌 Projeto", indicadores)
    
    # Filtro por Responsável
    responsaveis = ['Todos'] + sorted(tabela_final['Responsável'].unique().tolist())
    filtro_responsavel = st.sidebar.selectbox("👤 Responsável", responsaveis)
    
    # Filtro por Status
    status_opcoes = ['Todos', '🟢 Em dia', '🔴 Atrasado', '⚪ Sem status']
    filtro_status = st.sidebar.selectbox("🎯 Status", status_opcoes)
    
    # Filtro por Métrica
    metricas = ['Todos'] + sorted(tabela_final['Métrica'].unique().tolist())
    filtro_metrica = st.sidebar.selectbox("📊 Métrica", metricas)
    
    # Aplicar filtros
    df_filtrado = tabela_final.copy()
    
    if filtro_indicador != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Indicador'] == filtro_indicador]
    
    if filtro_responsavel != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Responsável'] == filtro_responsavel]
    
    if filtro_status != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Status_Visual'] == filtro_status]
    
    if filtro_metrica != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Métrica'] == filtro_metrica]
    
    # Mostrar quantidade de registros
    st.sidebar.markdown("---")
    st.sidebar.metric("📊 Registros encontrados", len(df_filtrado))
    
    # Botão para limpar filtros
    if st.sidebar.button("🗑️ Limpar Filtros"):
        st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.caption("💡 Dica: Use os filtros para refinar sua busca")
    
    # ==================== TABELA PRINCIPAL ====================
    st.subheader(f"📋 Resultados ({len(df_filtrado)} registros)")
    
    if not df_filtrado.empty:
        # Exibir dataframe com formatação
        st.dataframe(
            df_filtrado,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Métrica": st.column_config.TextColumn(
                    "Métrica", 
                    width="small",
                    help="Meta, Realizado ou Acumulado"
                ),
                "Indicador": st.column_config.TextColumn(
                    "Projeto", 
                    width="medium",
                    help="Nome do projeto/indicador"
                ),
                "Marcos": st.column_config.TextColumn(
                    "Principais Marcos", 
                    width="large",
                    help="Marcos e entregas do projeto"
                ),
                "Responsável": st.column_config.TextColumn(
                    "Responsável", 
                    width="medium",
                    help="Pessoa responsável pelo projeto"
                ),
                "Status_Visual": st.column_config.TextColumn(
                    "Status", 
                    width="small",
                    help="🟢 Em dia (J) | 🔴 Atrasado (L)"
                ),
                **{mes: st.column_config.NumberColumn(
                    mes.capitalize(), 
                    format="%.1f%%",
                    help=f"Percentual para {mes}"
                ) for mes in ordem_meses}
            }
        )
        
        # ==================== RESUMO ESTATÍSTICO ====================
        st.subheader("📊 Resumo Estatístico")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # Total de projetos únicos
            total_projetos = df_filtrado['Indicador'].nunique()
            st.metric("Total de Projetos", total_projetos)
        
        with col2:
            # Projetos em dia (status verde)
            projetos_verde = df_filtrado[df_filtrado['Status_Visual'].str.contains('🟢', na=False)]['Indicador'].nunique()
            st.metric("Projetos em Dia", projetos_verde)
        
        with col3:
            # Projetos atrasados (status vermelho)
            projetos_vermelho = df_filtrado[df_filtrado['Status_Visual'].str.contains('🔴', na=False)]['Indicador'].nunique()
            st.metric("Projetos Atrasados", projetos_vermelho)
        
        with col4:
            # Média de progresso dos projetos
            realizado_data = df_filtrado[df_filtrado['Métrica'] == 'Realizado']
            if not realizado_data.empty:
                # Pega o último mês com valor para cada projeto
                progressos = []
                for projeto in realizado_data['Indicador'].unique():
                    dados_projeto = realizado_data[realizado_data['Indicador'] == projeto]
                    if not dados_projeto.empty:
                        for mes in reversed(ordem_meses):
                            valor = dados_projeto[mes].iloc[0]
                            if valor > 0:
                                progressos.append(valor)
                                break
                if progressos:
                    media_progresso = sum(progressos) / len(progressos)
                    st.metric("Média de Progresso", f"{media_progresso:.1f}%")
                else:
                    st.metric("Média de Progresso", "0%")
            else:
                st.metric("Média de Progresso", "N/A")
        
        # ==================== TABELA DE PROJETOS ÚNICOS ====================
        with st.expander("📋 Ver Lista de Projetos"):
            # Criar resumo por projeto
            projetos_unicos = []
            for projeto in df_filtrado['Indicador'].unique():
                dados_projeto = df_filtrado[df_filtrado['Indicador'] == projeto]
                
                # Pegar status do projeto
                status = dados_projeto['Status_Visual'].iloc[0]
                
                # Pegar responsável
                responsavel = dados_projeto['Responsável'].iloc[0]
                
                # Pegar meta final (dezembro)
                meta_data = dados_projeto[dados_projeto['Métrica'] == 'Meta']
                meta_final = meta_data['dezembro'].iloc[0] if not meta_data.empty else 0
                
                # Pegar progresso atual
                realizado_data_proj = dados_projeto[dados_projeto['Métrica'] == 'Realizado']
                progresso = 0
                if not realizado_data_proj.empty:
                    for mes in reversed(ordem_meses):
                        valor = realizado_data_proj[mes].iloc[0]
                        if valor > 0:
                            progresso = valor
                            break
                
                # Calcular percentual concluído
                if meta_final > 0:
                    perc_concluido = (progresso / meta_final * 100)
                else:
                    perc_concluido = 0
                
                projetos_unicos.append({
                    'Projeto': projeto,
                    'Status': status,
                    'Responsável': responsavel,
                    'Meta Final (%)': meta_final,
                    'Progresso (%)': progresso,
                    '% Concluído': perc_concluido
                })
            
            df_projetos = pd.DataFrame(projetos_unicos)
            df_projetos = df_projetos.sort_values('Progresso (%)', ascending=False)
            
            st.dataframe(
                df_projetos,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Status": st.column_config.TextColumn("Status", width="small"),
                    "Projeto": st.column_config.TextColumn("Projeto", width="large"),
                    "Responsável": st.column_config.TextColumn("Responsável", width="medium"),
                    "Meta Final (%)": st.column_config.NumberColumn("Meta Final", format="%.1f%%"),
                    "Progresso (%)": st.column_config.ProgressColumn(
                        "Progresso",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                    ),
                    "% Concluído": st.column_config.NumberColumn("% da Meta", format="%.1f%%")
                }
            )
    
    else:
        st.warning("Nenhum registro encontrado com os filtros selecionados.")

except Exception as e:
    st.error(f"Erro ao processar tabela: {e}")
    st.code(f"Detalhes do erro: {str(e)}")

st.divider()
st.caption("Dashboard de Acompanhamento de Projetos - Status: J (Verde) e L (Vermelho)")