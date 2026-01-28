import customtkinter as ctk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
import io
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
# Supondo que estes módulos existam no seu projeto
from logica import ProcessadorBalancete
from utilitarios import converter_csv_para_excel

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class AppBalancete(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Análise de Balancete Contábil")

        # 1. Ajuste Responsivo Automático
        # Se a altura da tela for de notebook (geralmente < 800px), reduz a escala dos widgets em 15%
        screen_height = self.winfo_screenheight()
        if screen_height < 860:
            ctk.set_widget_scaling(0.85)
            ctk.set_window_scaling(0.85)

        self.after(0, lambda: self.state('zoomed'))
        self.logica = ProcessadorBalancete()
        self.figura_atual = None
        self.todas_contas = []

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 2. Container Lateral (Estrutura Fixa)
        # Substituímos o sidebar direto por um Frame Container para dividir Menu e Rodapé
        self.left_container = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.left_container.grid(row=0, column=0, sticky="nsew")

        # O menu ocupa todo o espaço disponível (weight=1), empurrando o rodapé para baixo
        self.left_container.grid_rowconfigure(0, weight=1)
        self.left_container.grid_rowconfigure(1, weight=0)

        # Menu Rolável (Fica na linha 0 do container)
        self.sidebar = ctk.CTkScrollableFrame(self.left_container, width=280, corner_radius=0, fg_color="transparent")
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # --- ITENS DO MENU (Com pady reduzido para telas menores) ---
        pad_y_padrao = 5 if screen_height < 800 else 10  # Padding dinâmico

        ctk.CTkLabel(self.sidebar, text="MENU PRINCIPAL", font=("Arial", 20, "bold")).pack(pady=(20, 10))

        self.btn_convert = ctk.CTkButton(self.sidebar, text="Converter Balancete CSV", fg_color="#2c3e50",
                                         command=self.acao_converter)
        self.btn_convert.pack(pady=pad_y_padrao, padx=20)

        self.btn_upload = ctk.CTkButton(self.sidebar, text="Incluir Arquivo Excel", command=self.acao_upload)
        self.btn_upload.pack(pady=pad_y_padrao, padx=20)

        ctk.CTkLabel(self.sidebar, text="---------------------------").pack(pady=5)

        ctk.CTkLabel(self.sidebar, text="Selecionar Plano:").pack(pady=(5, 0))
        self.combo_planos = ctk.CTkComboBox(self.sidebar, values=[], command=lambda _: self.atualizar_tela(), width=220)
        self.combo_planos.pack(pady=pad_y_padrao, padx=20)

        ctk.CTkLabel(self.sidebar, text="Conta Principal:").pack(pady=(5, 0))
        self.combo_contas = ctk.CTkComboBox(self.sidebar, values=[], command=lambda _: self.atualizar_tela(), width=220)
        self.combo_contas.pack(pady=pad_y_padrao, padx=20)
        self.combo_contas._entry.bind("<KeyRelease>", self.filtrar_combo_contas)

        ctk.CTkLabel(self.sidebar, text="Comparar com (Opcional):").pack(pady=(5, 0))
        self.combo_contas_2 = ctk.CTkComboBox(self.sidebar, values=[], command=lambda _: self.atualizar_tela(),
                                              width=220)
        self.combo_contas_2.set("")
        self.combo_contas_2.pack(pady=pad_y_padrao, padx=20)
        self.combo_contas_2._entry.bind("<KeyRelease>", self.filtrar_combo_contas_2)

        ctk.CTkLabel(self.sidebar, text="Período (dd-mm-yyyy):", font=("Arial", 12, "bold")).pack(pady=(10, 0))
        self.ent_data_inicio = ctk.CTkEntry(self.sidebar, placeholder_text="Início: 01-01-2024")
        self.ent_data_inicio.pack(pady=pad_y_padrao, padx=20)
        self.ent_data_fim = ctk.CTkEntry(self.sidebar, placeholder_text="Fim: 31-12-2024")
        self.ent_data_fim.pack(pady=pad_y_padrao, padx=20)

        self.btn_filtrar_data = ctk.CTkButton(self.sidebar, text="Aplicar Filtro", fg_color="#27ae60",
                                              command=self.atualizar_tela)
        self.btn_filtrar_data.pack(pady=10, padx=20)  # Botões de ação mantêm destaque

        self.btn_limpar = ctk.CTkButton(self.sidebar, text="Limpar Filtros", fg_color="#e74c3c",
                                        command=self.limpar_filtros)
        self.btn_limpar.pack(pady=pad_y_padrao, padx=20)

        self.btn_exportar = ctk.CTkButton(self.sidebar, text="Exportar Resumo (PDF)", fg_color="#8e44ad",
                                          command=self.acao_exportar_pdf)
        self.btn_exportar.pack(pady=pad_y_padrao, padx=20)

        # 3. Rodapé Fixo (Linha 1 do Container)
        # Ao usar grid no container, ele nunca sobrepõe o menu, nem quando a tela encolhe
        self.lbl_creditos = ctk.CTkLabel(self.left_container, text="Desenvolvido pela GCO",
                                         font=("Arial", 10, "italic"),
                                         fg_color="transparent")
        self.lbl_creditos.grid(row=1, column=0, pady=10, sticky="s")

        # --- ÁREA PRINCIPAL ---
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=3)
        self.main_frame.grid_rowconfigure(1, weight=2)

        self.graph_frame = ctk.CTkFrame(self.main_frame, fg_color="#F0F0F0")
        self.graph_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.txt_detalhamento = ctk.CTkTextbox(self.main_frame, font=("Courier New", 13))
        self.txt_detalhamento.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    def filtrar_combo_contas(self, event):
        self._filtrar_generico(self.combo_contas)

    def filtrar_combo_contas_2(self, event):
        self._filtrar_generico(self.combo_contas_2)

    def _filtrar_generico(self, widget_combo):
        texto = widget_combo.get().lower()
        if not self.todas_contas: return

        if texto == "":
            widget_combo.configure(values=self.todas_contas)
        else:
            filtrada = [i for i in self.todas_contas if texto in i.lower()]
            widget_combo.configure(values=filtrada)

    def limpar_filtros(self):
        self.combo_planos.set("Todos")
        contas = self.logica.obter_lista_contas_combinada()
        if contas:
            self.todas_contas = contas
            self.combo_contas.set(contas[0])
            self.combo_contas.configure(values=self.todas_contas)
            self.combo_contas_2.set("")
            self.combo_contas_2.configure(values=self.todas_contas)

        self.ent_data_inicio.delete(0, 'end')
        self.ent_data_fim.delete(0, 'end')
        self.atualizar_tela()

    def acao_upload(self):
        caminho = filedialog.askopenfilename(filetypes=[("Arquivos de Dados", "*.xlsx *.xls *.csv")])
        if caminho:
            try:
                self.logica.carregar_arquivo(caminho)
                contas_combinadas = self.logica.obter_lista_contas_combinada()

                self.todas_contas = contas_combinadas

                self.combo_contas.configure(values=self.todas_contas)
                self.combo_contas_2.configure(values=self.todas_contas)
                self.combo_contas_2.set("")

                planos = ["Todos"] + self.logica.obter_lista_planos()
                self.combo_planos.configure(values=planos)

                if contas_combinadas:
                    self.combo_contas.set(contas_combinadas[0])
                    self.combo_planos.set("Todos")
                    self.atualizar_tela()
                messagebox.showinfo("Sucesso", "Dados importados!")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro: {e}")

    def acao_converter(self):
        caminho_csv = filedialog.askopenfilename(filetypes=[("Arquivo CSV", "*.csv")])
        if caminho_csv:
            sucesso, resultado = converter_csv_para_excel(caminho_csv)
            if sucesso:
                messagebox.showinfo("Sucesso", f"Salvo em Downloads:\n{os.path.basename(resultado)}")
            else:
                messagebox.showerror("Erro", f"Falha: {resultado}")

    def acao_exportar_pdf(self):
        selecao = self.combo_contas.get()
        if not selecao or not self.figura_atual:
            messagebox.showwarning("Aviso", "Não há dados ou gráfico para exportar.")
            return

        pasta_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        nome_pdf = f"Resumo_{selecao.split(' - ')[0]}.pdf"
        caminho_pdf = os.path.join(pasta_downloads, nome_pdf)

        try:
            buffer_img = io.BytesIO()
            self.figura_atual.savefig(buffer_img, format='png', bbox_inches='tight', dpi=150)
            buffer_img.seek(0)
            img_grafico = Image.open(buffer_img)

            c = canvas.Canvas(caminho_pdf, pagesize=A4)
            largura, altura = A4

            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, altura - 50, f"Relatório de Análise")
            c.setFont("Helvetica", 10)
            info = f"Plano: {self.combo_planos.get()} | Filtro: {self.ent_data_inicio.get()} a {self.ent_data_fim.get()}"
            c.drawString(50, altura - 65, info)
            c.line(50, altura - 70, largura - 50, altura - 70)

            img_w, img_h = img_grafico.size
            aspect = img_h / float(img_w)
            larg_disp = largura - 100
            alt_disp = larg_disp * aspect
            c.drawInlineImage(img_grafico, 50, altura - 80 - alt_disp, width=larg_disp, height=alt_disp)

            y_pos = altura - 100 - alt_disp
            c.setFont("Courier-Bold", 10)
            c.drawString(50, y_pos, "DETALHAMENTO:")
            y_pos -= 20

            c.setFont("Courier", 8)
            linhas = self.txt_detalhamento.get("1.0", "end").split('\n')
            for linha in linhas:
                if y_pos < 50:
                    c.showPage()
                    y_pos = altura - 50
                    c.setFont("Courier", 8)
                c.drawString(50, y_pos, linha)
                y_pos -= 12

            c.save()
            messagebox.showinfo("Sucesso", f"PDF gerado em Downloads:\n{nome_pdf}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao exportar PDF: {e}")

    def atualizar_tela(self, _=None):
        selecao1 = self.combo_contas.get()
        selecao2 = self.combo_contas_2.get()
        plano = self.combo_planos.get()

        if not selecao1: return

        df1 = self.logica.filtrar_dados(selecao1, plano)

        df2 = None
        if selecao2 and selecao2 in self.todas_contas and selecao2 != "":
            df2 = self.logica.filtrar_dados(selecao2, plano)

        d_ini = self.ent_data_inicio.get()
        d_fim = self.ent_data_fim.get()

        if d_ini and d_fim:
            try:
                df1 = self.logica.filtrar_por_periodo(df1, d_ini, d_fim)
                if df2 is not None:
                    df2 = self.logica.filtrar_por_periodo(df2, d_ini, d_fim)
            except Exception as e:
                messagebox.showwarning("Aviso", str(e))
                return

        if not df1.empty:
            self.desenhar_grafico(df1, df2, selecao1, selecao2)
            self.preencher_detalhes(df1, df2)
        else:
            self.txt_detalhamento.delete("1.0", "end")
            self.txt_detalhamento.insert("end", "Nenhum dado encontrado.")

    def desenhar_grafico(self, df1, df2=None, nome1="", nome2=""):
        from matplotlib.ticker import FuncFormatter
        for w in self.graph_frame.winfo_children():
            w.destroy()

        plt.close('all')
        fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
        self.figura_atual = fig
        fig.subplots_adjust(top=0.85)

        df_plot1 = df1.sort_values(by=df1.columns[0])
        x1 = df_plot1.iloc[:, 0]
        y1 = df_plot1.iloc[:, 8]

        line1, = ax.plot(x1, y1, marker='o', color='#1f77b4', linewidth=2, label=nome1.split(' - ')[0])

        for x, y in zip(x1, y1):
            label_valor = y / 1000
            ax.annotate(f'{label_valor:,.1f}K'.replace(',', 'X').replace('.', ',').replace('X', '.'),
                        (x, y), textcoords="offset points", xytext=(0, 10), ha='center',
                        fontsize=9, fontweight='bold', color='#1f77b4')

        if df2 is not None and not df2.empty:
            df_plot2 = df2.sort_values(by=df2.columns[0])
            x2 = df_plot2.iloc[:, 0]
            y2 = df_plot2.iloc[:, 8]

            line2, = ax.plot(x2, y2, marker='s', color='#ff7f0e', linewidth=2, label=nome2.split(' - ')[0])

            for x, y in zip(x2, y2):
                label_valor = y / 1000
                ax.annotate(f'{label_valor:,.1f}K'.replace(',', 'X').replace('.', ',').replace('X', '.'),
                            (x, y), textcoords="offset points", xytext=(0, -15), ha='center',
                            fontsize=9, fontweight='bold', color='#ff7f0e')

        def mil_format(x, pos=None):
            if abs(x) >= 1000:
                return f'R$ {x / 1000:,.1f}K'.replace(',', 'X').replace('.', ',').replace('X', '.')
            return f'R$ {x:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

        ax.yaxis.set_major_formatter(FuncFormatter(mil_format))

        titulo = f"Evolução: {df_plot1.iloc[0, 2]}"
        if df2 is not None and not df2.empty:
            titulo += "  vs  " + df_plot2.iloc[0, 2]

        ax.set_title(titulo, fontsize=10, fontweight='bold', pad=20)
        ax.legend(loc='upper left', fontsize=8)

        ax.text(1.0, 1.05, 'R$ em Mil', transform=ax.transAxes,
                fontsize=10, verticalalignment='bottom', horizontalalignment='right',
                style='italic', color='#555555')

        ax.grid(True, linestyle=':', alpha=0.5)
        plt.xticks(rotation=45)
        plt.tight_layout()

        canvas_mc = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas_mc.draw()
        canvas_mc.get_tk_widget().pack(fill="both", expand=True)

    def preencher_detalhes(self, df1, df2=None):
        self.txt_detalhamento.delete("1.0", "end")

        plano_ativo = self.combo_planos.get()
        d_ini = self.ent_data_inicio.get()
        d_fim = self.ent_data_fim.get()

        header = f"{'CÓDIGO (B)':<25} | {'NOME (C)':<22} | {'PLANO':<10} | {'PERÍODO':<10} | {'SALDO (I)':<15} | {'% (P)':<10}\n"

        def _gerar_bloco_texto(df_alvo, titulo_secao):
            texto_saida = f"\n=== {titulo_secao} ===\n"
            texto_saida += header + "-" * 115 + "\n"

            if df_alvo.empty:
                return texto_saida + "Nenhum dado para esta conta.\n"

            dict_valores_pai = df_alvo.groupby(df_alvo.columns[0])[df_alvo.columns[8]].sum().to_dict()

            df_filhas = self.logica.obter_contas_filhas(df_alvo, plano_ativo, d_ini, d_fim)

            if df_filhas.empty:
                return texto_saida + "Nenhuma subconta encontrada.\n"

            df_filhas = df_filhas.sort_values(by=[df_filhas.columns[0], df_filhas.columns[1]])

            lista_codigos = [str(row.iloc[1]) for _, row in df_filhas.iterrows()]
            tamanhos = [len(c.rstrip('0')) for c in lista_codigos]
            min_len = min(tamanhos) if tamanhos else 0

            for _, row in df_filhas.iterrows():
                try:
                    data_atual = row.iloc[0]
                    periodo = data_atual.strftime('%d/%m/%Y') if hasattr(data_atual, 'strftime') else str(data_atual)
                    valor = float(row.iloc[8])
                    saldo = f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

                    valor_pai_periodo = dict_valores_pai.get(data_atual, 0)

                    percentual = 0.0
                    if valor_pai_periodo != 0:
                        percentual = (valor / valor_pai_periodo) * 100
                    str_perc = f"{percentual:,.2f}%".replace('.', ',')

                    codigo_original = str(row.iloc[1])
                    tamanho_atual = len(codigo_original.rstrip('0'))
                    qtde_espacos = (tamanho_atual - min_len)
                    espacos = " " * qtde_espacos
                    codigo_visual = f"{espacos}{codigo_original}"

                    linha = f"{codigo_visual:<25} | {str(row.iloc[2])[:22]:<22} | {str(row.iloc[10])[:10]:<10} | {periodo:<10} | {saldo:<15} | {str_perc:<10}\n"
                    texto_saida += linha
                except:
                    continue
            return texto_saida

        texto_final = _gerar_bloco_texto(df1, f"PRINCIPAL: {self.combo_contas.get().split(' - ')[0]}")

        if df2 is not None and not df2.empty:
            texto_final += "\n" + ("." * 115) + "\n"
            texto_final += _gerar_bloco_texto(df2, f"COMPARATIVO: {self.combo_contas_2.get().split(' - ')[0]}")

        self.txt_detalhamento.insert("end", texto_final)


if __name__ == "__main__":
    app = AppBalancete()
    app.mainloop()