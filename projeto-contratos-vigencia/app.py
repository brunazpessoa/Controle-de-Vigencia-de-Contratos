from datetime import datetime
import pandas as pd
import streamlit as st
import plotly.express as px


# 1. Upload dos dados ------------------------------------------------------------------------------------------------------------------------------

    url_base = "https://raw.githubusercontent.com/brunazpessoa/Controle-de-Vigencia-de-Contratos/main/projeto-contratos-vigencia/compras-contratos-administrativos.xlsx"

    df = pd.read_excel(url_base)
    st.success("Base carregada com sucesso!")
    
# 2. Tratamento dos dados ------------------------------------------------------------------------------------------------------------------------------

    #convertendo as colunas de data para "datetime"
    df['data_de_assinatura'] = pd.to_datetime(df['data_de_assinatura'], errors='coerce')
    df['data_de_atualizacao'] = pd.to_datetime(df['data_de_atualizacao'], errors='coerce')
    df['inicio_vigencia'] = pd.to_datetime(df['inicio_vigencia'], errors='coerce')
    df['data_de_publicacao_do_extrato_no_dou'] = pd.to_datetime(df['data_de_publicacao_do_extrato_no_dou'], errors='coerce')
    df['fim_vigencia_atualizado'] = pd.to_datetime(df['fim_vigencia_atualizado'], errors='coerce')
    df['fim_vigencia_original'] = pd.to_datetime(df['fim_vigencia_original'], errors='coerce')

    df['contratado'] = df['contratado'].str.split(' - ').str[1] #retirar cnpj da coluna contratado




# 3. Cálculo de dias para vencimento ------------------------------------------------------------------------------------------------------------------------------

    #nova coluna "data_fim_utilizada" para termos consolidada uma única data final para cada contrato
    #caso uma data na coluna "fim_vigencia_atualizado" esteja em branco, utilizará a data da coluna "fim_vigencia _original" da mesma linha
    df['data_fim_utilizada'] = df['fim_vigencia_atualizado'].combine_first(df['fim_vigencia_original'])

    #contagem de dias até vencimento do contrato
    hoje = pd.Timestamp.today()
    df['dias_para_vencer'] = (df['data_fim_utilizada'] - hoje).dt.days

# 4. Classificação do Status ------------------------------------------------------------------------------------------------------------------------------

    def classificar_vigencia(dias):
        if pd.isna(dias):
            return "Data inválida"
        elif dias < 0:
            return "Vencido"
        elif dias <= 30:
            return "A vencer (30 dias)"
        else:
            return "Em andamento"

    #nova coluna "status_vigencia"
    df['status_vigencia'] = df['dias_para_vencer'].apply(classificar_vigencia)

# 5. Visualizações e Gráficos ------------------------------------------------------------------------------------------------------------------------------

    st.title("Controle de Vigência dos Contratos")
    st.subheader("Contratações administrativas realizadas pelo BNDES a partir de 2006.")

    # VISÃO 1: Contratos próximos ao vencimento
    st.subheader("⚠️ Contratos a vencer nos próximos 30 dias")

    proximos = df[df['status_vigencia'] == "A vencer (30 dias)"].copy()

    # formartar valores como moeda
    proximos['valor_formatado'] = proximos['valor_global_acumulado'].apply(lambda x: f"R$ {x:,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))

    # mostrar apenas colunas desejadas, incluindo valor formatado
    st.write(f"Total: {len(proximos)} contratos")
    st.dataframe(proximos[['objeto', 'valor_formatado', 'dias_para_vencer']].rename(columns={'valor_formatado': 'Valor acumulado (R$)'}))


    # VISÃO 2: Distribuição por status
    st.subheader("📊 Distribuição por status de vigência")
    ## contar ocorrências
    status_counts = df['status_vigencia'].value_counts().reset_index()
    status_counts.columns = ['status', 'quantidade']

    # gráfico de barras
    fig = px.bar(
        status_counts,
        x='status',
        y='quantidade',
        title='Distribuição por status de vigência',
        text='quantidade', #rótulos de dados
        labels={'status': 'Status', 'quantidade': 'Quantidade'},
    )

    fig.update_layout(xaxis_tickangle=0)  # mantém horizontal
    fig.update_traces(
        textposition='auto',
        textfont=dict(
            size=14
        ) 
    )
    st.plotly_chart(fig, use_container_width=True)
        
    # VISÃO 3: Valor total por status e por ano 
    st.subheader("💰 Valor total por status de vigência")

    # Seleção do ano
    anos_disponiveis = sorted(df['ano'].dropna().unique(), reverse=True)
    ano_selecionado = st.selectbox("Selecione o ano de assinatura", anos_disponiveis)

    # Filtro por ano
    df_filtrado_ano = df[df['ano'] == ano_selecionado]

    # Agrupamento por status de vigência
    valor_por_status = df_filtrado_ano.groupby('status_vigencia')['valor_global_acumulado'].sum().sort_values(ascending=False)

    # Transformar em DataFrame para usar no gráfico
    valor_por_status_df = valor_por_status.reset_index()
    valor_por_status_df.columns = ['status', 'valor']

    # Gráfico
    fig = px.bar(
        valor_por_status_df,
        x='status',
        y='valor',
        title=f'💰 Valor total por status - Ano {ano_selecionado}',
        text='valor',
        labels={'status': 'Status', 'valor': 'Valor acumulado (R$)'}
    )

    # Formatação de rótulos e eixos como moeda R$
    fig.update_layout(
        xaxis_tickangle=0,
        yaxis_tickprefix="R$ ",
        yaxis_tickformat=",", 
    )

    # mostrar os valores em cima das barras, também como moeda
    fig.update_traces(
        texttemplate='R$ %{text:,.2f}',
        textposition='auto',
        textfont=dict(
            size=14
        ) 
    )
    
    st.plotly_chart(fig, use_container_width=True)


    # --- VISÃO 4: Top 10 fornecedores com contratos ativos ---
    st.subheader("🏆 Top 10 fornecedores com contratos em andamento")
    # filtro de contratos em andamento
    ativos = df[df['status_vigencia'] == 'Em andamento']

    # gráfico de barras horizontais
    top_qtd = ativos['contratado'].value_counts().head(10)
    fig_qtd = px.bar(
        top_qtd.sort_values(),
        orientation='h',
        title='📌 Por quantidade de contratos',
        labels={'value': 'Quantidade', 'index': 'Fornecedor'}
    )


    st.plotly_chart(fig_qtd, use_container_width=True)

    # gráfico de pizza
    top_valor = ativos.groupby('contratado')['valor_global_acumulado'].sum().sort_values(ascending=False).head(10)
    top_valor_df = top_valor.reset_index()
    top_valor_df.columns = ['fornecedor', 'valor']

    fig_valor = px.pie(
        top_valor_df,
        names='fornecedor',
        values='valor',
        title='💰 Distribuição percentual por valor acumulado - Top 10 fornecedores',
    )

    # melhorar visual da pizza
    fig_valor.update_traces(textposition='inside', textinfo='percent')
    fig_valor.update_layout(font=dict(size=12))

    st.plotly_chart(fig_valor, use_container_width=True)

    #fim da página
    st.markdown("---")
    st.caption('Base de Dados utilizada: https://dados.gov.br/dados/conjuntos-dados/compras-contratos-administrativos1 ')
    st.caption('Desenvolvido por Bruna Zakaib Pessoa.')
    st.caption('Código completo: https://github.com/brunazpessoa/Controle-de-Vigencia-de-Contratos')
    
