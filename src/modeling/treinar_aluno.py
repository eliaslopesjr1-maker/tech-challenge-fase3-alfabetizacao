"""Treina e avalia o modelo de alfabetização do aluno.

Etapas:
1. Base: amostra de alunos de 2023 (treino) e 2024 (teste) + features de contexto
2. Validação cruzada no treino com GroupKFold por município (5 folds)
   - baseline: regressão logística
   - HistGradientBoosting (scikit-learn) com regularização fixa
   - LightGBM com busca aleatória de hiperparâmetros
   - LightGBM ponderado pelo peso amostral do Inep (`peso_aluno`)
   Para cada modelo: AUC simples e AUC ponderado pelo peso amostral.
3. Limiar de decisão escolhido nas predições out-of-fold do TREINO
   (nunca no teste), para identificar 80% dos não alfabetizados
4. Avaliação final no teste 2024 + "teto" teórico do problema
5. Salva modelos (models/), métricas (reports/) e predições (data/gold/)

Uso:
    python -m src.modeling.treinar_aluno
"""

import json
import time

import joblib
import numpy as np
import pandas as pd
from scipy.stats import loguniform, randint, uniform
from sklearn.base import clone
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold, RandomizedSearchCV

from src.config import DIR_GOLD, DIR_MODELOS, DIR_REPORTS, SEED
from src.evaluation.metricas import calcular_metricas, limiar_por_recall, tabela_comparacao
from src.modeling.dados import (
    ALVO, FEATURES_CATEGORICAS, carregar_base_alunos, carregar_painel, features_numericas, separar_treino_teste,
)
from src.modeling.pipeline import pipeline_hist_gradient_boosting, pipeline_lightgbm, pipeline_logistica

RECALL_ALVO_NAO_ALFABETIZADOS = 0.80

ESPACO_BUSCA = {
    "modelo__n_estimators": randint(200, 800),
    "modelo__learning_rate": loguniform(0.01, 0.15),
    "modelo__num_leaves": randint(15, 127),
    "modelo__min_child_samples": randint(50, 1000),
    "modelo__colsample_bytree": uniform(0.5, 0.5),
    "modelo__reg_lambda": loguniform(0.1, 20),
}


def teto_do_problema(teste: pd.DataFrame) -> float:
    """AUC de um 'oráculo' que conhece a taxa REAL de 2024 de cada município x
    rede e a usa como probabilidade. Como todas as features são de contexto
    (iguais para alunos do mesmo município/rede), nenhum modelo baseado nelas
    supera esse valor: é o limite superior do problema com esses dados."""
    taxa_real = teste.groupby(["id_municipio", "rede"])[ALVO].transform("mean")
    return roc_auc_score(teste[ALVO], taxa_real)


def validar(pipeline, X, y, peso, grupos, cv, ponderar_treino: bool = False) -> dict:
    """GroupKFold manual para medir, em cada fold, o AUC simples e o ponderado, e
    devolver as predições out-of-fold. Com `ponderar_treino`, o modelo é ajustado
    com sample_weight = peso_aluno."""
    oof = np.zeros(len(y))
    auc, auc_ponderado, auc_treino = [], [], []
    for indices_treino, indices_validacao in cv.split(X, y, grupos):
        modelo = clone(pipeline)
        parametros = {"modelo__sample_weight": peso.iloc[indices_treino].to_numpy()} if ponderar_treino else {}
        modelo.fit(X.iloc[indices_treino], y.iloc[indices_treino], **parametros)
        oof[indices_validacao] = modelo.predict_proba(X.iloc[indices_validacao])[:, 1]
        auc.append(roc_auc_score(y.iloc[indices_validacao], oof[indices_validacao]))
        auc_ponderado.append(roc_auc_score(y.iloc[indices_validacao], oof[indices_validacao],
                                           sample_weight=peso.iloc[indices_validacao]))
        auc_treino.append(roc_auc_score(y.iloc[indices_treino], modelo.predict_proba(X.iloc[indices_treino])[:, 1]))
    return {"auc": [float(np.mean(auc)), float(np.std(auc))],
            "auc_ponderado": [float(np.mean(auc_ponderado)), float(np.std(auc_ponderado))],
            "auc_treino": float(np.mean(auc_treino)), "oof": oof}


