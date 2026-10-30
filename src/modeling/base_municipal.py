"""Base municipal (rede municipal) usada na aplicação estratégica.

Uma linha por município com rede municipal avaliada no ano, juntando o painel
(resultado + contexto), as metas oficiais 2024-2030 (definidas pelo Inep a
partir do resultado de 2023) e as coordenadas do município.
"""

import pandas as pd

from src.config import ANOS_META, DIR_RAW
from src.modeling.dados import carregar_painel


def carregar_metas_municipais() -> pd.DataFrame:
    """As edições 2023 e 2024 da tabela trazem a mesma trajetória de metas;
    fica uma linha por município (a edição mais recente)."""
    metas = pd.read_parquet(DIR_RAW / "meta_alfabetizacao_municipio.parquet")
    metas = metas.sort_values("ano").drop_duplicates("id_municipio", keep="last")
    # percentual_participacao da edição mais recente = participação na avaliação de 2024
    metas = metas.rename(columns={"percentual_participacao": "participacao_2024"})
    colunas = ["id_municipio", *[f"meta_alfabetizacao_{ano}" for ano in ANOS_META], "participacao_2024"]
    return metas[colunas]


def carregar_base_municipal(ano: int) -> pd.DataFrame:
    painel = carregar_painel()
    base = painel[(painel["ano"] == ano) & (painel["rede"] == "3")]
    coordenadas = pd.read_parquet(DIR_RAW / "diretorio_municipio.parquet",
                                  columns=["id_municipio", "longitude", "latitude"])
    base = (
        base.merge(carregar_metas_municipais(), on="id_municipio", how="left")
        .merge(coordenadas, on="id_municipio", how="left")
        .reset_index(drop=True)
    )
    coluna_meta = f"meta_alfabetizacao_{ano}"
    if coluna_meta in base:
        # 1/0 quando há meta para o ano; nulo quando o município não tem meta definida.
        atingiu = (base["taxa_alfabetizacao"] >= base[coluna_meta]).astype(float)
        base["atingiu_meta_no_ano"] = atingiu.where(base[coluna_meta].notna())
    return base
