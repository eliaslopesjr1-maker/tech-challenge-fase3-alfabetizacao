"""Silver + Gold locais: reproduz em pandas as regras da Fase 2.

Equivale a `src/silver/tratamento_silver.py` + `src/gold/indicador_alfabetizacao_gold.py`
do repositório da Fase 2. A única diferença de regra é que a parte de streaming
(eventos simulados) não é reproduzida: a Gold é calculada só sobre os dados reais
da Base dos Dados.

Entradas: data/raw/*.parquet (gerados por extrair_dados.py)
Saídas:   data/gold/{alunos, indicador_municipio, indicador_uf, indicador_brasil,
          comparacao_meta_resultado}.parquet

Uso:
    python -m src.preprocessing.construir_gold
"""

import pandas as pd

from src.config import ANOS_META, DIR_GOLD, DIR_RAW, PONTO_DE_CORTE_ALFABETIZACAO
from src.preprocessing.qualidade import checar_chave_estrangeira, checar_duplicidade, checar_valores_ausentes


def ler(nome: str) -> pd.DataFrame:
    return pd.read_parquet(DIR_RAW / f"{nome}.parquet")


# ---------------------------------------------------------------------------
# Silver
# ---------------------------------------------------------------------------

def silver_diretorio_municipio() -> pd.DataFrame:
    return ler("diretorio_municipio").rename(columns={"nome": "nome_municipio"})


def silver_municipio(df_dir_municipio: pd.DataFrame) -> pd.DataFrame:
    """Indicador oficial por município (publicado pelo Inep) + nome/UF/região."""
    df = ler("municipio").drop_duplicates(["id_municipio", "ano", "rede", "serie"])
    colunas_dir = ["id_municipio", "nome_municipio", "sigla_uf", "nome_uf", "nome_regiao"]
    return df.merge(df_dir_municipio[colunas_dir], on="id_municipio", how="left")


def manter_edicao_mais_recente(df: pd.DataFrame, colunas_chave: list[str]) -> pd.DataFrame:
    """A fonte publica mais de uma edição da meta (2023 e 2024) para o mesmo
    local/rede - fica só a mais recente, como na Fase 2."""
    return (
        df.sort_values("ano", ascending=False)
        .drop_duplicates(colunas_chave + ["rede"], keep="first")
    )


def desempilhar_metas(df: pd.DataFrame, abrangencia: str, colunas_chave: list[str]) -> pd.DataFrame:
    """Transforma meta_alfabetizacao_2024..2030 em uma linha por ano_meta."""
    df = manter_edicao_mais_recente(df, colunas_chave)
    colunas_meta = [f"meta_alfabetizacao_{ano}" for ano in ANOS_META]
    df = df.melt(
        id_vars=colunas_chave + ["ano", "rede", "taxa_alfabetizacao"],
        value_vars=colunas_meta,
        var_name="ano_meta",
        value_name="meta_percentual",
    )
    df["ano_meta"] = df["ano_meta"].str.split("_").str[-1].astype(int)
    df["abrangencia"] = abrangencia
    return df


def silver_metas() -> pd.DataFrame:
    return pd.concat(
        [
            desempilhar_metas(ler("meta_alfabetizacao_brasil"), "brasil", []),
            desempilhar_metas(ler("meta_alfabetizacao_uf"), "uf", ["sigla_uf"]),
            desempilhar_metas(ler("meta_alfabetizacao_municipio"), "municipio", ["id_municipio"]),
        ],
        ignore_index=True,
    ).drop_duplicates()


def silver_alunos() -> pd.DataFrame:
    """Descarta quem não tem proficiência (faltou ou não preencheu o caderno),
    deduplica aluno/ano de forma determinística e aplica o ponto de corte."""
    df = ler("alunos")
    df["proficiencia"] = pd.to_numeric(df["proficiencia"], errors="coerce")
    qtd_antes = len(df)

    df = (
        df[df["proficiencia"].notna()]
        .sort_values(["peso_aluno", "proficiencia"], ascending=False, na_position="last")
        .drop_duplicates(["id_aluno", "ano"], keep="first")
        .sort_values(["ano", "id_municipio", "id_escola", "id_aluno"])
        .reset_index(drop=True)
    )
    df["atingiu_ponto_corte"] = df["proficiencia"] >= PONTO_DE_CORTE_ALFABETIZACAO

    print(f"alunos: {qtd_antes:,} linhas na Bronze -> {len(df):,} na Silver "
          f"({qtd_antes - len(df):,} descartadas por duplicidade ou falta de nota)")
    return df


# ---------------------------------------------------------------------------
# Gold
# ---------------------------------------------------------------------------

