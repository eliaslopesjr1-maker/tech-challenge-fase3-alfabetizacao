"""Clusterização: quais municípios têm padrões de contexto semelhantes?

Os grupos são formados só com variáveis de CONTEXTO (trajetória escolar,
socioeconomia, ruralidade, infraestrutura, docentes e porte), sem o resultado
da avaliação. Assim dá para comparar o desempenho de municípios parecidos e
encontrar os que vão muito melhor que os seus pares (referências a estudar).
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.metrics import silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.config import SEED

FEATURES_CLUSTER = {
    "tdi_ef_anos_iniciais": "distorção idade-série (%)",
    "taxa_abandono_ef_anos_iniciais": "abandono (%)",
    "inse_medio": "INSE médio",
    "prop_pobreza_criancas": "pobreza infantil (%)",
    "idhm": "IDHM",
    "pct_alunos_escola_rural": "alunos em escola rural",
    "pct_alunos_area_diferenciada": "alunos em área diferenciada",
    "pct_biblioteca_ou_sala_leitura": "biblioteca/sala de leitura",
    "pct_matricula_integral_ai": "matrícula em tempo integral",
    "dsu_ef_anos_iniciais": "docentes com superior (%)",
    "alunos_por_docente_ai": "alunos por docente",
    "log_populacao": "log da população",
}


def pipeline_kmeans(k: int) -> Pipeline:
    return Pipeline([
        ("imputar", SimpleImputer(strategy="median")),
        ("escalar", StandardScaler()),
        ("kmeans", KMeans(n_clusters=k, n_init=20, random_state=SEED)),
    ])


def avaliar_k(df: pd.DataFrame, ks=range(3, 9)) -> pd.DataFrame:
    """Inércia (cotovelo) e silhueta para cada número de grupos."""
    X = df[list(FEATURES_CLUSTER)]
    linhas = []
    for k in ks:
        pipeline = pipeline_kmeans(k).fit(X)
        X_escalado = pipeline[:-1].transform(X)
        linhas.append({"k": k, "inercia": pipeline["kmeans"].inertia_,
                       "silhueta": silhouette_score(X_escalado, pipeline["kmeans"].labels_,
                                                    sample_size=3000, random_state=SEED)})
    return pd.DataFrame(linhas).set_index("k")


def agrupar(df: pd.DataFrame, k: int) -> tuple[Pipeline, np.ndarray]:
    pipeline = pipeline_kmeans(k).fit(df[list(FEATURES_CLUSTER)])
    return pipeline, pipeline["kmeans"].labels_


def nomear_clusters(df: pd.DataFrame, rotulo: str = "cluster") -> dict[int, str]:
    """Dá um nome a cada grupo a partir do perfil de contexto (regras fixas,
    para os nomes não dependerem da numeração arbitrária do KMeans)."""
    mediana = df.groupby(rotulo)[list(FEATURES_CLUSTER)].median()
    nomes, restantes = {}, list(mediana.index)

    def escolher(coluna, nome, maior=True):
        candidato = mediana.loc[restantes, coluna].idxmax() if maior else mediana.loc[restantes, coluna].idxmin()
        nomes[candidato] = nome
        restantes.remove(candidato)

    escolher("pct_alunos_area_diferenciada", "Áreas diferenciadas e rurais")
    escolher("tdi_ef_anos_iniciais", "Vulnerável com fluxo escolar crítico")
    escolher("prop_pobreza_criancas", "Vulnerável com fluxo escolar regular")
    escolher("log_populacao", "Urbano de maior porte")
    for resto in restantes:
        nomes[resto] = "Pequenos municípios desenvolvidos"
    return nomes


def perfil(df: pd.DataFrame, rotulo: str = "cluster") -> pd.DataFrame:
    """Média do contexto e do resultado em cada grupo. A taxa do grupo é
    ponderada pelo número de alunos avaliados."""
    contexto = df.groupby(rotulo)[list(FEATURES_CLUSTER)].median().rename(columns=FEATURES_CLUSTER)
    resultado = df.groupby(rotulo).apply(
        lambda g: pd.Series({
            "municípios": len(g),
            "taxa de alfabetização (%)": np.average(g["taxa_alfabetizacao"], weights=g["alunos_avaliados"]),
            "% atingiu a meta do ano": g["atingiu_meta_no_ano"].mean() * 100,
            "região mais comum": g["nome_regiao"].mode().iat[0],
        }),
        include_groups=False,
    )
    return resultado.join(contexto)
