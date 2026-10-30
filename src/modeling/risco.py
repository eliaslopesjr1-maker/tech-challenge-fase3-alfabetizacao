"""Risco educacional por município (rede municipal).

Combina três sinais, todos em percentil (0 = menor risco, 1 = maior):
1. resultado atual: quanto menor a taxa de alfabetização observada, maior o risco
2. risco estrutural: taxa esperada pelo contexto, segundo o modelo do aluno
   (todos os alunos de uma rede recebem a mesma previsão, então ela é a taxa
   esperada daquela rede)
3. risco de meta: probabilidade de NÃO atingir a meta do próximo ano

O índice é a média dos três. Além dele, o ranking por número de crianças
não alfabetizadas mostra onde está o maior volume (impacto absoluto).
"""

import joblib
import pandas as pd

from src.config import DIR_MODELOS


def taxa_esperada_contexto(base: pd.DataFrame) -> pd.Series:
    artefato = joblib.load(DIR_MODELOS / "modelo_aluno_lgbm.joblib")
    colunas = artefato["numericas"] + artefato["categoricas"]
    proba = artefato["pipeline"].predict_proba(base[colunas])[:, 1]
    return pd.Series(proba * 100, index=base.index, name="taxa_esperada_contexto")


def indice_risco(base: pd.DataFrame, proba_atingir_meta: pd.Series) -> pd.DataFrame:
    df = base.copy()
    df["taxa_esperada_contexto"] = taxa_esperada_contexto(df)
    df["proba_nao_atingir_meta"] = 1 - proba_atingir_meta
    df["criancas_nao_alfabetizadas"] = (df["alunos_avaliados"] * (1 - df["taxa_alfabetizacao"] / 100)).round()

    componentes = {
        "risco_resultado": -df["taxa_alfabetizacao"],
        "risco_estrutural": -df["taxa_esperada_contexto"],
        "risco_meta": df["proba_nao_atingir_meta"],
    }
    for nome, valores in componentes.items():
        df[nome] = valores.rank(pct=True)
    df["indice_risco"] = df[list(componentes)].mean(axis=1)
    df["desvio_vs_esperado"] = df["taxa_alfabetizacao"] - df["taxa_esperada_contexto"]
    return df.sort_values("indice_risco", ascending=False)
