import customtkinter as ctk
from tkinter import filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
import io
import threading  # Import necessário para não travar a tela
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
# Módulos do projeto
from logica import ProcessadorBalancete
from utilitarios import converter_csv_para_excel

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class AppBalancete(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Análise de Balancete Contábil")

        # 1. Ajuste Responsivo Automático
        screen_height = self.winfo_screenheight()
        if screen_height < 860:
            ctk.set_widget_scaling(0.85)
            ctk.set_window_scaling(0.85)

        self.after(0, lambda: self.state('zoomed'))
        self.logica = ProcessadorBalancete()
        self.figura_atual = None

        # Lista para armazenar dicionários dos filtros
        self.blocos_filtros = []
        self.todas_contas = []

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 2. Container Lateral (Estrutura Fixa)
        self.left_container = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.left_container.grid(row=0, column=0, sticky="nsew")
        self.left_container.grid_rowconfigure(0, weight=1)

        # Menu Rolável
        self.sidebar = ctk.CTkScrollableFrame(self.left_container, width=280, corner_radius=0, fg_color="transparent")
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # --- ITENS DO MENU ---
        pad_y_padrao = 5 if screen_height < 800 else 10

        ctk.CTkLabel(self.sidebar, text="MENU PRINCIPAL", font=("Arial", 20, "bold")).pack(pady=(20, 10))

        self.btn_convert = ctk.CTkButton(self.sidebar, text="Converter Balancete CSV", fg_color="#2c3e50",
                                         command=self.acao_converter)
        self.btn_convert.pack(pady=pad_y_padrao, padx=20)

        self.btn_upload = ctk.CTkButton(self.sidebar, text="Incluir Arquivo Excel", command=self.acao_upload)
        self.btn_upload.pack(pady=pad_y_padrao, padx=20)

        ctk.CTkLabel(self.sidebar, text="---------------------------").pack(pady=5)

        # === ÁREA DE FILTROS DINÂMICOS ===
        self.container_filtros = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.container_filtros.pack(fill="x")

        # Adiciona o primeiro bloco obrigatoriamente
        self.adicionar_bloco_filtro()

        # === BOTÕES DE CONTROLE (+ / -) ===
        self.frame_botoes = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.frame_botoes.pack(pady=15)

        # Botão Adicionar (+)
        self.btn_add = ctk.CTkButton(self.frame_botoes, text="+", width=40, height=40, corner_radius=20,
                                     font=("Arial", 24, "bold"), fg_color="#2980b9", hover_color="#3498db",
                                     command=self.adicionar_bloco_filtro)
        self.btn_add.pack(side="left", padx=10)

        # Botão Remover (-)
        self.btn_remove = ctk.CTkButton(self.frame_botoes, text="-", width=40, height=40, corner_radius=20,
                                        font=("Arial", 24, "bold"), fg_color="#c0392b", hover_color="#e74c3c",
                                        command=self.remover_ultimo_bloco)
        self.btn_remove.pack(side="left", padx=10)

        # Inicia desabilitado pois só tem 1 bloco
        self.btn_remove.configure(state="disabled", fg_color="gray")

        ctk.CTkLabel(self.sidebar, text="---------------------------").pack(pady=5)

        # === PERÍODO (LAYOUT LADO A LADO E MÁSCARA) ===
        ctk.CTkLabel(self.sidebar, text="Período (dd-mm-yyyy):", font=("Arial", 12, "bold")).pack(pady=(5, 0))

        # Container horizontal para as datas
        self.frame_datas = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.frame_datas.pack(pady=pad_y_padrao, padx=20)

        # Data Início
        self.ent_data_inicio = ctk.CTkEntry(self.frame_datas, placeholder_text="01-01-2024", width=105)
        self.ent_data_inicio.pack(side="left", padx=(0, 10))
        self.ent_data_inicio.bind("<KeyRelease>", lambda event: self._formatar_data_entry(event, self.ent_data_inicio))

        # Data Fim
        self.ent_data_fim = ctk.CTkEntry(self.frame_datas, placeholder_text="31-12-2024", width=105)
        self.ent_data_fim.pack(side="left")
        self.ent_data_fim.bind("<KeyRelease>", lambda event: self._formatar_data_entry(event, self.ent_data_fim))

        self.btn_filtrar_data = ctk.CTkButton(self.sidebar, text="Aplicar Filtro", fg_color="#27ae60",
                                              command=self.atualizar_tela)
        self.btn_filtrar_data.pack(pady=10, padx=20)

        self.btn_limpar = ctk.CTkButton(self.sidebar, text="Limpar Filtros", fg_color="#e74c3c",
                                        command=self.limpar_filtros)
        self.btn_limpar.pack(pady=pad_y_padrao, padx=20)

        self.btn_exportar = ctk.CTkButton(self.sidebar, text="Exportar Resumo (PDF)", fg_color="#8e44ad",
                                          command=self.acao_exportar_pdf)
        self.btn_exportar.pack(pady=pad_y_padrao, padx=20)

        # 3. Rodapé Fixo
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
        self.txt_detalhamento.configure(state="disabled")

    # --- FORMATACAO DATA ---
    def _formatar_data_entry(self, event, widget):
        if event.keysym.lower() == "backspace":
            return
        texto_atual = widget.get()
        apenas_numeros = ''.join(filter(str.isdigit, texto_atual))

        if len(apenas_numeros) > 8:
            apenas_numeros = apenas_numeros[:8]

        novo_texto = ""
        if len(apenas_numeros) > 4:
            novo_texto = f"{apenas_numeros[:2]}-{apenas_numeros[2:4]}-{apenas_numeros[4:]}"
        elif len(apenas_numeros) > 2:
            novo_texto = f"{apenas_numeros[:2]}-{apenas_numeros[2:]}"
        else:
            novo_texto = apenas_numeros

        if texto_atual != novo_texto:
            widget.delete(0, "end")
            widget.insert(0, novo_texto)

    # --- FILTROS DINAMICOS ---
    def adicionar_bloco_filtro(self):
        if len(self.blocos_filtros) >= 4:
            return

        indice = len(self.blocos_filtros) + 1

        frame_bloco = ctk.CTkFrame(self.container_filtros, fg_color="transparent")
        frame_bloco.pack(fill="x", pady=5)

        cores_labels = ["#3498db", "#e67e22", "#2ecc71", "#e74c3c"]
        cor_atual = cores_labels[indice - 1]

        lbl_titulo = ctk.CTkLabel(frame_bloco, text=f"Série de Dados {indice}:", text_color=cor_atual,
                                  font=("Arial", 12, "bold"))
        lbl_titulo.pack(pady=(5, 0))

        combo_plano = ctk.CTkComboBox(frame_bloco, values=["Todos"], command=lambda _: self.atualizar_tela(), width=220)
        combo_plano.set("Todos")
        combo_plano.pack(pady=5, padx=20)

        combo_conta = ctk.CTkComboBox(frame_bloco, values=[], command=lambda _: self.atualizar_tela(), width=220)
        combo_conta.pack(pady=5, padx=20)
        combo_conta._entry.bind("<KeyRelease>", lambda event, w=combo_conta: self._filtrar_generico(w, event))

        if self.todas_contas:
            planos = ["Todos"] + self.logica.obter_lista_planos()
            combo_plano.configure(values=planos)
            combo_conta.configure(values=self.todas_contas)
            if self.todas_contas:
                combo_conta.set(self.todas_contas[0])

        self.blocos_filtros.append({
            "frame": frame_bloco,
            "plano": combo_plano,
            "conta": combo_conta
        })

        if hasattr(self, 'btn_remove'):
            self.btn_remove.configure(state="normal", fg_color="#c0392b")

        if hasattr(self, 'btn_add'):
            if len(self.blocos_filtros) >= 4:
                self.btn_add.configure(state="disabled", fg_color="gray")

    def remover_ultimo_bloco(self):
        if len(self.blocos_filtros) > 1:
            bloco_removido = self.blocos_filtros.pop()
            bloco_removido["frame"].destroy()

            if hasattr(self, 'btn_add'):
                self.btn_add.configure(state="normal", fg_color="#2980b9")

            if len(self.blocos_filtros) == 1 and hasattr(self, 'btn_remove'):
                self.btn_remove.configure(state="disabled", fg_color="gray")

            self.atualizar_tela()

    def _filtrar_generico(self, widget_combo, event):
        texto = widget_combo.get().lower()
        if not self.todas_contas: return

        if texto == "":
            widget_combo.configure(values=self.todas_contas)
        else:
            filtrada = [i for i in self.todas_contas if texto in i.lower()]
            widget_combo.configure(values=filtrada)

    def limpar_filtros(self):
        while len(self.blocos_filtros) > 1:
            bloco = self.blocos_filtros.pop()
            bloco["frame"].destroy()

        primeiro_bloco = self.blocos_filtros[0]
        primeiro_bloco["plano"].set("Todos")

        if hasattr(self, 'btn_add'):
            self.btn_add.configure(state="normal", fg_color="#2980b9")
        if hasattr(self, 'btn_remove'):
            self.btn_remove.configure(state="disabled", fg_color="gray")

        contas = self.logica.obter_lista_contas_combinada()
        if contas:
            self.todas_contas = contas
            primeiro_bloco["conta"].set(contas[0])
            primeiro_bloco["conta"].configure(values=self.todas_contas)

        self.ent_data_inicio.delete(0, 'end')
        self.ent_data_fim.delete(0, 'end')
        self.atualizar_tela()

    # --- LOADING E THREADING ---

    def exibir_tela_carregamento(self):
        """Cria uma janela TopLevel para indicar carregamento"""
        self.loading_window = ctk.CTkToplevel(self)
        self.loading_window.title("Carregando...")
        self.loading_window.geometry("300x120")
        self.loading_window.resizable(False, False)

        # Tenta centralizar em relação à tela principal
        x = self.winfo_x() + (self.winfo_width() // 2) - 150
        y = self.winfo_y() + (self.winfo_height() // 2) - 60
        self.loading_window.geometry(f"+{x}+{y}")

        # Garante que a janela fique no topo e modal
        self.loading_window.transient(self)
        self.loading_window.grab_set()

        lbl_msg = ctk.CTkLabel(self.loading_window, text="Processando dados...\nPor favor, aguarde.",
                               font=("Arial", 14))
        lbl_msg.pack(pady=20)

        # Barra de progresso indeterminada
        progress = ctk.CTkProgressBar(self.loading_window, mode="indeterminate", width=200)
        progress.pack(pady=10)
        progress.start()

    def fechar_tela_carregamento(self):
        if hasattr(self, 'loading_window') and self.loading_window.winfo_exists():
            self.loading_window.grab_release()
            self.loading_window.destroy()

    def acao_upload(self):
        """Inicia o processo de upload com thread"""
        caminho = filedialog.askopenfilename(filetypes=[("Arquivos de Dados", "*.xlsx *.xls *.csv")])
        if caminho:
            self.exibir_tela_carregamento()
            # Inicia thread para não travar a GUI
            thread = threading.Thread(target=self._thread_carga, args=(caminho,))
            thread.start()

    def _thread_carga(self, caminho):
        """Executada em segundo plano"""
        try:
            self.logica.carregar_arquivo(caminho)
            # Agenda atualização da UI na thread principal
            self.after(0, self._pos_carga_sucesso)
        except Exception as e:
            # Agenda exibição do erro na thread principal
            self.after(0, lambda: self._pos_carga_erro(e))

    def _pos_carga_sucesso(self):
        """Atualiza a UI após sucesso"""
        self.fechar_tela_carregamento()
        try:
            self.todas_contas = self.logica.obter_lista_contas_combinada()
            lista_planos = ["Todos"] + self.logica.obter_lista_planos()

            for bloco in self.blocos_filtros:
                bloco["plano"].configure(values=lista_planos)
                bloco["plano"].set("Todos")
                bloco["conta"].configure(values=self.todas_contas)
                if self.todas_contas:
                    bloco["conta"].set(self.todas_contas[0])

            self.atualizar_tela()
            messagebox.showinfo("Sucesso", "Dados importados com sucesso!")
        except Exception as e:
            messagebox.showerror("Erro de UI", f"Erro ao atualizar interface: {e}")

    def _pos_carga_erro(self, erro):
        """Exibe erro após falha na thread"""
        self.fechar_tela_carregamento()
        messagebox.showerror("Erro", f"Falha ao carregar arquivo:\n{erro}")

    # --- FIM DO LOADING ---

    def acao_converter(self):
        caminho_csv = filedialog.askopenfilename(filetypes=[("Arquivo CSV", "*.csv")])
        if caminho_csv:
            sucesso, resultado = converter_csv_para_excel(caminho_csv)
            if sucesso:
                messagebox.showinfo("Sucesso", f"Salvo em Downloads:\n{os.path.basename(resultado)}")
            else:
                messagebox.showerror("Erro", f"Falha: {resultado}")

    def acao_exportar_pdf(self):
        if not self.figura_atual:
            messagebox.showwarning("Aviso", "Não há gráfico para exportar.")
            return

        pasta_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        nome_pdf = "Relatorio_Analise.pdf"
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

            info = f"Filtro Data: {self.ent_data_inicio.get()} a {self.ent_data_fim.get()}"
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
        dados_processados = []
        d_ini = self.ent_data_inicio.get()
        d_fim = self.ent_data_fim.get()

        for idx, bloco in enumerate(self.blocos_filtros):
            conta = bloco["conta"].get()
            plano = bloco["plano"].get()

            if not conta: continue

            df = self.logica.filtrar_dados(conta, plano)

            if d_ini and d_fim:
                try:
                    df = self.logica.filtrar_por_periodo(df, d_ini, d_fim)
                except Exception as e:
                    pass

            if not df.empty:
                dados_processados.append({
                    "df": df,
                    "conta": conta,
                    "plano": plano,
                    "indice": idx
                })

        if dados_processados:
            self.desenhar_grafico(dados_processados)
            self.preencher_detalhes(dados_processados)
        else:
            self.txt_detalhamento.configure(state="normal")
            self.txt_detalhamento.delete("1.0", "end")
            self.txt_detalhamento.insert("end", "Nenhum dado encontrado.")
            self.txt_detalhamento.configure(state="disabled")
            for w in self.graph_frame.winfo_children(): w.destroy()

    def desenhar_grafico(self, lista_dados):
        from matplotlib.ticker import FuncFormatter
        for w in self.graph_frame.winfo_children():
            w.destroy()

        plt.close('all')
        fig, ax = plt.subplots(figsize=(6, 4), dpi=100)
        self.figura_atual = fig

        # AJUSTE DE ESPAÇAMENTO DO GRÁFICO
        fig.subplots_adjust(top=0.75, bottom=0.20)

        cores = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        marcadores = ['o', 's', '^', 'D']

        titulo_parts = []

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

            legenda = f"{conta.split(' - ')[0]} ({plano})"
            titulo_parts.append(conta.split(' - ')[0])

            ax.plot(x, y, marker=marcador, color=cor, linewidth=2, label=legenda)

            offset = 10 if idx % 2 == 0 else -15
            for vx, vy in zip(x, y):
                label_valor = vy / 1000
                ax.annotate(f'{label_valor:,.1f}K'.replace(',', 'X').replace('.', ',').replace('X', '.'),
                            (vx, vy), textcoords="offset points", xytext=(0, offset), ha='center',
                            fontsize=8, fontweight='bold', color=cor)

        def mil_format(x, pos=None):
            if abs(x) >= 1000:
                return f'R$ {x / 1000:,.1f}K'.replace(',', 'X').replace('.', ',').replace('X', '.')
            return f'R$ {x:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

        ax.yaxis.set_major_formatter(FuncFormatter(mil_format))

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

        canvas_mc = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas_mc.draw()
        canvas_mc.get_tk_widget().pack(fill="both", expand=True)

    def preencher_detalhes(self, lista_dados):
        self.txt_detalhamento.configure(state="normal")
        self.txt_detalhamento.delete("1.0", "end")

        d_ini = self.ent_data_inicio.get()
        d_fim = self.ent_data_fim.get()
        header = f"{'CÓDIGO (B)':<25} | {'NOME (C)':<22} | {'PLANO':<10} | {'PERÍODO':<10} | {'SALDO (I)':<15} | {'% (P)':<10}\n"

        texto_acumulado = ""

        for item in lista_dados:
            df_alvo = item["df"]
            conta = item["conta"]
            plano = item["plano"]

            titulo_secao = f"CONTA: {conta.split(' - ')[0]} | PLANO: {plano}"
            texto_saida = f"\n=== {titulo_secao} ===\n"
            texto_saida += header + "-" * 115 + "\n"

            dict_valores_pai = df_alvo.groupby(df_alvo.columns[0])[df_alvo.columns[8]].sum().to_dict()
            df_filhas = self.logica.obter_contas_filhas(df_alvo, plano, d_ini, d_fim)

            if df_filhas.empty:
                texto_saida += "Nenhuma subconta encontrada.\n"
            else:
                df_filhas = df_filhas.sort_values(by=[df_filhas.columns[0], df_filhas.columns[1]])
                lista_codigos = [str(row.iloc[1]) for _, row in df_filhas.iterrows()]
                tamanhos = [len(c.rstrip('0')) for c in lista_codigos]
                min_len = min(tamanhos) if tamanhos else 0

                for _, row in df_filhas.iterrows():
                    try:
                        data_atual = row.iloc[0]
                        periodo = data_atual.strftime('%d/%m/%Y') if hasattr(data_atual, 'strftime') else str(
                            data_atual)
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

            texto_acumulado += texto_saida + "\n" + ("." * 115) + "\n"

        self.txt_detalhamento.insert("end", texto_acumulado)
        self.txt_detalhamento.configure(state="disabled")


if __name__ == "__main__":
    app = AppBalancete()
    app.mainloop()