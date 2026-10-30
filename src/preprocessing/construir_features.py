"""Base analítica: Gold + fontes externas, na granularidade município x rede x ano.

Saída: data/gold/painel_municipio_rede.parquet - uma linha por município/rede/ano
avaliado, com o resultado da avaliação (alunos, alfabetizados, taxa ponderada) e
todas as features de contexto. É a base da EDA, do modelo de municípios e a
tabela de features que é juntada aos alunos no modelo individual.

Regra anti-leakage temporal - cada fonte entra com a informação disponível
ANTES da avaliação daquele ano:

| Fonte                       | Avaliação 2023 | Avaliação 2024 | Por quê                                          |
|-----------------------------|----------------|----------------|--------------------------------------------------|
| Censo Escolar               | 2023           | 2024           | coletado em maio, a prova é em outubro/novembro  |
| Indicadores educacionais    | 2022           | 2022           | edição 2023 com colunas deslocadas na fonte      |
| INSE                        | 2021           | 2023           | edição publicada antes da avaliação              |
| PIB e população (IBGE)      | 2022           | 2023           | ano anterior                                     |
| Atlas IDHM                  | 2010           | 2010           | último Atlas municipal disponível                |
| Taxa do ano anterior        | -              | 2023           | só existe para 2024; não entra no modelo de aluno|

Uso:
    python -m src.preprocessing.construir_features
"""

import numpy as np
import pandas as pd

from src.config import DIR_GOLD, DIR_RAW

# Redes avaliadas: 2 = estadual, 3 = municipal (a rede 4 tem 25 alunos em um município).
REDES = {"2": "estadual", "3": "municipal"}

ANO_INDICADORES = {2023: 2022, 2024: 2022}
ANO_INSE = {2023: 2021, 2024: 2023}
ANO_IBGE = {2023: 2022, 2024: 2023}


def ler(nome: str, **kwargs) -> pd.DataFrame:
    return pd.read_parquet(DIR_RAW / f"{nome}.parquet", **kwargs)


def resultado_avaliacao() -> pd.DataFrame:
    """Alvo agregado por município/rede/ano, com a taxa ponderada por peso_aluno
    (a forma oficial do Inep - ver README)."""
    df = pd.read_parquet(
        DIR_GOLD / "alunos.parquet",
        columns=["ano", "id_municipio", "rede", "atingiu_ponto_corte", "peso_aluno"],
    )
    df = df[df["rede"].isin(REDES)]
    df["peso_alfabetizado"] = df["peso_aluno"] * df["atingiu_ponto_corte"]
    painel = (
        df.groupby(["ano", "id_municipio", "rede"])
        .agg(
            alunos_avaliados=("atingiu_ponto_corte", "size"),
            alunos_alfabetizados=("atingiu_ponto_corte", "sum"),
            soma_peso=("peso_aluno", "sum"),
            soma_peso_alfabetizado=("peso_alfabetizado", "sum"),
        )
        .reset_index()
    )
    painel["taxa_alfabetizacao"] = (painel["soma_peso_alfabetizado"] / painel["soma_peso"] * 100).round(2)
    return painel.drop(columns=["soma_peso", "soma_peso_alfabetizado"])


def _por_ano_avaliacao(df: pd.DataFrame, mapa_anos: dict[int, int]) -> pd.DataFrame:
    """Replica a fonte para cada ano de avaliação, usando o ano de referência do mapa."""
    partes = []
    for ano_avaliacao, ano_fonte in mapa_anos.items():
        parte = df[df["ano"] == ano_fonte].drop(columns="ano").copy()
        parte["ano"] = ano_avaliacao
        partes.append(parte)
    return pd.concat(partes, ignore_index=True)


def features_municipio_rede() -> pd.DataFrame:
    censo = ler("censo_municipio_rede")
    indicadores = _por_ano_avaliacao(ler("indicadores_municipio_rede"), ANO_INDICADORES)
    inse = _por_ano_avaliacao(ler("inse_municipio_rede"), ANO_INSE)

    chave = ["ano", "id_municipio", "rede"]
    return censo.merge(indicadores, on=chave, how="outer").merge(inse, on=chave, how="outer")


def features_municipio() -> pd.DataFrame:
    pib = ler("pib_municipio")
    populacao = ler("populacao_municipio")
    ibge = pib.merge(populacao, on=["ano", "id_municipio"], how="inner")
    ibge["pib_per_capita"] = ibge["pib"] / ibge["populacao"]
    ibge["log_populacao"] = np.log10(ibge["populacao"])
    ibge = _por_ano_avaliacao(ibge[["ano", "id_municipio", "pib_per_capita", "log_populacao"]], ANO_IBGE)

    adh = ler("adh_municipio")
    diretorio = ler("diretorio_municipio")[
        ["id_municipio", "nome", "sigla_uf", "nome_regiao", "capital_uf", "amazonia_legal"]
    ].rename(columns={"nome": "nome_municipio"})

    return ibge.merge(adh, on="id_municipio", how="left").merge(diretorio, on="id_municipio", how="left")


def construir() -> pd.DataFrame:
    painel = resultado_avaliacao()
    painel = painel.merge(features_municipio_rede(), on=["ano", "id_municipio", "rede"], how="left")
    painel = painel.merge(features_municipio(), on=["ano", "id_municipio"], how="left")
    painel["rede_nome"] = painel["rede"].map(REDES)

    # Taxa do mesmo município/rede no ano anterior - útil para prever metas
    # futuras, mas só existe para 2024 e por isso fica fora do modelo de aluno.
    anterior = painel[["ano", "id_municipio", "rede", "taxa_alfabetizacao"]].copy()
    anterior["ano"] += 1
    painel = painel.merge(
        anterior.rename(columns={"taxa_alfabetizacao": "taxa_ano_anterior"}),
        on=["ano", "id_municipio", "rede"], how="left",
    )

    for coluna in ["capital_uf", "amazonia_legal"]:
        painel[coluna] = painel[coluna].astype("float")
    painel = painel.sort_values(["ano", "id_municipio", "rede"]).reset_index(drop=True)

    destino = DIR_GOLD / "painel_municipio_rede.parquet"
    painel.to_parquet(destino, index=False)
    print(f"{destino.name}: {len(painel):,} linhas x {painel.shape[1]} colunas")
    print("\n% de valores ausentes por coluna (só as que têm algum):")
    ausentes = painel.isna().mean().mul(100).round(1)
    print(ausentes[ausentes > 0].sort_values(ascending=False).to_string())
    return painel


if __name__ == "__main__":
    construir()
