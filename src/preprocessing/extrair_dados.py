"""Camada Bronze local: baixa as tabelas originais da Base dos Dados (BigQuery).

Equivale ao `src/bronze/ingestao_bronze.py` da Fase 2, mas grava Parquet em
`data/raw/` em vez de tabelas Delta no Databricks. Os dados ficam exatamente
como vieram da fonte.

Autenticação: usa as credenciais padrão do Google (`gcloud auth
application-default login`), nunca uma chave dentro do repositório.

Uso:
    python -m src.preprocessing.extrair_dados            # baixa o que ainda não existe
    python -m src.preprocessing.extrair_dados --forcar   # baixa tudo de novo
"""

import argparse

from google.cloud import bigquery

from src.config import DIR_RAW, GCP_PROJECT_ID

# nome local -> consulta. As tabelas de diretório trazem só as colunas usadas
# (a de município tem uma coluna GEOGRAPHY que não precisamos).
CONSULTAS = {
    "uf": "SELECT * FROM `basedosdados.br_inep_avaliacao_alfabetizacao.uf`",
    "municipio": "SELECT * FROM `basedosdados.br_inep_avaliacao_alfabetizacao.municipio`",
    "meta_alfabetizacao_brasil": "SELECT * FROM `basedosdados.br_inep_avaliacao_alfabetizacao.meta_alfabetizacao_brasil`",
    "meta_alfabetizacao_uf": "SELECT * FROM `basedosdados.br_inep_avaliacao_alfabetizacao.meta_alfabetizacao_uf`",
    "meta_alfabetizacao_municipio": "SELECT * FROM `basedosdados.br_inep_avaliacao_alfabetizacao.meta_alfabetizacao_municipio`",
    "alunos": "SELECT * FROM `basedosdados.br_inep_avaliacao_alfabetizacao.alunos`",
    "diretorio_uf": "SELECT id_uf, sigla, nome, regiao FROM `basedosdados.br_bd_diretorios_brasil.uf`",
    "diretorio_municipio": """
        SELECT id_municipio, nome, capital_uf, sigla_uf, nome_uf, nome_regiao,
               id_regiao_imediata, nome_regiao_imediata, amazonia_legal
        FROM `basedosdados.br_bd_diretorios_brasil.municipio`
    """,
}


def extrair(forcar: bool = False) -> None:
    DIR_RAW.mkdir(parents=True, exist_ok=True)
    cliente = bigquery.Client(project=GCP_PROJECT_ID)

    for nome, consulta in CONSULTAS.items():
        destino = DIR_RAW / f"{nome}.parquet"
        if destino.exists() and not forcar:
            print(f"já existe, pulando: {destino.name}")
            continue

        print(f"baixando {nome}...")
        df = cliente.query(consulta).to_dataframe()
        df.to_parquet(destino, index=False)
        print(f"OK: {destino.name} ({len(df):,} linhas)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--forcar", action="store_true", help="baixa de novo mesmo se o arquivo já existir")
    extrair(parser.parse_args().forcar)
