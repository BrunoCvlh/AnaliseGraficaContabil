import pandas as pd


class ProcessadorBalancete:
    def __init__(self):
        self.df = None
        # Índices das colunas baseados no Excel padrão
        self.COL_DATA = 0
        self.COL_CODIGO = 1
        self.COL_NOME = 2
        self.COL_SALDO = 8
        self.COL_PLANO = 10

    def carregar_arquivo(self, caminho):
        if caminho.endswith('.csv'):
            self.df = pd.read_csv(caminho)
        else:
            self.df = pd.read_excel(caminho)

        # Tratamento inicial
        self.df.iloc[:, self.COL_DATA] = pd.to_datetime(self.df.iloc[:, self.COL_DATA]).dt.date
        self.df.iloc[:, self.COL_CODIGO] = self.df.iloc[:, self.COL_CODIGO].astype(str).str.strip()
        self.df.iloc[:, self.COL_NOME] = self.df.iloc[:, self.COL_NOME].astype(str).str.strip()

        # Cria coluna auxiliar para exibição no combobox
        self.df['display_conta'] = self.df.iloc[:, self.COL_CODIGO] + " - " + self.df.iloc[:, self.COL_NOME]
        return self.df

    def obter_lista_contas_combinada(self):
        if self.df is not None:
            return sorted(self.df['display_conta'].unique())
        return []

    def obter_lista_planos(self):
        if self.df is not None:
            return sorted(self.df.iloc[:, self.COL_PLANO].astype(str).unique())
        return []

    def filtrar_dados(self, conta_selecionada, nome_plano="Todos"):
        if self.df is None: return pd.DataFrame()

        codigo = conta_selecionada.split(' - ')[0]
        df_f = self.df[self.df.iloc[:, self.COL_CODIGO] == codigo]

        if nome_plano != "Todos":
            df_f = df_f[df_f.iloc[:, self.COL_PLANO].astype(str) == nome_plano]
        return df_f

    def filtrar_por_periodo(self, df_f, data_inicio, data_fim):
        try:
            # Garante formato datetime para comparação
            df_f.iloc[:, self.COL_DATA] = pd.to_datetime(df_f.iloc[:, self.COL_DATA])
            dt_ini = pd.to_datetime(data_inicio, dayfirst=True)
            dt_fim = pd.to_datetime(data_fim, dayfirst=True)

            mask = (df_f.iloc[:, self.COL_DATA] >= dt_ini) & (df_f.iloc[:, self.COL_DATA] <= dt_fim)
            return df_f.loc[mask].sort_values(by=df_f.columns[self.COL_DATA])
        except Exception as e:
            raise ValueError(f"Formato de data inválido: {e}")

    def obter_contas_filhas(self, df_f, nome_plano=None, data_inicio=None, data_fim=None):
        if df_f.empty: return df_f

        # Pega o código da conta "mãe" selecionada
        codigo_mae = str(df_f.iloc[0, self.COL_CODIGO]).rstrip('0')

        # Filtra na base geral quem começa com o código da mãe
        df_filhas = self.df[
            (self.df.iloc[:, self.COL_CODIGO].str.startswith(codigo_mae)) &
            (self.df.iloc[:, self.COL_CODIGO] != df_f.iloc[0, self.COL_CODIGO])  # Exclui a própria mãe da lista
            ]

        if nome_plano and nome_plano != "Todos":
            df_filhas = df_filhas[df_filhas.iloc[:, self.COL_PLANO].astype(str) == nome_plano]

        if data_inicio and data_fim:
            df_filhas.iloc[:, self.COL_DATA] = pd.to_datetime(df_filhas.iloc[:, self.COL_DATA])
            dt_ini = pd.to_datetime(data_inicio, dayfirst=True)
            dt_fim = pd.to_datetime(data_fim, dayfirst=True)
            mask = (df_filhas.iloc[:, self.COL_DATA] >= dt_ini) & (df_filhas.iloc[:, self.COL_DATA] <= dt_fim)
            df_filhas = df_filhas.loc[mask]

        return df_filhas