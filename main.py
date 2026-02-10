import pandas as pd
import json

df = pd.read_excel("base.xlsx")

with open("de_para.json", "r", encoding="utf-8") as f:
    config = json.load(f)

def classificar_baremo(linha, regras, prioridade):
    for coluna in prioridade:
        texto = linha.get(coluna)

        if pd.isna(texto):
            continue

        texto = str(texto).lower()

        for regra in regras.get(coluna, []):
            if regra["palavra"].lower() in texto:
                return (
                    regra["baremo"],
                    regra["resultado"],
                    coluna,
                    regra["palavra"]
                )

    return "SEM_BAREMO", "NAO_CLASSIFICADO", None, None


df[["BAREMO_FINAL", "RESULTADO", "ORIGEM", "PALAVRA_CHAVE"]] = df.apply(
    lambda linha: pd.Series(
        classificar_baremo(
            linha,
            config["regras"],
            config["prioridade"]
        )
    ),
    axis=1
)


