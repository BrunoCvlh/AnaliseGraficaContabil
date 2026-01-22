import customtkinter as ctk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
import io
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from logica import ProcessadorBalancete
from utilitarios import converter_csv_para_excel

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class AppBalancete(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Análise de Balancete Contábil")
        self.after(0, lambda: self.state('zoomed'))
        self.logica = ProcessadorBalancete()
        self.figura_atual = None  # Armazena a figura para exportação

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkScrollableFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(self.sidebar, text="MENU PRINCIPAL", font=("Arial", 20, "bold")).pack(pady=20)

        self.btn_convert = ctk.CTkButton(self.sidebar, text="Converter Balancete CSV", fg_color="#2c3e50",
                                         command=self.acao_converter)
        self.btn_convert.pack(pady=5, padx=20)

        self.btn_upload = ctk.CTkButton(self.sidebar, text="Incluir Arquivo Excel", command=self.acao_upload)
        self.btn_upload.pack(pady=5, padx=20)

        ctk.CTkLabel(self.sidebar, text="---------------------------").pack(pady=10)

        ctk.CTkLabel(self.sidebar, text="Selecionar Plano:").pack(pady=(5, 0))
        self.combo_planos = ctk.CTkComboBox(self.sidebar, values=[], command=lambda _: self.atualizar_tela(), width=220)
        self.combo_planos.pack(pady=10, padx=20)

        ctk.CTkLabel(self.sidebar, text="Pesquisar Código ou Nome:").pack(pady=(5, 0))
        self.combo_contas = ctk.CTkComboBox(self.sidebar, values=[], command=lambda _: self.atualizar_tela(), width=220)
        self.combo_contas.pack(pady=10, padx=20)

        ctk.CTkLabel(self.sidebar, text="Período (dd-mm-yyyy):", font=("Arial", 12, "bold")).pack(pady=(15, 0))
        self.ent_data_inicio = ctk.CTkEntry(self.sidebar, placeholder_text="Início: 01-01-2024")
        self.ent_data_inicio.pack(pady=5, padx=20)
        self.ent_data_fim = ctk.CTkEntry(self.sidebar, placeholder_text="Fim: 31-12-2024")
        self.ent_data_fim.pack(pady=5, padx=20)

        self.btn_filtrar_data = ctk.CTkButton(self.sidebar, text="Aplicar Filtro", fg_color="#27ae60",
                                              command=self.atualizar_tela)
        self.btn_filtrar_data.pack(pady=10, padx=20)

        self.btn_limpar = ctk.CTkButton(self.sidebar, text="Limpar Filtros", fg_color="#e74c3c",
                                        command=self.limpar_filtros)
        self.btn_limpar.pack(pady=5, padx=20)

        self.btn_exportar = ctk.CTkButton(self.sidebar, text="Exportar Resumo (PDF)", fg_color="#8e44ad",
                                          command=self.acao_exportar_pdf)
        self.btn_exportar.pack(pady=5, padx=20)

        self.lbl_creditos = ctk.CTkLabel(self, text="Desenvolvido pela GCO",
                                         font=("Arial", 10, "italic"),
                                         fg_color="transparent")
        self.lbl_creditos.place(relx=0.01, rely=0.99, anchor="sw")

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=3)
        self.main_frame.grid_rowconfigure(1, weight=2)

        self.graph_frame = ctk.CTkFrame(self.main_frame, fg_color="#F0F0F0")
        self.graph_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.txt_detalhamento = ctk.CTkTextbox(self.main_frame, font=("Courier New", 13))
        self.txt_detalhamento.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    def limpar_filtros(self):
        self.combo_planos.set("Todos")
        contas = self.logica.obter_lista_contas_combinada()
        if contas:
            self.combo_contas.set(contas[0])
            self.combo_contas.configure(values=contas)
        self.ent_data_inicio.delete(0, 'end')
        self.ent_data_fim.delete(0, 'end')
        self.atualizar_tela()

    def acao_upload(self):
        caminho = filedialog.askopenfilename(filetypes=[("Arquivos de Dados", "*.xlsx *.xls *.csv")])
        if caminho:
            try:
                self.logica.carregar_arquivo(caminho)
                contas_combinadas = self.logica.obter_lista_contas_combinada()
                self.combo_contas.configure(values=contas_combinadas)
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
            # Uso da figura armazenada para evitar o erro 'Canvas'
            buffer_img = io.BytesIO()
            self.figura_atual.savefig(buffer_img, format='png', bbox_inches='tight', dpi=150)
            buffer_img.seek(0)
            img_grafico = Image.open(buffer_img)

            c = canvas.Canvas(caminho_pdf, pagesize=A4)
            largura, altura = A4

            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, altura - 50, f"Relatório: {selecao}")
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
        selecao = self.combo_contas.get()
        plano = self.combo_planos.get()
        if not selecao: return

        df_f = self.logica.filtrar_dados(selecao, plano)
        d_ini = self.ent_data_inicio.get()
        d_fim = self.ent_data_fim.get()

        if d_ini and d_fim:
            try:
                df_f = self.logica.filtrar_por_periodo(df_f, d_ini, d_fim)
            except Exception as e:
                messagebox.showwarning("Aviso", str(e))
                return

        if not df_f.empty:
            self.desenhar_grafico(df_f)
            self.preencher_detalhes(df_f)
        else:
            self.txt_detalhamento.delete("1.0", "end")
            self.txt_detalhamento.insert("end", "Nenhum dado encontrado.")

    def desenhar_grafico(self, df_f):
        from matplotlib.ticker import FuncFormatter
        for w in self.graph_frame.winfo_children():
            w.destroy()

        plt.close('all')
        fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
        self.figura_atual = fig  # Armazena para exportação posterior
        fig.subplots_adjust(top=0.85)

        df_plot = df_f.sort_values(by=df_f.columns[0])
        x_data = df_plot.iloc[:, 0]
        y_data = df_plot.iloc[:, 8]

        ax.plot(x_data, y_data, marker='o', color='#1f77b4', linewidth=2)

        for x, y in zip(x_data, y_data):
            label_valor = y / 1000
            ax.annotate(f'{label_valor:,.1f}K'.replace(',', 'X').replace('.', ',').replace('X', '.'),
                        (x, y),
                        textcoords="offset points",
                        xytext=(0, 10),
                        ha='center',
                        fontsize=9,
                        fontweight='bold',
                        color='#2c3e50')

        def mil_format(x, pos=None):
            if abs(x) >= 1000:
                return f'R$ {x / 1000:,.1f}K'.replace(',', 'X').replace('.', ',').replace('X', '.')
            return f'R$ {x:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

        ax.yaxis.set_major_formatter(FuncFormatter(mil_format))
        ax.set_title(f"Evolução: {df_plot.iloc[0, 2]}", fontsize=11, fontweight='bold', pad=20)

        ax.text(1.0, 1.05, 'R$ em Mil', transform=ax.transAxes,
                fontsize=10, verticalalignment='bottom', horizontalalignment='right',
                style='italic', color='#555555')

        ax.grid(True, linestyle=':', alpha=0.5)
        plt.xticks(rotation=45)
        plt.tight_layout()

        canvas_mc = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas_mc.draw()
        canvas_mc.get_tk_widget().pack(fill="both", expand=True)

    def preencher_detalhes(self, df_f):
        self.txt_detalhamento.delete("1.0", "end")
        plano_ativo = self.combo_planos.get()
        d_ini = self.ent_data_inicio.get()
        d_fim = self.ent_data_fim.get()

        df_filhas = self.logica.obter_contas_filhas(df_f, plano_ativo, d_ini, d_fim)
        header = f"{'CÓDIGO (B)':<15} | {'NOME (C)':<25} | {'PLANO (K)':<18} | {'PERÍODO (A)':<12} | {'SALDO (I)':<15}\n"
        self.txt_detalhamento.insert("end", header + "-" * 110 + "\n")

        if df_filhas.empty:
            self.txt_detalhamento.insert("end", "Nenhuma subconta encontrada.")
        else:
            for _, row in df_filhas.iterrows():
                try:
                    periodo = row.iloc[0].strftime('%d/%m/%Y') if hasattr(row.iloc[0], 'strftime') else str(row.iloc[0])
                    valor = float(row.iloc[8])
                    saldo = f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    linha = f"{str(row.iloc[1]):<15} | {str(row.iloc[2])[:25]:<25} | {str(row.iloc[10])[:18]:<18} | {periodo:<12} | {saldo:<15}\n"
                    self.txt_detalhamento.insert("end", linha)
                except:
                    continue


if __name__ == "__main__":
    app = AppBalancete()
    app.mainloop()