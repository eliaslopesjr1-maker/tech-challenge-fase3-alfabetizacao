"""Treina e avalia o modelo de alfabetização do aluno.

Etapas:
1. Base: amostra de alunos de 2023 (treino) e 2024 (teste) + features de contexto
2. Validação cruzada no treino com GroupKFold por município (5 folds)
   - baseline: regressão logística
   - LightGBM com busca aleatória de hiperparâmetros
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
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold, RandomizedSearchCV, cross_val_predict, cross_validate

from src.config import DIR_GOLD, DIR_MODELOS, DIR_REPORTS, SEED
from src.evaluation.metricas import calcular_metricas, limiar_por_recall, tabela_comparacao
from src.modeling.dados import (
    ALVO, FEATURES_CATEGORICAS, carregar_base_alunos, carregar_painel, features_numericas, separar_treino_teste,
)
from src.modeling.pipeline import pipeline_lightgbm, pipeline_logistica

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


def treinar() -> None:
    inicio = time.time()
    DIR_MODELOS.mkdir(exist_ok=True)
    DIR_REPORTS.mkdir(exist_ok=True)

    numericas = features_numericas(carregar_painel())
    categoricas = FEATURES_CATEGORICAS
    base = carregar_base_alunos()
    treino, teste = separar_treino_teste(base)
    X_treino, y_treino, grupos = treino[numericas + categoricas], treino[ALVO], treino["id_municipio"]
    X_teste, y_teste = teste[numericas + categoricas], teste[ALVO]
    print(f"treino 2023: {len(treino):,} alunos | teste 2024: {len(teste):,} alunos | "
          f"{len(numericas)} numéricas + {len(categoricas)} categóricas")

    cv = GroupKFold(n_splits=5)

    # --- Baseline -----------------------------------------------------------
    logistica = pipeline_logistica(numericas, categoricas)
    cv_logistica = cross_validate(logistica, X_treino, y_treino, groups=grupos, cv=cv,
                                  scoring="roc_auc", return_train_score=True, n_jobs=1)
    print(f"logística   CV AUC {cv_logistica['test_score'].mean():.4f} ± {cv_logistica['test_score'].std():.4f}")

    # --- LightGBM com busca de hiperparâmetros ------------------------------
    busca = RandomizedSearchCV(
        pipeline_lightgbm(numericas, categoricas), ESPACO_BUSCA, n_iter=12, scoring="roc_auc",
        cv=cv, random_state=SEED, n_jobs=1, return_train_score=True, refit=False, verbose=1,
    )
    busca.fit(X_treino, y_treino, groups=grupos)
    resultados_busca = pd.DataFrame(busca.cv_results_).sort_values("rank_test_score")
    resultados_busca.to_csv(DIR_REPORTS / "busca_hiperparametros_lgbm.csv", index=False)
    melhores = {k.replace("modelo__", ""): v for k, v in busca.best_params_.items()}
    melhor_linha = resultados_busca.iloc[0]
    print(f"LightGBM    CV AUC {melhor_linha['mean_test_score']:.4f} ± {melhor_linha['std_test_score']:.4f} "
          f"(treino {melhor_linha['mean_train_score']:.4f}) | {melhores}")

    lgbm = pipeline_lightgbm(numericas, categoricas, **melhores)

    # --- Limiar escolhido no treino (out-of-fold) ---------------------------
    oof = cross_val_predict(lgbm, X_treino, y_treino, groups=grupos, cv=cv, method="predict_proba", n_jobs=1)[:, 1]
    limiar = limiar_por_recall(y_treino, oof, RECALL_ALVO_NAO_ALFABETIZADOS)
    print(f"limiar para {RECALL_ALVO_NAO_ALFABETIZADOS:.0%} de recall dos não alfabetizados (OOF treino): {limiar}")

    # --- Ajuste final e teste 2024 ------------------------------------------
    logistica.fit(X_treino, y_treino)
    lgbm.fit(X_treino, y_treino)
    proba_logistica = logistica.predict_proba(X_teste)[:, 1]
    proba_lgbm = lgbm.predict_proba(X_teste)[:, 1]
    proba_treino_lgbm = lgbm.predict_proba(X_treino)[:, 1]

    resultados = {
        "logistica (limiar 0,5)": calcular_metricas(y_teste, proba_logistica),
        "lightgbm (limiar 0,5)": calcular_metricas(y_teste, proba_lgbm),
        f"lightgbm (limiar {limiar})": calcular_metricas(y_teste, proba_lgbm, limiar),
    }
    tabela = tabela_comparacao(resultados)
    print("\nTeste 2024:\n", tabela.to_string())

    teto = teto_do_problema(teste)
    taxa_base = 1 - y_teste.mean()
    print(f"\nteto teórico (oráculo município x rede): AUC {teto:.4f}")

    metricas = {
        "dados": {"alunos_treino": len(treino), "alunos_teste": len(teste),
                  "features_numericas": numericas, "features_categoricas": categoricas,
                  "proporcao_nao_alfabetizados_teste": taxa_base},
        "validacao_cruzada": {
            "logistica_auc": [float(cv_logistica["test_score"].mean()), float(cv_logistica["test_score"].std())],
            "logistica_auc_treino": float(cv_logistica["train_score"].mean()),
            "lightgbm_auc": [float(melhor_linha["mean_test_score"]), float(melhor_linha["std_test_score"])],
            "lightgbm_auc_treino": float(melhor_linha["mean_train_score"]),
            "lightgbm_melhores_parametros": {k: (float(v) if isinstance(v, (float, np.floating)) else int(v))
                                             for k, v in melhores.items()},
        },
        "lightgbm_auc_treino_completo": float(roc_auc_score(y_treino, proba_treino_lgbm)),
        "limiar_escolhido_no_treino": limiar,
        "teste_2024": tabela.to_dict(orient="index"),
        "teto_teorico_auc": teto,
    }
    (DIR_REPORTS / "metricas_modelo_aluno.json").write_text(json.dumps(metricas, indent=2, ensure_ascii=False),
                                                           encoding="utf-8")
    tabela.to_csv(DIR_REPORTS / "metricas_teste_2024.csv")

    joblib.dump(logistica, DIR_MODELOS / "modelo_aluno_logistica.joblib")
    joblib.dump({"pipeline": lgbm, "limiar": limiar, "numericas": numericas, "categoricas": categoricas},
                DIR_MODELOS / "modelo_aluno_lgbm.joblib")

    predicoes = teste[["ano", "id_municipio", "rede", "sigla_uf", "nome_regiao", "rede_nome", ALVO, "peso_aluno"]].copy()
    predicoes["proba_logistica"] = proba_logistica.astype("float32")
    predicoes["proba_lgbm"] = proba_lgbm.astype("float32")
    predicoes.to_parquet(DIR_GOLD / "predicoes_aluno_2024.parquet", index=False)

    print(f"\nconcluído em {(time.time() - inicio) / 60:.1f} min")


if __name__ == "__main__":
    treinar()