def calcular_indicador(df: pd.DataFrame, colunas_agrupamento: list[str]) -> pd.DataFrame:
    """Percentual de alunos avaliados que atingiram 743 pontos."""
    df = (
        df.groupby(colunas_agrupamento, dropna=False)
        .agg(
            total_alunos_avaliados=("atingiu_ponto_corte", "size"),
            total_alunos_alfabetizados=("atingiu_ponto_corte", "sum"),
        )
        .reset_index()
    )
    df["taxa_alfabetizacao_calculada"] = (
        df["total_alunos_alfabetizados"] / df["total_alunos_avaliados"] * 100
    ).round(2)
    return df


def comparar_com_meta(df_indicador: pd.DataFrame, df_metas: pd.DataFrame,
                      colunas_join: list[str], abrangencia: str) -> pd.DataFrame:
    """Indicador calculado x meta oficial de cada ano (2024-2030). O indicador
    não é aberto por rede, então a mesma taxa é comparada com a meta de cada rede."""
    colunas_geo_nao_usadas = list({"sigla_uf", "id_municipio"} - set(colunas_join))
    df_metas = (
        df_metas[df_metas["abrangencia"] == abrangencia]
        .drop(columns=["ano", *colunas_geo_nao_usadas])
    )
    if colunas_join:
        df = df_indicador.merge(df_metas, on=colunas_join, how="inner")
    else:
        df = df_indicador.merge(df_metas, how="cross")

    df["diferenca_percentual"] = (df["taxa_alfabetizacao_calculada"] - df["meta_percentual"]).round(2)
    df["atingiu_meta"] = df["taxa_alfabetizacao_calculada"] >= df["meta_percentual"]
    return df


def construir() -> None:
    DIR_GOLD.mkdir(parents=True, exist_ok=True)

    df_dir_municipio = silver_diretorio_municipio()
    df_municipio = silver_municipio(df_dir_municipio)
    df_metas = silver_metas()
    df_alunos = silver_alunos()

    colunas_localizacao = ["id_municipio", "nome_municipio", "sigla_uf", "nome_uf", "nome_regiao"]
    df_localizacao = df_dir_municipio[colunas_localizacao].drop_duplicates("id_municipio")
    df_alunos = df_alunos.merge(df_localizacao, on="id_municipio", how="left")

    df_ind_municipio = calcular_indicador(df_alunos, colunas_localizacao + ["ano"])
    df_ind_uf = calcular_indicador(df_alunos, ["sigla_uf", "nome_uf", "nome_regiao", "ano"])
    df_ind_brasil = calcular_indicador(df_alunos, ["ano"])

    df_comparacao = pd.concat(
        [
            comparar_com_meta(df_ind_municipio, df_metas, ["id_municipio"], "municipio"),
            comparar_com_meta(df_ind_uf, df_metas, ["sigla_uf"], "uf"),
            comparar_com_meta(df_ind_brasil, df_metas, [], "brasil"),
        ],
        ignore_index=True,
    )

    saidas = {
        "alunos": df_alunos,
        "indicador_municipio_oficial": df_municipio,
        "indicador_municipio": df_ind_municipio,
        "indicador_uf": df_ind_uf,
        "indicador_brasil": df_ind_brasil,
        "comparacao_meta_resultado": df_comparacao,
    }
    for nome, df in saidas.items():
        df.to_parquet(DIR_GOLD / f"{nome}.parquet", index=False)
        print(f"gold/{nome}: {len(df):,} linhas")

    checagens = [
        checar_duplicidade(df_alunos, ["id_aluno", "ano"], "gold.alunos"),
        *checar_valores_ausentes(df_alunos, ["proficiencia", "nome_municipio"], "gold.alunos"),
        checar_chave_estrangeira(df_alunos, df_dir_municipio, "id_municipio", "gold.alunos"),
        checar_duplicidade(df_municipio, ["id_municipio", "ano", "rede", "serie"], "gold.indicador_municipio_oficial"),
        checar_duplicidade(df_ind_municipio, ["id_municipio", "ano"], "gold.indicador_municipio"),
        *checar_valores_ausentes(df_ind_municipio, ["taxa_alfabetizacao_calculada"], "gold.indicador_municipio"),
        checar_duplicidade(df_ind_uf, ["sigla_uf", "ano"], "gold.indicador_uf"),
        checar_duplicidade(
            df_comparacao,
            ["abrangencia", "id_municipio", "sigla_uf", "ano", "ano_meta", "rede"],
            "gold.comparacao_meta_resultado",
        ),
    ]
    df_qualidade = pd.DataFrame(checagens)
    df_qualidade.to_csv(DIR_GOLD / "relatorio_qualidade.csv", index=False)
    print("\nChecagens de qualidade:")
    print(df_qualidade.to_string(index=False))
    if not df_qualidade["passou"].all():
        print("\nATENÇÃO: alguma checagem de qualidade falhou.")


if __name__ == "__main__":
    construir()
