import io
import os
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from tkinter import messagebox


class GeradorRelatorio:
    @staticmethod
    def gerar_texto_detalhado(lista_dados, logica_app, d_ini, d_fim):
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
            df_filhas = logica_app.obter_contas_filhas(df_alvo, plano, d_ini, d_fim)

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

        return texto_acumulado

    @staticmethod
    def exportar_pdf(figura, texto_detalhado, d_ini, d_fim):
        if not figura:
            messagebox.showwarning("Aviso", "Não há gráfico para exportar.")
            return

        pasta_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        nome_pdf = "Relatorio_Analise.pdf"
        caminho_pdf = os.path.join(pasta_downloads, nome_pdf)

        try:
            buffer_img = io.BytesIO()
            figura.savefig(buffer_img, format='png', bbox_inches='tight', dpi=150)
            buffer_img.seek(0)
            img_grafico = Image.open(buffer_img)

            c = canvas.Canvas(caminho_pdf, pagesize=A4)
            largura, altura = A4

            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, altura - 50, f"Relatório de Análise")
            c.setFont("Helvetica", 10)

            info = f"Filtro Data: {d_ini} a {d_fim}"
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
            linhas = texto_detalhado.split('\n')
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