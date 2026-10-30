"""Interpretabilidade do modelo: permutation importance, SHAP e importância por tema.

Como várias features medem a mesma coisa (IDHM e seus componentes, pobreza,
Gini...), a importância de cada uma isolada fica "diluída". Por isso, além da
leitura por variável, os valores SHAP são somados por TEMA - o que responde
melhor à pergunta de negócio "quais fatores mais impactam a alfabetização".
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.inspection import permutation_importance

from src.config import DIR_IMAGENS, SEED

TEMAS = {
    "Trajetória escolar": [
        "tdi_ef_anos_iniciais", "taxa_abandono_ef_anos_iniciais", "taxa_aprovacao_ef_2_ano",
        "atu_ef_2_ano", "had_ef_anos_iniciais",
    ],
    "Nível socioeconômico": [
        "inse_medio", "pct_alunos_inse_baixo", "idhm", "idhm_e", "idhm_l", "idhm_r", "indice_gini",
        "renda_pc", "prop_pobreza_criancas", "taxa_analfabetismo_15_mais", "taxa_criancas_dom_sem_fund",
        "pib_per_capita", "taxa_freq_4_5",
    ],
    "Docentes e equipe": [
        "dsu_ef_anos_iniciais", "afd_ef_anos_iniciais_grupo_1", "alunos_por_docente_ai", "alunos_por_turma_ai",
        "pct_coordenador_pedagogico", "pct_psicologo", "pct_bibliotecario",
    ],
    "Infraestrutura escolar": [
        "pct_biblioteca_ou_sala_leitura", "pct_agua_potavel", "pct_esgoto_rede_publica", "pct_internet_alunos",
        "pct_banda_larga", "pct_laboratorio_informatica", "pct_quadra_esportes", "pct_parque_infantil",
        "pct_material_pedagogico_infantil", "pct_matricula_integral_ai",
    ],
    "Ruralidade e diversidade": [
        "pct_alunos_escola_rural", "pct_alunos_area_diferenciada", "pct_educacao_indigena", "pct_residencia_rural",
        "pct_transporte_escolar", "pct_populacao_rural_2010", "amazonia_legal",
    ],
    "Porte da rede e do município": [
        "escolas_com_2_ano", "matriculas_2_ano", "tamanho_medio_escola", "log_populacao", "capital_uf",
    ],
    "Estado (UF) e região": ["sigla_uf", "nome_regiao"],
    "Rede (estadual/municipal)": ["rede_nome"],
}
TEMA_DA_FEATURE = {feature: tema for tema, features in TEMAS.items() for feature in features}

CATEGORICAS = ["sigla_uf", "nome_regiao", "rede_nome"]


def feature_original(nome_transformado: str) -> str:
    """'missingindicator_inse_medio' -> 'inse_medio'; 'sigla_uf_CE' -> 'sigla_uf'."""
    nome = nome_transformado.removeprefix("missingindicator_")
    for categorica in CATEGORICAS:
        if nome.startswith(categorica + "_"):
            return categorica
    return nome


def calcular_shap(pipeline, X: pd.DataFrame) -> tuple[np.ndarray, pd.DataFrame]:
    """Valores SHAP (em log-odds) do modelo LightGBM, nas features já transformadas."""
    prep, modelo = pipeline.named_steps["prep"], pipeline.named_steps["modelo"]
    X_transformado = pd.DataFrame(prep.transform(X), columns=prep.get_feature_names_out(), index=X.index)
    valores = shap.TreeExplainer(modelo).shap_values(X_transformado)
    if isinstance(valores, list):  # versões antigas do SHAP devolvem uma matriz por classe
        valores = valores[1]
    return valores, X_transformado


def importancia_por_feature(valores_shap: np.ndarray, colunas: list[str]) -> pd.Series:
    """|SHAP| médio somando one-hot e indicador de ausente na feature original."""
    por_coluna = pd.Series(np.abs(valores_shap).mean(axis=0), index=colunas)
    return por_coluna.groupby(por_coluna.index.map(feature_original)).sum().sort_values(ascending=False)


def importancia_por_tema(valores_shap: np.ndarray, colunas: list[str]) -> pd.Series:
    """|soma dos SHAP do tema| por aluno, em média. Somar antes do valor absoluto
    deixa efeitos de variáveis correlacionadas se compensarem dentro do tema,
    como acontece na predição."""
    temas = pd.Index(colunas).map(lambda c: TEMA_DA_FEATURE.get(feature_original(c), "Outros"))
    por_tema = pd.DataFrame(valores_shap, columns=colunas).T.groupby(temas).sum().T
    return por_tema.abs().mean().sort_values(ascending=False)


def importancia_permutacao(pipeline, X: pd.DataFrame, y: pd.Series, repeticoes: int = 5) -> pd.DataFrame:
    """Queda de AUC ao embaralhar cada feature original (no teste), independente do modelo."""
    resultado = permutation_importance(pipeline, X, y, scoring="roc_auc", n_repeats=repeticoes,
                                       random_state=SEED, n_jobs=1)
    return (
        pd.DataFrame({"queda_auc": resultado.importances_mean, "desvio": resultado.importances_std}, index=X.columns)
        .sort_values("queda_auc", ascending=False)
    )


def efeito_por_categoria(valores_shap: np.ndarray, colunas: list[str], X_original: pd.DataFrame,
                         categorica: str) -> pd.Series:
    """Contribuição SHAP média de cada categoria (ex.: de cada UF) para os alunos dela."""
    indices = [i for i, c in enumerate(colunas) if feature_original(c) == categorica]
    contribuicao = valores_shap[:, indices].sum(axis=1)
    return pd.Series(contribuicao, index=X_original.index).groupby(X_original[categorica]).mean().sort_values()


# ---------------------------------------------------------------------------
# Gráficos
# ---------------------------------------------------------------------------

def _salvar(fig, salvar):
    fig.tight_layout()
    if salvar:
        fig.savefig(DIR_IMAGENS / f"{salvar}.png")
    return fig


def grafico_barras(serie: pd.Series, titulo: str, xlabel: str, salvar: str | None = None,
                   cor: str = "#264653", top: int | None = None) -> plt.Figure:
    serie = serie.head(top) if top else serie
    serie = serie.sort_values()
    fig, ax = plt.subplots(figsize=(8, max(3.5, 0.32 * len(serie))))
    ax.barh(serie.index, serie.values, color=cor)
    ax.set(title=titulo, xlabel=xlabel)
    return _salvar(fig, salvar)


def grafico_efeito_categoria(efeito: pd.Series, titulo: str, salvar: str | None = None) -> plt.Figure:
    cores = np.where(efeito > 0, "#264653", "#e76f51")
    fig, ax = plt.subplots(figsize=(8, max(4, 0.3 * len(efeito))))
    ax.barh(efeito.index, efeito.values, color=cores)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set(title=titulo, xlabel="contribuição SHAP média (log-odds) - positivo aumenta a chance de alfabetização")
    return _salvar(fig, salvar)


def grafico_beeswarm(valores_shap: np.ndarray, X_transformado: pd.DataFrame, salvar: str | None = None,
                     maximo: int = 15) -> plt.Figure:
    plt.figure()
    shap.summary_plot(valores_shap, X_transformado, max_display=maximo, show=False, plot_size=(9, 6.5))
    fig = plt.gcf()
    fig.axes[0].set_title("SHAP - impacto de cada feature na previsão (teste 2024)", fontweight="bold")
    return _salvar(fig, salvar)


def grafico_dependencia(valores_shap: np.ndarray, X_transformado: pd.DataFrame, features: list[str],
                        rotulos: dict[str, str], salvar: str | None = None) -> plt.Figure:
    """Valor da feature x contribuição SHAP, com a tendência média por faixa."""
    fig, eixos = plt.subplots(1, len(features), figsize=(4.2 * len(features), 4), sharey=True)
    for ax, feature in zip(np.atleast_1d(eixos), features):
        i = X_transformado.columns.get_loc(feature)
        x, y = X_transformado[feature].to_numpy(), valores_shap[:, i]
        ax.scatter(x, y, s=4, alpha=0.15, color="#264653")
        faixas = pd.qcut(x, 20, duplicates="drop")
        media = pd.DataFrame({"x": x, "y": y}).groupby(faixas, observed=True).mean()
        ax.plot(media["x"], media["y"], color="#e76f51", linewidth=2.5)
        ax.axhline(0, color="black", linewidth=0.6)
        ax.set(xlabel=rotulos.get(feature, feature), title=rotulos.get(feature, feature))
    np.atleast_1d(eixos)[0].set_ylabel("contribuição SHAP (log-odds)")
    return _salvar(fig, salvar)
