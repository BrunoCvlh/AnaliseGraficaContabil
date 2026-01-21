import pandas as pd
import os
from pathlib import Path

def converter_csv_para_excel(caminho_csv):
    if not os.path.exists(caminho_csv):
        return False, "Arquivo de origem não encontrado."

    try:
        pasta_downloads = str(Path.home() / "Downloads")
        nome_base = os.path.basename(caminho_csv)
        nome_excel = os.path.splitext(nome_base)[0] + ".xlsx"
        caminho_saida = os.path.join(pasta_downloads, nome_excel)

        df = pd.read_csv(caminho_csv)
        df.to_excel(caminho_saida, index=False)

        return True, caminho_saida
    except Exception as e:
        return False, f"Erro na conversão: {str(e)}"