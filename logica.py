import pandas as pd

class ProcessadorBalancete:
    def __init__(self):
        self.df = None
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

        self.df.iloc[:, self.COL_DATA] = pd.to_datetime(self.df.iloc[:, self.COL_DATA]).dt.date
        self.df.iloc[:, self.COL_CODIGO] = self.df.iloc[:, self.COL_CODIGO].astype(str).str.strip()
        self.df.iloc[:, self.COL_NOME] = self.df.iloc[:, self.COL_NOME].astype(str).str.strip()

        self.df['display_conta'] = self.df.iloc[:, self.COL_CODIGO] + " - " + self.df.iloc[:, self.COL_NOME]
        return self.df

    def obter_lista_contas_combinada(self):
        if self.df is not None:
            return sorted(self.df['display_conta'].unique())
        return []

    def obter_lista_planos(self):
        if self.df is not None and len(self.df.columns) > self.COL_PLANO:
            return sorted(self.df.iloc[:, self.COL_PLANO].dropna().unique().astype(str))
        return ["Todos"]

    def filtrar_dados(self, selecao_combinada, nome_plano=None):
        df_f = self.df[self.df['display_conta'] == selecao_combinada].copy()
        if nome_plano and nome_plano != "Todos":
            df_f = df_f[df_f.iloc[:, self.COL_PLANO].astype(str) == nome_plano]
        return df_f

    def filtrar_por_periodo(self, df_f, data_inicio, data_fim):
        try:
            df_f.iloc[:, self.COL_DATA] = pd.to_datetime(df_f.iloc[:, self.COL_DATA])
            dt_ini = pd.to_datetime(data_inicio, dayfirst=True)
            dt_fim = pd.to_datetime(data_fim, dayfirst=True)
            mask = (df_f.iloc[:, self.COL_DATA] >= dt_ini) & (df_f.iloc[:, self.COL_DATA] <= dt_fim)
            return df_f.loc[mask].sort_values(by=df_f.columns[self.COL_DATA])
        except Exception as e:
            raise ValueError(f"Formato de data inválido: {e}")

    def obter_contas_filhas(self, df_f, nome_plano=None, data_inicio=None, data_fim=None):
        if df_f.empty: return df_f

        codigo_mae = str(df_f.iloc[0, self.COL_CODIGO]).rstrip('0')
        df_filhas = self.df[
            (self.df.iloc[:, self.COL_CODIGO].str.startswith(codigo_mae)) &
            (self.df.iloc[:, self.COL_CODIGO] != str(df_f.iloc[0, self.COL_CODIGO]))
        ].copy()

        if nome_plano and nome_plano != "Todos":
            df_filhas = df_filhas[df_filhas.iloc[:, self.COL_PLANO].astype(str) == nome_plano]

        if data_inicio and data_fim:
            try:
                df_filhas = self.filtrar_por_periodo(df_filhas, data_inicio, data_fim)
            except:
                pass

        return df_filhas.sort_values(by=self.df.columns[self.COL_CODIGO])