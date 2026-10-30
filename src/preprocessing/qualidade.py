"""Checagens de qualidade - versão pandas de `quality/validacoes.py` da Fase 2.

Cada função devolve um dicionário (ou lista de dicionários) com o resultado,
que vira uma linha do relatório `data/gold/relatorio_qualidade.csv`.
"""

import pandas as pd


def checar_duplicidade(df: pd.DataFrame, colunas_chave: list[str], tabela: str) -> dict:
    duplicadas = int(df.duplicated(colunas_chave).sum())
    return {
        "tabela": tabela,
        "checagem": f"duplicidade {colunas_chave}",
        "passou": duplicadas == 0,
        "detalhe": f"{duplicadas} linha(s) duplicada(s)",
    }


def checar_valores_ausentes(df: pd.DataFrame, colunas: list[str], tabela: str) -> list[dict]:
    resultados = []
    for coluna in colunas:
        nulos = int(df[coluna].isna().sum())
        resultados.append({
            "tabela": tabela,
            "checagem": f"ausentes em {coluna}",
            "passou": nulos == 0,
            "detalhe": f"{nulos} valor(es) nulo(s)",
        })
    return resultados


def checar_chave_estrangeira(df: pd.DataFrame, df_referencia: pd.DataFrame, coluna: str, tabela: str) -> dict:
    orfaos = int((~df[coluna].isin(df_referencia[coluna])).sum())
    return {
        "tabela": tabela,
        "checagem": f"chave estrangeira {coluna}",
        "passou": orfaos == 0,
        "detalhe": f"{orfaos} linha(s) sem correspondência",
    }
