"""Modelo de metas: a rede municipal vai atingir a meta do ano seguinte?

Estrutura "ano atual -> ano seguinte":
- Treino: situação em 2023 (taxa, meta de 2024, contexto) -> atingiu a meta de 2024?
- Previsão: situação em 2024 (taxa, meta de 2025, contexto) -> vai atingir a meta de 2025?

Todas as features são conhecidas ANTES do ano previsto. As metas foram
publicadas pelo Inep a partir do resultado de 2023, e o contexto vem da edição
do ano atual.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold, StratifiedKFold, cross_val_predict

from src.config import SEED
from src.modeling.base_municipal import carregar_base_municipal
from src.modeling.dados import carregar_painel, features_numericas
from src.modeling.pipeline import pipeline_lightgbm, pipeline_logistica

CATEGORICAS = ["sigla_uf", "nome_regiao"]
FEATURES_SITUACAO = ["taxa_atual", "meta_proximo_ano", "distancia_meta", "log_alunos_avaliados"]
ALVO = "atingiu_meta"


def base_transicao(ano_atual: int) -> pd.DataFrame:
    """Situação de cada rede municipal em `ano_atual` e, se já houver resultado,
    se ela atingiu a meta de `ano_atual + 1`."""
    base = carregar_base_municipal(ano_atual)
    base = base[base[f"meta_alfabetizacao_{ano_atual + 1}"].notna()].copy()
    base["taxa_atual"] = base["taxa_alfabetizacao"]
    base["meta_proximo_ano"] = base[f"meta_alfabetizacao_{ano_atual + 1}"]
    base["distancia_meta"] = base["taxa_atual"] - base["meta_proximo_ano"]
    base["log_alunos_avaliados"] = np.log10(base["alunos_avaliados"])

    seguinte = carregar_base_municipal(ano_atual + 1)
    if len(seguinte):
        resultado = seguinte.set_index("id_municipio")["taxa_alfabetizacao"].rename("taxa_ano_seguinte")
        base = base.join(resultado, on="id_municipio")
        base[ALVO] = (base["taxa_ano_seguinte"] >= base["meta_proximo_ano"]).astype("Int8")
        base.loc[base["taxa_ano_seguinte"].isna(), ALVO] = pd.NA
    return base.reset_index(drop=True)


def colunas_modelo() -> tuple[list[str], list[str]]:
    contexto = features_numericas(carregar_painel())
    return FEATURES_SITUACAO + contexto, CATEGORICAS


def modelos(numericas: list[str], categoricas: list[str]) -> dict:
    return {
        "logística": pipeline_logistica(numericas, categoricas),
        # Base pequena (~5 mil municípios): árvores rasas e folhas grandes.
        "LightGBM": pipeline_lightgbm(numericas, categoricas, n_estimators=300, learning_rate=0.03,
                                      num_leaves=15, min_child_samples=40, colsample_bytree=0.7),
    }


def avaliar(treino: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    """Validação cruzada estratificada (municípios novos) e por UF (estados novos),
    comparando com a regra ingênua 'atinge se já estiver acima da meta'."""
    numericas, categoricas = colunas_modelo()
    X, y = treino[numericas + categoricas], treino[ALVO].astype(int)

    linhas, predicoes = [], {}
    regra = (treino["distancia_meta"] >= 0).astype(int)
    linhas.append({"modelo": "regra: já está acima da meta", "AUC (estratificado)": roc_auc_score(y, regra),
                   "AUC (por UF)": roc_auc_score(y, regra), "Brier": np.nan})

    for nome, pipeline in modelos(numericas, categoricas).items():
        estratificado = cross_val_predict(pipeline, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=SEED),
                                          method="predict_proba")[:, 1]
        por_uf = cross_val_predict(pipeline, X, y, groups=treino["sigla_uf"], cv=GroupKFold(5),
                                   method="predict_proba")[:, 1]
        predicoes[nome] = estratificado
        linhas.append({"modelo": nome, "AUC (estratificado)": roc_auc_score(y, estratificado),
                       "AUC (por UF)": roc_auc_score(y, por_uf), "Brier": brier_score_loss(y, estratificado)})
    return pd.DataFrame(linhas).set_index("modelo"), predicoes


def sensibilidade_territorio(treino: pd.DataFrame, futuro: pd.DataFrame) -> pd.DataFrame:
    """Repete o LightGBM com e sem UF/região. Com uma única transição (2023 -> 2024)
    não dá para separar choque passageiro de tendência; esta tabela mostra quanto
    a previsão de 2025 depende do território."""
    numericas, _ = colunas_modelo()
    y = treino[ALVO].astype(int)
    linhas = {}
    for nome, categoricas in [("com UF e região", CATEGORICAS), ("só região", ["nome_regiao"]), ("sem UF/região", [])]:
        pipeline = modelos(numericas, categoricas)["LightGBM"]
        X = treino[numericas + categoricas]
        estratificado = cross_val_predict(pipeline, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=SEED),
                                          method="predict_proba")[:, 1]
        por_uf = cross_val_predict(pipeline, X, y, groups=treino["sigla_uf"], cv=GroupKFold(5),
                                   method="predict_proba")[:, 1]
        proba = pipeline.fit(X, y).predict_proba(futuro[numericas + categoricas])[:, 1]
        media_uf = pd.Series(proba, index=futuro.index).groupby(futuro["sigla_uf"]).mean()
        linhas[nome] = {"AUC (estratificado)": roc_auc_score(y, estratificado), "AUC (por UF)": roc_auc_score(y, por_uf),
                        "% previsto de atingir 2025": proba.mean() * 100,
                        **{f"prob. média {uf}": media_uf[uf] for uf in ["RS", "BA", "CE", "SP"]}}
    return pd.DataFrame(linhas).T


def treinar_e_prever(treino: pd.DataFrame, futuro: pd.DataFrame, nome_modelo: str = "LightGBM",
                     numericas: list[str] | None = None, categoricas: list[str] | None = None):
    padrao_numericas, padrao_categoricas = colunas_modelo()
    numericas = padrao_numericas if numericas is None else numericas
    categoricas = padrao_categoricas if categoricas is None else categoricas
    pipeline = modelos(numericas, categoricas)[nome_modelo]
    pipeline.fit(treino[numericas + categoricas], treino[ALVO].astype(int))
    proba = pipeline.predict_proba(futuro[numericas + categoricas])[:, 1]
    return pipeline, proba


LIMITE_CHOQUE_PP = 10


def avaliar_cenario_neutro(treino: pd.DataFrame) -> dict:
    """Validação do cenário neutro (só a situação da rede, sem contexto nem território)."""
    y = treino[ALVO].astype(int)
    pipeline = modelos(FEATURES_SITUACAO, [])["LightGBM"]
    X = treino[FEATURES_SITUACAO]
    estratificado = cross_val_predict(pipeline, X, y, cv=StratifiedKFold(5, shuffle=True, random_state=SEED),
                                      method="predict_proba")[:, 1]
    por_uf = cross_val_predict(pipeline, X, y, groups=treino["sigla_uf"], cv=GroupKFold(5),
                               method="predict_proba")[:, 1]
    return {"AUC (estratificado)": roc_auc_score(y, estratificado), "AUC (por UF)": roc_auc_score(y, por_uf),
            "Brier": brier_score_loss(y, estratificado)}


def choques_estaduais(treino: pd.DataFrame) -> pd.Series:
    """Variação da taxa da rede municipal de cada UF no ano de treino (ponderada
    pelos alunos), descontada a variação nacional, em pontos percentuais."""
    peso = treino["alunos_avaliados"]
    antes = (treino["taxa_atual"] * peso).groupby(treino["sigla_uf"]).sum() / peso.groupby(treino["sigla_uf"]).sum()
    depois = (treino["taxa_ano_seguinte"] * peso).groupby(treino["sigla_uf"]).sum() / peso.groupby(treino["sigla_uf"]).sum()
    nacional = np.average(treino["taxa_ano_seguinte"] - treino["taxa_atual"], weights=peso)
    return (depois - antes - nacional).rename("choque_vs_brasil_pp")


def prever_com_cenarios(treino: pd.DataFrame, futuro: pd.DataFrame) -> pd.DataFrame:
    """Previsão conservadora para o ano seguinte.

    Dois cenários:
    - completo: contexto + UF/região, o mais bem validado;
    - neutro: só a situação da rede (taxa, meta, distância, tamanho), que capta a
      dinâmica nacional (regressão à média) sem padrão regional.

    Com uma única transição de treino, o cenário completo repete o que aconteceu
    em cada estado naquele ano. Nos estados com choque atípico (variação que se
    afasta da nacional em mais de LIMITE_CHOQUE_PP pontos, como o RS em 2024, ano
    das enchentes), esse padrão não deve ser projetado: ali se publica o cenário
    neutro. Estados sem rede municipal no ano de treino não têm histórico e são
    marcados com confiança baixa.
    """
    _, completo = treinar_e_prever(treino, futuro)
    _, neutro = treinar_e_prever(treino, futuro, numericas=FEATURES_SITUACAO, categoricas=[])
    choques = choques_estaduais(treino)
    ufs_com_choque = set(choques[choques.abs() > LIMITE_CHOQUE_PP].index)
    ufs_sem_historico = set(futuro["sigla_uf"]) - set(choques.index)

    cenarios = pd.DataFrame({"proba_cenario_completo": completo, "proba_cenario_neutro": neutro}, index=futuro.index)
    usa_neutro = futuro["sigla_uf"].isin(ufs_com_choque)
    cenarios["proba_atingir_meta"] = np.where(usa_neutro, neutro, completo)
    cenarios["confianca"] = np.select(
        [usa_neutro, futuro["sigla_uf"].isin(ufs_sem_historico)],
        ["baixa: UF com choque atípico no treino (cenário neutro)", "baixa: UF sem histórico no treino"],
        default="normal",
    )
    return cenarios
