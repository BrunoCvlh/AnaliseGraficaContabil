import customtkinter as ctk


class LoadingPopup:
    def __init__(self, parent):
        self.parent = parent
        self.window = None

    def exibir(self):
        self.window = ctk.CTkToplevel(self.parent)
        self.window.title("Carregando...")
        self.window.geometry("300x120")
        self.window.resizable(False, False)

        # Centraliza
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - 150
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - 60
        self.window.geometry(f"+{x}+{y}")

        self.window.transient(self.parent)
        self.window.grab_set()

        ctk.CTkLabel(self.window, text="Processando dados...\nPor favor, aguarde.", font=("Arial", 14)).pack(pady=20)
        progress = ctk.CTkProgressBar(self.window, mode="indeterminate", width=200)
        progress.pack(pady=10)
        progress.start()

    def fechar(self):
        if self.window and self.window.winfo_exists():
            self.window.grab_release()
            self.window.destroy()


class GerenciadorFiltros:
    @staticmethod
    def criar_bloco(container, indice, callback_atualizar, callback_filtro_texto, lista_planos, lista_contas):
        frame_bloco = ctk.CTkFrame(container, fg_color="transparent")
        frame_bloco.pack(fill="x", pady=5)

        cores_labels = ["#3498db", "#e67e22", "#2ecc71", "#e74c3c"]
        cor_atual = cores_labels[(indice - 1) % 4]

        ctk.CTkLabel(frame_bloco, text=f"Série de Dados {indice}:", text_color=cor_atual,
                     font=("Arial", 12, "bold")).pack(pady=(5, 0))

        combo_plano = ctk.CTkComboBox(frame_bloco, values=lista_planos, command=lambda _: callback_atualizar(),
                                      width=220)
        combo_plano.set("Todos")
        combo_plano.pack(pady=5, padx=20)

        combo_conta = ctk.CTkComboBox(frame_bloco, values=lista_contas, command=lambda _: callback_atualizar(),
                                      width=220)
        combo_conta.pack(pady=5, padx=20)

        # Seta a primeira conta se disponível
        if lista_contas:
            combo_conta.set(lista_contas[0])

        combo_conta._entry.bind("<KeyRelease>", lambda event: callback_filtro_texto(combo_conta, event))

        return {
            "frame": frame_bloco,
            "plano": combo_plano,
            "conta": combo_conta
        }