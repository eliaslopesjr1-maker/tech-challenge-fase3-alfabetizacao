"""Pipelines, métricas, interpretabilidade e clusterização com dados sintéticos."""

import numpy as np
import pandas as pd
import pytest

from src.evaluation.interpretabilidade import feature_original
from src.evaluation.metricas import calcular_metricas, limiar_por_recall
from src.modeling import clusterizacao
from src.modeling.pipeline import pipeline_lightgbm, pipeline_logistica


@pytest.fixture
def dados():
    rng = np.random.default_rng(0)
    n = 600
    X = pd.DataFrame({
        "tdi_ef_anos_iniciais": rng.uniform(0, 30, n),
        "inse_medio": rng.uniform(3.5, 6, n),
        "sigla_uf": rng.choice(["CE", "BA", "SP"], n),
        "rede_nome": rng.choice(["municipal", "estadual"], n),
    })
    X.loc[::10, "inse_medio"] = np.nan
    logito = -0.1 * X["tdi_ef_anos_iniciais"] + 1.2 * X["inse_medio"].fillna(4.8) - 4
    y = pd.Series((rng.uniform(size=n) < 1 / (1 + np.exp(-logito))).astype(int))
    return X, y


@pytest.mark.parametrize("construtor", [pipeline_logistica, pipeline_lightgbm])
def test_pipelines_treinam_com_ausentes_e_categoria_nova(dados, construtor):
    X, y = dados
    pipeline = construtor(["tdi_ef_anos_iniciais", "inse_medio"], ["sigla_uf", "rede_nome"])
    if construtor is pipeline_lightgbm:
        pipeline.set_params(modelo__n_estimators=20, modelo__min_child_samples=20)
    pipeline.fit(X, y)

    novo = X.head(3).assign(sigla_uf="RR", inse_medio=np.nan)   # UF nunca vista + ausente
    proba = pipeline.predict_proba(novo)[:, 1]
    assert proba.shape == (3,) and np.all((proba >= 0) & (proba <= 1))


def test_metricas_e_limiar_por_recall():
    y = np.array([0, 0, 0, 1, 1, 1, 1, 1])
    proba = np.array([0.1, 0.4, 0.6, 0.5, 0.7, 0.8, 0.9, 0.95])
    metricas = calcular_metricas(y, proba)
    assert metricas["roc_auc"] == pytest.approx(0.9333, abs=1e-3)
    limiar = limiar_por_recall(y, proba, recall_alvo=1.0)
    assert ((proba < limiar) & (y == 0)).sum() == 3   # todos os não alfabetizados sinalizados


@pytest.mark.parametrize("nome, esperado", [
    ("missingindicator_inse_medio", "inse_medio"),
    ("sigla_uf_CE", "sigla_uf"),
    ("rede_nome_municipal", "rede_nome"),
    ("tdi_ef_anos_iniciais", "tdi_ef_anos_iniciais"),
])
def test_feature_original(nome, esperado):
    assert feature_original(nome) == esperado


def test_nomear_clusters_e_deterministico():
    linhas = []
    perfis = {
        0: {"pct_alunos_area_diferenciada": 0.4, "tdi_ef_anos_iniciais": 8, "prop_pobreza_criancas": 60, "log_populacao": 4.1},
        1: {"pct_alunos_area_diferenciada": 0.0, "tdi_ef_anos_iniciais": 16, "prop_pobreza_criancas": 56, "log_populacao": 4.2},
        2: {"pct_alunos_area_diferenciada": 0.0, "tdi_ef_anos_iniciais": 6, "prop_pobreza_criancas": 57, "log_populacao": 4.0},
        3: {"pct_alunos_area_diferenciada": 0.0, "tdi_ef_anos_iniciais": 4, "prop_pobreza_criancas": 12, "log_populacao": 4.7},
        4: {"pct_alunos_area_diferenciada": 0.0, "tdi_ef_anos_iniciais": 3, "prop_pobreza_criancas": 17, "log_populacao": 3.8},
    }
    for cluster, perfil in perfis.items():
        base = {coluna: 0.0 for coluna in clusterizacao.FEATURES_CLUSTER}
        linhas.append({**base, **perfil, "cluster": cluster})
    nomes = clusterizacao.nomear_clusters(pd.DataFrame(linhas))
    assert nomes == {
        0: "Áreas diferenciadas e rurais",
        1: "Vulnerável com fluxo escolar crítico",
        2: "Vulnerável com fluxo escolar regular",
        3: "Urbano de maior porte",
        4: "Pequenos municípios desenvolvidos",
    }
