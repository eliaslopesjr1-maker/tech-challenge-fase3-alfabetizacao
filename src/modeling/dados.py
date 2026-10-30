"""Base de modelagem do aluno: alvo individual + features de contexto.

Cada aluno avaliado recebe as features do seu município x rede x ano (painel
gerado por `construir_features.py`). Variáveis do próprio aluno que vêm da prova
(`proficiencia`, `alfabetizado`) ficam de fora, porque definem o alvo.
"""

import pandas as pd

from src.config import DIR_GOLD, SEED

ALVO = "alfabetizado"

FEATURES_CATEGORICAS = ["sigla_uf", "nome_regiao", "rede_nome"]

# Colunas do painel que NÃO são features:
# - identificadores e nomes
# - a nota e o alvo do aluno (proficiencia, alfabetizado, atingiu_ponto_corte):
#   não estão no painel, mas ficam listadas como proteção contra uso acidental
# - o resultado da própria avaliação (alunos_avaliados/alfabetizados e taxa
#   são calculados com as notas do ano que se quer prever → leakage)
# - taxa_ano_anterior: só existe para 2024 (usada apenas no modelo de metas)
NAO_FEATURES = {
    "ano", "id_municipio", "rede", "nome_municipio",
    "proficiencia", "alfabetizado", "atingiu_ponto_corte", "peso_aluno",
    "alunos_avaliados", "alunos_alfabetizados", "taxa_alfabetizacao", "taxa_ano_anterior",
    *FEATURES_CATEGORICAS,
}


def features_numericas(painel: pd.DataFrame) -> list[str]:
    return [c for c in painel.select_dtypes("number").columns if c not in NAO_FEATURES]


def carregar_painel() -> pd.DataFrame:
    return pd.read_parquet(DIR_GOLD / "painel_municipio_rede.parquet")


def carregar_base_alunos(alunos_por_ano: int | None = 300_000, seed: int = SEED) -> pd.DataFrame:
    """Alunos (amostra aleatória de cada ano) + features do painel.

    A amostra existe só por limite de memória da máquina de desenvolvimento;
    `alunos_por_ano=None` usa todos os alunos. Como as features são do
    município x rede, 300 mil alunos por ano já cobrem praticamente todas as
    combinações e a perda de informação é mínima.
    """
    alunos = pd.read_parquet(
        DIR_GOLD / "alunos.parquet",
        columns=["ano", "id_municipio", "rede", "atingiu_ponto_corte", "peso_aluno"],
    )
    alunos = alunos[alunos["rede"].isin(["2", "3"])].rename(columns={"atingiu_ponto_corte": ALVO})
    alunos[ALVO] = alunos[ALVO].astype("int8")

    if alunos_por_ano is not None and alunos.groupby("ano").size().min() > alunos_por_ano:
        alunos = alunos.groupby("ano").sample(n=alunos_por_ano, random_state=seed).reset_index(drop=True)

    painel = carregar_painel()
    colunas_painel = ["ano", "id_municipio", "rede", *FEATURES_CATEGORICAS, *features_numericas(painel)]
    base = alunos.merge(painel[colunas_painel], on=["ano", "id_municipio", "rede"], how="left")

    numericas = features_numericas(painel)
    base[numericas] = base[numericas].astype("float32")
    return base


def separar_treino_teste(base: pd.DataFrame, ano_treino: int = 2023, ano_teste: int = 2024):
    """Split temporal: treina no ciclo anterior, testa no seguinte."""
    treino = base[base["ano"] == ano_treino].reset_index(drop=True)
    teste = base[base["ano"] == ano_teste].reset_index(drop=True)
    return treino, teste
