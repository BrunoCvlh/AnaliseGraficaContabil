import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
# Módulos da Raiz (Modelos e Utilitários)
from logica import ProcessadorBalancete
from utilitarios import converter_csv_para_excel

# --- AQUI ESTÁ A MUDANÇA ---
# Importando os módulos de dentro da pasta 'views'
from views.graficos import GerenciadorGrafico
from views.relatorios import GeradorRelatorio
from views.componentes import LoadingPopup, GerenciadorFiltros

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class AppBalancete(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Análise de Balancete Contábil")
        self._configurar_janela()

        # Estado da Aplicação
        self.logica = ProcessadorBalancete()
        self.grafico_manager = None
        self.loading = LoadingPopup(self)
        self.blocos_filtros = []
        self.todas_contas = []

        self._setup_layout()
        self._setup_sidebar()
        self._setup_area_principal()

        # Adiciona o primeiro filtro obrigatoriamente
        self.adicionar_bloco_filtro()

    def _configurar_janela(self):
        screen_height = self.winfo_screenheight()
        if screen_height < 860:
            ctk.set_widget_scaling(0.85)
            ctk.set_window_scaling(0.85)
        self.after(0, lambda: self.state('zoomed'))

    def _setup_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.left_container = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.left_container.grid(row=0, column=0, sticky="nsew")
        self.left_container.grid_rowconfigure(0, weight=1)

    def _setup_sidebar(self):
        self.sidebar = ctk.CTkScrollableFrame(self.left_container, width=280, corner_radius=0, fg_color="transparent")
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(self.sidebar, text="MENU PRINCIPAL", font=("Arial", 20, "bold")).pack(pady=(20, 10))

        ctk.CTkButton(self.sidebar, text="Converter Balancete CSV", fg_color="#2c3e50",
                      command=self.acao_converter).pack(pady=5, padx=20)
        ctk.CTkButton(self.sidebar, text="Incluir Arquivo Excel", command=self.acao_upload).pack(pady=5, padx=20)
        ctk.CTkLabel(self.sidebar, text="---------------------------").pack(pady=5)

        # Container de Filtros
        self.container_filtros = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.container_filtros.pack(fill="x")

        # Botões + / -
        self.frame_botoes = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.frame_botoes.pack(pady=15)
        self.btn_add = ctk.CTkButton(self.frame_botoes, text="+", width=40, height=40, corner_radius=20,
                                     font=("Arial", 24, "bold"), fg_color="#2980b9", hover_color="#3498db",
                                     command=self.adicionar_bloco_filtro)
        self.btn_add.pack(side="left", padx=10)
        self.btn_remove = ctk.CTkButton(self.frame_botoes, text="-", width=40, height=40, corner_radius=20,
                                        font=("Arial", 24, "bold"), fg_color="#c0392b", hover_color="#e74c3c",
                                        command=self.remover_ultimo_bloco, state="disabled")
        self.btn_remove.pack(side="left", padx=10)

        ctk.CTkLabel(self.sidebar, text="---------------------------").pack(pady=5)

        # Datas
        ctk.CTkLabel(self.sidebar, text="Período (dd-mm-yyyy):", font=("Arial", 12, "bold")).pack(pady=(5, 0))
        self.frame_datas = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.frame_datas.pack(pady=5, padx=20)

        self.ent_data_inicio = ctk.CTkEntry(self.frame_datas, placeholder_text="01-01-2024", width=105)
        self.ent_data_inicio.pack(side="left", padx=(0, 10))
        self.ent_data_inicio.bind("<KeyRelease>", lambda e: self._formatar_data_entry(e, self.ent_data_inicio))

        self.ent_data_fim = ctk.CTkEntry(self.frame_datas, placeholder_text="31-12-2024", width=105)
        self.ent_data_fim.pack(side="left")
        self.ent_data_fim.bind("<KeyRelease>", lambda e: self._formatar_data_entry(e, self.ent_data_fim))

        ctk.CTkButton(self.sidebar, text="Aplicar Filtro", fg_color="#27ae60", command=self.atualizar_tela).pack(
            pady=10, padx=20)
        ctk.CTkButton(self.sidebar, text="Limpar Filtros", fg_color="#e74c3c", command=self.limpar_filtros).pack(pady=5,
                                                                                                                 padx=20)
        ctk.CTkButton(self.sidebar, text="Exportar Resumo (PDF)", fg_color="#8e44ad",
                      command=self.acao_exportar_pdf).pack(pady=5, padx=20)

        # Créditos
        ctk.CTkLabel(self.left_container, text="Desenvolvido pela GCO", font=("Arial", 10, "italic"),
                     fg_color="transparent").grid(row=1, column=0, pady=10, sticky="s")

    def _setup_area_principal(self):
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=3)
        self.main_frame.grid_rowconfigure(1, weight=2)

        self.graph_frame = ctk.CTkFrame(self.main_frame, fg_color="#F0F0F0")
        self.graph_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.grafico_manager = GerenciadorGrafico(self.graph_frame)

        self.txt_detalhamento = ctk.CTkTextbox(self.main_frame, font=("Courier New", 13))
        self.txt_detalhamento.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.txt_detalhamento.configure(state="disabled")

    # --- LÓGICA DE FILTROS ---
    def adicionar_bloco_filtro(self):
        if len(self.blocos_filtros) >= 4: return

        planos = ["Todos"] + self.logica.obter_lista_planos() if self.todas_contas else ["Todos"]

        bloco = GerenciadorFiltros.criar_bloco(
            self.container_filtros,
            len(self.blocos_filtros) + 1,
            self.atualizar_tela,
            self._filtrar_generico_evento,
            planos,
            self.todas_contas
        )
        self.blocos_filtros.append(bloco)
        self._atualizar_estado_botoes()

    def remover_ultimo_bloco(self):
        if len(self.blocos_filtros) > 1:
            bloco = self.blocos_filtros.pop()
            bloco["frame"].destroy()
            self._atualizar_estado_botoes()
            self.atualizar_tela()

    def _atualizar_estado_botoes(self):
        if hasattr(self, 'btn_remove'):
            state = "normal" if len(self.blocos_filtros) > 1 else "disabled"
            color = "#c0392b" if len(self.blocos_filtros) > 1 else "gray"
            self.btn_remove.configure(state=state, fg_color=color)

        if hasattr(self, 'btn_add'):
            state = "normal" if len(self.blocos_filtros) < 4 else "disabled"
            color = "#2980b9" if len(self.blocos_filtros) < 4 else "gray"
            self.btn_add.configure(state=state, fg_color=color)

    def _filtrar_generico_evento(self, widget, event):
        texto = widget.get().lower()
        valores = [i for i in self.todas_contas if texto in i.lower()] if texto else self.todas_contas
        widget.configure(values=valores)

    def limpar_filtros(self):
        while len(self.blocos_filtros) > 1:
            self.blocos_filtros.pop()["frame"].destroy()

        self.blocos_filtros[0]["plano"].set("Todos")
        self.ent_data_inicio.delete(0, 'end')
        self.ent_data_fim.delete(0, 'end')

        if self.todas_contas:
            self.blocos_filtros[0]["conta"].set(self.todas_contas[0])
            self.blocos_filtros[0]["conta"].configure(values=self.todas_contas)

        self._atualizar_estado_botoes()
        self.atualizar_tela()

    def _formatar_data_entry(self, event, widget):
        if event.keysym.lower() == "backspace": return
        texto = ''.join(filter(str.isdigit, widget.get()))[:8]
        novo = f"{texto[:2]}-{texto[2:4]}-{texto[4:]}" if len(texto) > 4 else f"{texto[:2]}-{texto[2:]}" if len(
            texto) > 2 else texto
        if widget.get() != novo:
            widget.delete(0, "end")
            widget.insert(0, novo)

    # --- AÇÕES E EVENTOS ---
    def acao_upload(self):
        caminho = filedialog.askopenfilename(filetypes=[("Arquivos de Dados", "*.xlsx *.xls *.csv")])
        if caminho:
            self.loading.exibir()
            threading.Thread(target=self._thread_carga, args=(caminho,)).start()

    def _thread_carga(self, caminho):
        try:
            self.logica.carregar_arquivo(caminho)
            self.after(0, self._pos_carga_sucesso)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erro", f"Falha: {e}") or self.loading.fechar())

    def _pos_carga_sucesso(self):
        self.loading.fechar()
        self.todas_contas = self.logica.obter_lista_contas_combinada()
        planos = ["Todos"] + self.logica.obter_lista_planos()

        for bloco in self.blocos_filtros:
            bloco["plano"].configure(values=planos)
            bloco["plano"].set("Todos")
            bloco["conta"].configure(values=self.todas_contas)
            if self.todas_contas: bloco["conta"].set(self.todas_contas[0])

        self.atualizar_tela()
        messagebox.showinfo("Sucesso", "Dados importados!")

    def acao_converter(self):
        caminho = filedialog.askopenfilename(filetypes=[("Arquivo CSV", "*.csv")])
        if caminho:
            ok, res = converter_csv_para_excel(caminho)
            msg = f"Salvo em: {os.path.basename(res)}" if ok else f"Erro: {res}"
            getattr(messagebox, "showinfo" if ok else "showerror")("Conversão", msg)

    def acao_exportar_pdf(self):
        texto = self.txt_detalhamento.get("1.0", "end")
        GeradorRelatorio.exportar_pdf(self.grafico_manager.figura, texto, self.ent_data_inicio.get(),
                                      self.ent_data_fim.get())

    def atualizar_tela(self, _=None):
        dados_processados = []
        d_ini, d_fim = self.ent_data_inicio.get(), self.ent_data_fim.get()

        for idx, bloco in enumerate(self.blocos_filtros):
            conta, plano = bloco["conta"].get(), bloco["plano"].get()
            if not conta: continue

            df = self.logica.filtrar_dados(conta, plano)
            if d_ini and d_fim:
                try:
                    df = self.logica.filtrar_por_periodo(df, d_ini, d_fim)
                except:
                    pass

            if not df.empty:
                dados_processados.append({"df": df, "conta": conta, "plano": plano, "indice": idx})

        if dados_processados:
            self.grafico_manager.desenhar(dados_processados)
            texto = GeradorRelatorio.gerar_texto_detalhado(dados_processados, self.logica, d_ini, d_fim)
            self.txt_detalhamento.configure(state="normal")
            self.txt_detalhamento.delete("1.0", "end")
            self.txt_detalhamento.insert("end", texto)
            self.txt_detalhamento.configure(state="disabled")
        else:
            self.txt_detalhamento.configure(state="normal")
            self.txt_detalhamento.delete("1.0", "end")
            self.txt_detalhamento.insert("end", "Nenhum dado encontrado.")
            self.txt_detalhamento.configure(state="disabled")
            for w in self.graph_frame.winfo_children(): w.destroy()


if __name__ == "__main__":
    app = AppBalancete()
    app.mainloop()