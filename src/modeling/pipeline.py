"""Pipelines scikit-learn: pré-processamento + modelo num objeto só.

Todo o pré-processamento (imputação, escala, encoding) é ajustado dentro do
`Pipeline`. Assim, em cada fold da validação cruzada as medianas, médias e
categorias são aprendidas só com os dados de treino daquele fold, sem vazar
informação da validação.
"""

from lightgbm import LGBMClassifier
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config import SEED


def preprocessador(numericas: list[str], categoricas: list[str], escalar: bool) -> ColumnTransformer:
    passos_numericos = [("imputar", SimpleImputer(strategy="median", add_indicator=True))]
    if escalar:
        passos_numericos.append(("escalar", StandardScaler()))

    return ColumnTransformer(
        [
            ("num", Pipeline(passos_numericos), numericas),
            ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=20, sparse_output=False), categoricas),
        ],
        verbose_feature_names_out=False,
    )


def pipeline_logistica(numericas: list[str], categoricas: list[str]) -> Pipeline:
    """Baseline linear e interpretável. Regularização L2 por causa da
    multicolinearidade vista na EDA (IDHM e componentes, pobreza, Gini)."""
    return Pipeline([
        ("prep", preprocessador(numericas, categoricas, escalar=True)),
        ("modelo", LogisticRegression(C=1.0, max_iter=2000)),
    ])


def pipeline_lightgbm(numericas: list[str], categoricas: list[str], **params) -> Pipeline:
    """Gradient boosting: captura não linearidades e interações (ex.: rede x UF)."""
    modelo = LGBMClassifier(
        n_estimators=400, learning_rate=0.05, num_leaves=31, min_child_samples=200,
        subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0,
        random_state=SEED, n_jobs=4, verbose=-1,
    )
    modelo.set_params(**params)
    return Pipeline([
        ("prep", preprocessador(numericas, categoricas, escalar=False)),
        ("modelo", modelo),
    ])
