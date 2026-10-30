"""Funções de gráfico reaproveitadas pelos notebooks.

Todas recebem DataFrames já preparados, desenham com um estilo único e, quando
`salvar` é informado, gravam o PNG em images/ para uso no README e no vídeo.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.config import DIR_IMAGENS

CORES_REGIAO = {
    "Norte": "#2a9d8f",
    "Nordeste": "#e76f51",
    "Centro-Oeste": "#e9c46a",
    "Sudeste": "#264653",
    "Sul": "#8a5cf6",
}
COR_PRINCIPAL = "#264653"
COR_DESTAQUE = "#e76f51"


def configurar_estilo() -> None:
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams.update({
        "figure.dpi": 110,
        "savefig.dpi": 150,
        "savefig.bbox": "tight",
        "axes.titleweight": "bold",
        "axes.titlesize": 13,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def _finalizar(fig: plt.Figure, salvar: str | None) -> plt.Figure:
    fig.tight_layout()
    if salvar:
        DIR_IMAGENS.mkdir(exist_ok=True)
        fig.savefig(DIR_IMAGENS / f"{salvar}.png")
    return fig


def trajetoria_brasil(resultados: pd.Series, metas: pd.Series, salvar: str | None = None) -> plt.Figure:
    """Taxa nacional observada (por ano) contra a trajetória de metas até 2030."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(metas.index, metas.values, "--o", color="grey", label="Meta nacional")
    ax.plot(resultados.index, resultados.values, "-o", color=COR_DESTAQUE, linewidth=2.5, label="Resultado")
    for ano, valor in resultados.items():
        ax.annotate(f"{valor:.1f}%", (ano, valor), textcoords="offset points", xytext=(0, 9), ha="center")
    ax.set(title="Brasil: % de crianças alfabetizadas x meta", xlabel="", ylabel="% alfabetizadas", ylim=(40, 85))
    ax.legend(loc="lower right")
    return _finalizar(fig, salvar)


def barras_uf(df: pd.DataFrame, valor: str, salvar: str | None = None, titulo: str = "") -> plt.Figure:
    """Barras horizontais por UF, coloridas pela região. df: sigla_uf, nome_regiao, valor."""
    df = df.sort_values(valor)
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.barh(df["sigla_uf"], df[valor], color=df["nome_regiao"].map(CORES_REGIAO))
    media = df[valor].mean()
    ax.axvline(media, color="black", linestyle=":", linewidth=1)
    ax.text(media, -1.2, f"média das UFs {media:.1f}%", ha="center", fontsize=9)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in CORES_REGIAO.values()]
    ax.legend(handles, CORES_REGIAO.keys(), loc="lower right", frameon=True)
    ax.set(title=titulo, xlabel="% alfabetizadas", ylabel="")
    return _finalizar(fig, salvar)


def distribuicao_por_grupo(df: pd.DataFrame, valor: str, grupo: str, salvar: str | None = None,
                           titulo: str = "", ordem: list | None = None) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    paleta = CORES_REGIAO if grupo == "nome_regiao" else None
    sns.boxplot(data=df, x=grupo, y=valor, hue=grupo, order=ordem, palette=paleta, legend=False,
                ax=ax, fliersize=1.5, linewidth=1)
    ax.set(title=titulo, xlabel="", ylabel="% alfabetizadas")
    return _finalizar(fig, salvar)


def histograma(serie: pd.Series, salvar: str | None = None, titulo: str = "", xlabel: str = "",
               linha: float | None = None, rotulo_linha: str = "") -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(serie.dropna(), bins=50, color=COR_PRINCIPAL, alpha=0.85)
    if linha is not None:
        ax.axvline(linha, color=COR_DESTAQUE, linewidth=2)
        ax.text(linha, ax.get_ylim()[1] * 0.95, f" {rotulo_linha}", color=COR_DESTAQUE, va="top")
    ax.set(title=titulo, xlabel=xlabel, ylabel="quantidade")
    return _finalizar(fig, salvar)


def correlacoes_com_alvo(correlacoes: pd.Series, salvar: str | None = None, titulo: str = "",
                         xlabel: str = "correlação de Spearman com a taxa de alfabetização") -> plt.Figure:
    correlacoes = correlacoes.sort_values()
    cores = np.where(correlacoes > 0, COR_PRINCIPAL, COR_DESTAQUE)
    fig, ax = plt.subplots(figsize=(8, max(4, 0.28 * len(correlacoes))))
    ax.barh(correlacoes.index, correlacoes.values, color=cores)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set(title=titulo, xlabel=xlabel)
    return _finalizar(fig, salvar)


def heatmap_correlacao(df: pd.DataFrame, salvar: str | None = None, titulo: str = "") -> plt.Figure:
    corr = df.corr(method="spearman")
    mascara = np.triu(np.ones_like(corr, dtype=bool))
    fig, ax = plt.subplots(figsize=(10, 8.5))
    sns.heatmap(corr, mask=mascara, cmap="RdBu_r", center=0, vmin=-1, vmax=1, annot=True, fmt=".1f",
                annot_kws={"size": 7}, linewidths=0.5, cbar_kws={"shrink": 0.7}, ax=ax)
    ax.set_title(titulo)
    return _finalizar(fig, salvar)


def dispersao_por_regiao(df: pd.DataFrame, x: str, y: str, salvar: str | None = None, titulo: str = "",
                         xlabel: str = "", ylabel: str = "% alfabetizadas", tamanho: str | None = None) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.scatterplot(data=df, x=x, y=y, hue="nome_regiao", palette=CORES_REGIAO, size=tamanho,
                    sizes=(5, 120) if tamanho else None, alpha=0.45, linewidth=0, ax=ax, legend="brief")
    sns.regplot(data=df, x=x, y=y, scatter=False, color="black", line_kws={"linewidth": 1.5}, ax=ax)
    ax.set(title=titulo, xlabel=xlabel or x, ylabel=ylabel)
    handles, rotulos = ax.get_legend_handles_labels()
    regioes = [(h, r) for h, r in zip(handles, rotulos) if r in CORES_REGIAO]
    ax.legend(*zip(*regioes), title="", loc="best", fontsize=8)
    return _finalizar(fig, salvar)


def taxa_por_faixa(df: pd.DataFrame, variavel: str, alvo: str, peso: str, salvar: str | None = None,
                   titulo: str = "", xlabel: str = "", faixas: int = 5) -> plt.Figure:
    """Taxa ponderada do alvo por quintil (ou outra divisão) de uma variável."""
    dados = df[[variavel, alvo, peso]].dropna().copy()
    dados["faixa"] = pd.qcut(dados[variavel], faixas, duplicates="drop")
    resumo = dados.groupby("faixa", observed=True).apply(
        lambda g: np.average(g[alvo], weights=g[peso]), include_groups=False
    )
    fig, ax = plt.subplots(figsize=(8, 4))
    rotulos = [f"{i.left:.2f}–{i.right:.2f}" for i in resumo.index]
    barras = ax.bar(rotulos, resumo.values, color=COR_PRINCIPAL)
    ax.bar_label(barras, fmt="%.1f%%", padding=2)
    ax.set(title=titulo, xlabel=xlabel, ylabel="% alfabetizadas", ylim=(0, max(resumo.values) * 1.15))
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    return _finalizar(fig, salvar)