def treinar() -> None:
    inicio = time.time()
    DIR_MODELOS.mkdir(exist_ok=True)
    DIR_REPORTS.mkdir(exist_ok=True)

    numericas = features_numericas(carregar_painel())
    categoricas = FEATURES_CATEGORICAS
    base = carregar_base_alunos()
    treino, teste = separar_treino_teste(base)
    X_treino, y_treino, grupos = treino[numericas + categoricas], treino[ALVO], treino["id_municipio"]
    peso_treino, peso_teste = treino["peso_aluno"], teste["peso_aluno"]
    X_teste, y_teste = teste[numericas + categoricas], teste[ALVO]
    print(f"treino 2023: {len(treino):,} alunos | teste 2024: {len(teste):,} alunos | "
          f"{len(numericas)} numéricas + {len(categoricas)} categóricas")

    cv = GroupKFold(n_splits=5)

    # --- Busca de hiperparâmetros do LightGBM -------------------------------
    busca = RandomizedSearchCV(
        pipeline_lightgbm(numericas, categoricas), ESPACO_BUSCA, n_iter=12, scoring="roc_auc",
        cv=cv, random_state=SEED, n_jobs=1, return_train_score=True, refit=False, verbose=1,
    )
    busca.fit(X_treino, y_treino, groups=grupos)
    resultados_busca = pd.DataFrame(busca.cv_results_).sort_values("rank_test_score")
    resultados_busca.to_csv(DIR_REPORTS / "busca_hiperparametros_lgbm.csv", index=False)
    melhores = {k.replace("modelo__", ""): v for k, v in busca.best_params_.items()}
    print(f"melhores hiperparâmetros do LightGBM: {melhores}")

    # --- Validação cruzada comparável entre os quatro candidatos ------------
    candidatos = {
        "logistica": (pipeline_logistica(numericas, categoricas), False),
        "hist_gradient_boosting": (pipeline_hist_gradient_boosting(numericas, categoricas), False),
        "lightgbm": (pipeline_lightgbm(numericas, categoricas, **melhores), False),
        "lightgbm_ponderado": (pipeline_lightgbm(numericas, categoricas, **melhores), True),
    }
    validacao = {}
    for nome, (pipeline, ponderar) in candidatos.items():
        validacao[nome] = validar(pipeline, X_treino, y_treino, peso_treino, grupos, cv, ponderar)
        v = validacao[nome]
        print(f"{nome:24s} CV AUC {v['auc'][0]:.4f} ± {v['auc'][1]:.4f} | ponderado {v['auc_ponderado'][0]:.4f} "
              f"| treino {v['auc_treino']:.4f}")

    # --- Limiar escolhido no treino (out-of-fold do LightGBM) ---------------
    limiar = limiar_por_recall(y_treino, validacao["lightgbm"]["oof"], RECALL_ALVO_NAO_ALFABETIZADOS)
    print(f"limiar para {RECALL_ALVO_NAO_ALFABETIZADOS:.0%} de recall dos não alfabetizados (OOF treino): {limiar}")

    # --- Ajuste final e teste 2024 ------------------------------------------
    probas = {}
    for nome, (pipeline, ponderar) in candidatos.items():
        parametros = {"modelo__sample_weight": peso_treino.to_numpy()} if ponderar else {}
        pipeline.fit(X_treino, y_treino, **parametros)
        probas[nome] = pipeline.predict_proba(X_teste)[:, 1]

    resultados = {f"{nome} (limiar 0,5)": calcular_metricas(y_teste, proba, peso=peso_teste)
                  for nome, proba in probas.items()}
    resultados[f"lightgbm (limiar {limiar})"] = calcular_metricas(y_teste, probas["lightgbm"], limiar, peso=peso_teste)
    tabela = tabela_comparacao(resultados)
    print("\nTeste 2024:\n", tabela.to_string())

    teto = teto_do_problema(teste)
    print(f"\nteto teórico (oráculo município x rede): AUC {teto:.4f}")

    lgbm = candidatos["lightgbm"][0]
    metricas = {
        "dados": {"alunos_treino": len(treino), "alunos_teste": len(teste),
                  "features_numericas": numericas, "features_categoricas": categoricas,
                  "proporcao_nao_alfabetizados_teste": float(1 - y_teste.mean())},
        "validacao_cruzada": {
            **{nome: {k: v for k, v in resultado.items() if k != "oof"} for nome, resultado in validacao.items()},
            "lightgbm_melhores_parametros": {k: (float(v) if isinstance(v, (float, np.floating)) else int(v))
                                             for k, v in melhores.items()},
        },
        "lightgbm_auc_treino_completo": float(roc_auc_score(y_treino, lgbm.predict_proba(X_treino)[:, 1])),
        "limiar_escolhido_no_treino": limiar,
        "teste_2024": tabela.to_dict(orient="index"),
        "teto_teorico_auc": teto,
    }
    (DIR_REPORTS / "metricas_modelo_aluno.json").write_text(json.dumps(metricas, indent=2, ensure_ascii=False),
                                                           encoding="utf-8")
    tabela.to_csv(DIR_REPORTS / "metricas_teste_2024.csv")

    joblib.dump(candidatos["logistica"][0], DIR_MODELOS / "modelo_aluno_logistica.joblib")
    joblib.dump({"pipeline": lgbm, "limiar": limiar, "numericas": numericas, "categoricas": categoricas},
                DIR_MODELOS / "modelo_aluno_lgbm.joblib")

    predicoes = teste[["ano", "id_municipio", "rede", "sigla_uf", "nome_regiao", "rede_nome", ALVO, "peso_aluno"]].copy()
    predicoes["proba_logistica"] = probas["logistica"].astype("float32")
    predicoes["proba_hgb"] = probas["hist_gradient_boosting"].astype("float32")
    predicoes["proba_lgbm"] = probas["lightgbm"].astype("float32")
    predicoes["proba_lgbm_ponderado"] = probas["lightgbm_ponderado"].astype("float32")
    predicoes.to_parquet(DIR_GOLD / "predicoes_aluno_2024.parquet", index=False)

    print(f"\nconcluído em {(time.time() - inicio) / 60:.1f} min")


if __name__ == "__main__":
    treinar()
