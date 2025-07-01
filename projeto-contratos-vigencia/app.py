from datetime import datetime
import pandas as pd
import streamlit as st
import plotly.express as px

# 1. Upload dos dados
url_base = "https://raw.githubusercontent.com/brunazpessoa/Controle-de-Vigencia-de-Contratos/main/projeto-contratos-vigencia/compras-contratos-administrativos.xlsx"
df = pd.read_excel(url_base)
st.success("Base carregada com sucesso!")

# 2. Tratamento dos dados
df['data_de_assinatura'] = pd.to_datetime(df['data_de_assinatura'], errors='coerce')
df['data_de_atualizacao'] = pd.to_datetime(df['data_de_atualizacao'], errors='coerce')
df['inicio_vigencia'] = pd.to_datetime(df['inicio_vigencia'], errors='coerce')
df['data_de_publicacao_do_extrato_no_dou'] = pd.to_datetime(df['data_de_publicacao_do_extrato_no_dou'], errors='coerce')
df['fim_vigencia_atualizado'] = pd.to_datetime(df['fim_vigencia_atualizado'], errors='coerce')
df['fim_vigencia_original'] = pd.to_datetime(df['fim_vigencia_original'], errors='coerce')
df['contratado'] = df['contratado'].str.split(' - ').str[1]

# 3. Dias até vencimento
df['data_fim_utilizada'] = df['fim_vigencia_atualizado'].combine_first(df['fim_vigencia_original'])
hoje = pd.Timestamp.today()
df['dias_para_vencer'] = (df['data_fim_utilizada'] - hoje).dt.days

# 4. Classificação do status
def classificar_vigencia(dias):
    if pd.isna(dias):
        return "Data inválida"
    elif dias < 0:
        return "Vencido"
    elif dias <= 30:
        return "A vencer (30 dias)"
    else:
        return "Em andamento"

df['status_vigencia'] = df['dias_para_vencer'].apply(classificar_vigencia)

# 5. Visualizações
st.title("Controle de Vigência dos Contratos")
st.subheader("Contratações administrativas realizadas pelo BNDES a partir de 2006.")

# VISÃO 1
st.subheader("⚠️ Contratos a vencer nos próximos 30 dias")
proximos = df[df['status_vigencia'] == "A vencer (30 dias)"].copy()
proximos['valor_formatado'] = proximos['valor_global_acumulado'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))
st.write(f"Total: {len(proximos)} contratos")
st.dataframe(proximos[['objeto', 'valor_formatado', 'dias_para_vencer']].rename(columns={'valor_formatado': 'Valor acumulado (R$)'}))

# VISÃO 2
st.subheader("📊 Distribuição por status de vigência")
status_counts = df['status_vigencia'].value_counts().reset_index()
status_counts.columns = ['status', 'quantidade']
fig = px.bar(status_counts, x='status', y='quantidade', title='Distribuição por status de vigência', text='quantidade',
             labels={'status': 'Status', 'quantidade': 'Quantidade'})
fig.update_layout(xaxis_tickangle=0)
fig.update_traces(textposition='auto', textfont=dict(size=14))
st.plotly_chart(fig, use_container_width=True)

# VISÃO 3
st.subheader("💰 Valor total por status de vigência")
anos_disponiveis = sorted(df['ano'].dropna().unique(), reverse=True)
ano_selecionado = st.selectbox("Selecione o ano de assinatura", anos_disponiveis)
df_filtrado_ano = df[df['ano'] == ano_selecionado]
valor_por_status = df_filtrado_ano.groupby('status_vigencia')['valor_global_acumulado'].sum().sort_values(ascending=False)
valor_por_status_df = valor_por_status.reset_index()
valor_por_status_df.columns = ['status', 'valor']
fig = px.bar(valor_por_status_df, x='status', y='valor', title=f'💰 Valor total por status - Ano {ano_selecionado}', text='valor',
             labels={'status': 'Status', 'valor': 'Valor acumulado (R$)'})
fig.update_layout(xaxis_tickangle=0, yaxis_tickprefix="R$ ", yaxis_tickformat=",")
fig.update_traces(texttemplate='R$ %{text:,.2f}', textposition='auto', textfont=dict(size=14))
st.plotly_chart(fig, use_container_width=True)

# --- VISÃO 4: Top 10 fornecedores com contratos ativos ---
st.subheader("🏆 Top 10 fornecedores com contratos em andamento")

ativos = df[df['status_vigencia'] == 'Em andamento']

# --- Por quantidade de contratos ---
top_qtd = ativos['contratado'].value_counts().head(10)

fig_qtd = px.bar(
    top_qtd.sort_values(),
    orientation='h',
    title='📌 Por quantidade de contratos',
    labels={'value': 'Quantidade', 'index': 'Fornecedor'},
    color_discrete_sequence=['#6ecdf2']
)

fig_qtd.update_layout(
    height=500,
    width=500,
    yaxis=dict(tickfont=dict(size=12)),
    xaxis=dict(title='Quantidade'),
    margin=dict(l=120, r=20, t=60, b=40),
    showlegend=False
)

fig_qtd.update_traces(
    text=top_qtd.sort_values().values,
    textposition='auto',
    textfont=dict(size=12)
)

st.plotly_chart(fig_qtd, use_container_width=True)

# --- Por valor acumulado ---
top_valor = ativos.groupby('contratado')['valor_global_acumulado'].sum().sort_values(ascending=False).head(10)
top_valor_df = top_valor.reset_index()
top_valor_df.columns = ['fornecedor', 'valor']

# Ordenar do menor para o maior para visual melhor em barras horizontais
top_valor_df = top_valor_df.sort_values(by='valor', ascending=True)

# Cores: top 3 com destaque, os demais em cinza
cores = ['#1f77b4', '#ff7f0e', '#2ca02c'] + ['lightgray'] * (len(top_valor_df) - 3)

fig_valor = px.bar(
    top_valor_df,
    x='valor',
    y='fornecedor',
    orientation='h',
    title='💰 Valor acumulado - Top 10 fornecedores',
    text='valor',
    labels={'valor': 'Valor acumulado (R$)', 'fornecedor': 'Fornecedor'},
)

fig_valor.update_traces(
    marker_color=cores,
    texttemplate='R$ %{text:,.2f}',
    textposition='auto',
    textfont=dict(size=12)
)

fig_valor.update_layout(
    yaxis=dict(tickfont=dict(size=11)),
    xaxis_tickprefix="R$ ",
    xaxis_tickformat=",",
    margin=dict(l=150, r=40, t=60, b=40),
    height=500,
)

st.plotly_chart(fig_valor, use_container_width=True)

# Rodapé
st.markdown("---")
st.caption('Base: https://dados.gov.br/dados/conjuntos-dados/compras-contratos-administrativos1')
st.caption('Desenvolvido por Bruna Zakaib Pessoa.')
st.caption('Código: https://github.com/brunazpessoa/Controle-de-Vigencia-de-Contratos')
