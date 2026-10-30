"""Gera a amostra versionada em data/amostra/ (~6 MB).

Permite abrir e executar os notebooks sem conta no Google Cloud:

    set TC_AMOSTRA=1          # Linux/Mac: export TC_AMOSTRA=1
    jupyter notebook notebooks/

O que vai na amostra:
- painel município x rede x ano e tabelas de metas/diretório: COMPLETOS (são pequenos)
- alunos: 60 mil por ano, sorteados com semente fixa
- predições do teste 2024: 60 mil alunos

Os resultados dos notebooks com a amostra são muito próximos aos da base completa;
as métricas oficiais (reports/) vêm da base completa.

Uso (a partir dos dados completos):
    python -m src.preprocessing.gerar_amostra
"""

import shutil

import pandas as pd

from src.config import DIR_AMOSTRA, DIR_DADOS, SEED

ALUNOS_POR_ANO = 60_000
RAW_COMPLETOS = ["meta_alfabetizacao_brasil", "meta_alfabetizacao_municipio", "diretorio_municipio"]
GOLD_COMPLETOS = ["painel_municipio_rede", "indicador_brasil", "indicador_uf"]


def gerar() -> None:
    origem_raw, origem_gold = DIR_DADOS / "raw", DIR_DADOS / "gold"
    destino_raw, destino_gold = DIR_AMOSTRA / "raw", DIR_AMOSTRA / "gold"
    destino_raw.mkdir(parents=True, exist_ok=True)
    destino_gold.mkdir(parents=True, exist_ok=True)

    for nome in RAW_COMPLETOS:
        shutil.copy(origem_raw / f"{nome}.parquet", destino_raw)
    for nome in GOLD_COMPLETOS:
        shutil.copy(origem_gold / f"{nome}.parquet", destino_gold)

    alunos = pd.read_parquet(origem_gold / "alunos.parquet", columns=[
        "ano", "id_municipio", "id_aluno", "rede", "proficiencia", "atingiu_ponto_corte", "peso_aluno",
        "sigla_uf", "nome_regiao",
    ])
    amostra = alunos.groupby("ano").sample(n=ALUNOS_POR_ANO, random_state=SEED)
    amostra.drop(columns="id_aluno").to_parquet(destino_gold / "alunos.parquet", index=False)

    # Bronze de alunos (usada só no resumo de ausentes da EDA): mesmos alunos + uma
    # amostra proporcional dos ausentes, que não chegam à Gold.
    bruta = pd.read_parquet(origem_raw / "alunos.parquet", columns=["ano", "id_aluno", "presenca", "proficiencia"])
    presentes = bruta[bruta["id_aluno"].isin(amostra["id_aluno"])]
    fracao = ALUNOS_POR_ANO / alunos.groupby("ano").size()
    ausentes = pd.concat([
        grupo.sample(frac=fracao[ano], random_state=SEED)
        for ano, grupo in bruta[bruta["proficiencia"].isna()].groupby("ano")
    ])
    pd.concat([presentes, ausentes]).drop(columns="id_aluno").to_parquet(destino_raw / "alunos.parquet", index=False)

    predicoes = pd.read_parquet(origem_gold / "predicoes_aluno_2024.parquet")
    predicoes.sample(n=ALUNOS_POR_ANO, random_state=SEED).to_parquet(
        destino_gold / "predicoes_aluno_2024.parquet", index=False)

    tamanho = sum(arquivo.stat().st_size for arquivo in DIR_AMOSTRA.rglob("*.parquet")) / 1e6
    print(f"amostra gerada em {DIR_AMOSTRA} ({tamanho:.1f} MB)")


if __name__ == "__main__":
    gerar()
