"""Métricas de classificação e gráficos de avaliação.

Convenção: classe positiva = 1 = alfabetizado. Para política pública, o grupo
de interesse é o de NÃO alfabetizados (classe 0), por isso o recall e a precisão
dessa classe são reportados separadamente.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    ConfusionMatrixDisplay, average_precision_score, brier_score_loss, f1_score,
    precision_score, recall_score, roc_auc_score, roc_curve,
)

from src.config import DIR_IMAGENS


def calcular_metricas(y_true, proba, limiar: float = 0.5, peso=None) -> dict:
    """Com `peso` (peso amostral do Inep), inclui o AUC ponderado, que representa a
    população de alunos e não só a amostra avaliada."""
    pred = (proba >= limiar).astype(int)
    ponderado = {"roc_auc_ponderado": roc_auc_score(y_true, proba, sample_weight=peso)} if peso is not None else {}
    return {
        "roc_auc": roc_auc_score(y_true, proba),
        **ponderado,
        "pr_auc_alfabetizado": average_precision_score(y_true, proba),
        "pr_auc_nao_alfabetizado": average_precision_score(1 - np.asarray(y_true), 1 - proba),
        "brier": brier_score_loss(y_true, proba),
        "f1_macro": f1_score(y_true, pred, average="macro"),
        "recall_nao_alfabetizado": recall_score(y_true, pred, pos_label=0),
        "precisao_nao_alfabetizado": precision_score(y_true, pred, pos_label=0),
        "recall_alfabetizado": recall_score(y_true, pred, pos_label=1),
        "limiar": limiar,
    }


def tabela_comparacao(resultados: dict[str, dict]) -> pd.DataFrame:
    return pd.DataFrame(resultados).T.round(4)


def limiar_por_recall(y_true, proba, recall_alvo: float) -> float:
    """Maior limiar que garante pelo menos `recall_alvo` de não alfabetizados
    identificados (predição = 0 quando proba < limiar)."""
    y_true = np.asarray(y_true)
    # Arredonda ANTES de testar: o valor devolvido é exatamente o que foi avaliado.
    for limiar in np.round(np.arange(0.30, 0.80, 0.005), 3):
        if recall_score(y_true, (proba >= limiar).astype(int), pos_label=0) >= recall_alvo:
            return float(limiar)
    return 0.8


def grafico_roc(curvas: dict[str, tuple], salvar: str | None = None) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(6, 5.5))
    for nome, (y_true, proba) in curvas.items():
        fpr, tpr, _ = roc_curve(y_true, proba)
        ax.plot(fpr, tpr, label=f"{nome} (AUC {roc_auc_score(y_true, proba):.3f})")
    ax.plot([0, 1], [0, 1], ":", color="grey")
    ax.set(title="Curva ROC - teste 2024", xlabel="taxa de falsos positivos", ylabel="taxa de verdadeiros positivos")
    ax.legend(loc="lower right", fontsize=9)
    return _salvar(fig, salvar)


def grafico_calibracao(curvas: dict[str, tuple], salvar: str | None = None) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(6, 5.5))
    for nome, (y_true, proba) in curvas.items():
        frac_pos, media_pred = calibration_curve(y_true, proba, n_bins=15, strategy="quantile")
        ax.plot(media_pred, frac_pos, "o-", markersize=4, label=nome)
    ax.plot([0, 1], [0, 1], ":", color="grey", label="calibração perfeita")
    ax.set(title="Calibração - teste 2024", xlabel="probabilidade prevista de alfabetização",
           ylabel="fração observada de alfabetizados")
    ax.legend(fontsize=9)
    return _salvar(fig, salvar)


def grafico_matriz_confusao(y_true, proba, limiar: float, titulo: str, salvar: str | None = None) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(5, 4.5))
    ConfusionMatrixDisplay.from_predictions(
        y_true, (proba >= limiar).astype(int), display_labels=["não alfabetizado", "alfabetizado"],
        normalize="true", values_format=".1%", cmap="Blues", colorbar=False, ax=ax,
    )
    ax.set_title(titulo)
    ax.set(xlabel="previsto", ylabel="real")
    ax.grid(False)
    return _salvar(fig, salvar)


def _salvar(fig: plt.Figure, salvar: str | None) -> plt.Figure:
    fig.tight_layout()
    if salvar:
        fig.savefig(DIR_IMAGENS / f"{salvar}.png")
    return fig
