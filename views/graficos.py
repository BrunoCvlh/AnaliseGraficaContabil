import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter


class GerenciadorGrafico:
    def __init__(self, frame_pai):
        self.frame_pai = frame_pai
        self.figura = None

    def desenhar(self, lista_dados):
        # Limpa widgets anteriores
        for w in self.frame_pai.winfo_children():
            w.destroy()

        plt.close('all')
        self.figura, ax = plt.subplots(figsize=(6, 4), dpi=100)

        # Ajuste de margens (Top 0.75 para não cortar título/legenda)
        self.figura.subplots_adjust(top=0.75, bottom=0.20)

        cores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        marcadores = ['o', 's', '^', 'D']

        titulo_parts = []
        todos_valores_y = []

        for item in lista_dados:
            df = item["df"]
            conta = item["conta"]
            plano = item["plano"]
            idx = item["indice"]

            cor = cores[idx % len(cores)]
            marcador = marcadores[idx % len(marcadores)]

            df_plot = df.sort_values(by=df.columns[0])
            x = df_plot.iloc[:, 0]
            y = df_plot.iloc[:, 8]

            todos_valores_y.extend(y.tolist())

            legenda = f"{conta.split(' - ')[0]} ({plano})"
            titulo_parts.append(conta.split(' - ')[0])

            ax.plot(x, y, marker=marcador, color=cor, linewidth=2, label=legenda)

            # Anotações dos valores
            offset = 10 if idx % 2 == 0 else -15
            for vx, vy in zip(x, y):
                label_valor = vy / 1000
                ax.annotate(f'{label_valor:,.1f}K'.replace(',', 'X').replace('.', ',').replace('X', '.'),
                            (vx, vy), textcoords="offset points", xytext=(0, offset), ha='center',
                            fontsize=8, fontweight='bold', color=cor)

        # Ajuste Dinâmico do Eixo Y (Margem de Segurança)
        if todos_valores_y:
            max_y = max(todos_valores_y)
            min_y = min(todos_valores_y)
            amplitude = max_y - min_y
            if amplitude == 0:
                amplitude = abs(max_y) * 0.2 if max_y != 0 else 100

            margem_superior = max_y + (amplitude * 0.25)
            ax.set_ylim(top=margem_superior)

        # Formatação do Eixo Y (R$ K)
        def mil_format(x, pos=None):
            if abs(x) >= 1000:
                return f'R$ {x / 1000:,.1f}K'.replace(',', 'X').replace('.', ',').replace('X', '.')
            return f'R$ {x:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

        ax.yaxis.set_major_formatter(FuncFormatter(mil_format))

        # Títulos e Legendas
        titulo_final = " vs ".join(titulo_parts)
        if len(titulo_final) > 50:
            titulo_final = "Comparativo de Múltiplas Contas"

        ax.set_title(f"Evolução: {titulo_final}", fontsize=10, fontweight='bold', pad=40)
        ax.legend(loc='lower left', bbox_to_anchor=(0, 1.02), fontsize=8, ncol=2, frameon=True)

        ax.text(1.0, 1.05, 'R$ em Mil', transform=ax.transAxes,
                fontsize=10, verticalalignment='bottom', horizontalalignment='right',
                style='italic', color='#555555')

        ax.grid(True, linestyle=':', alpha=0.5)
        plt.xticks(rotation=45)

        # Renderização no Tkinter
        canvas_mc = FigureCanvasTkAgg(self.figura, master=self.frame_pai)
        canvas_mc.draw()
        canvas_mc.get_tk_widget().pack(fill="both", expand=True)

        return self.figura