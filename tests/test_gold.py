"""Regras da Silver/Gold reproduzidas da Fase 2 (dados sintéticos, sem BigQuery)."""

import pandas as pd
import pytest

from src.preprocessing.construir_gold import calcular_indicador, comparar_com_meta, desempilhar_metas
from src.preprocessing.qualidade import checar_chave_estrangeira, checar_duplicidade, checar_valores_ausentes


def _metas_municipio():
    linha = {"id_municipio": "1", "rede": "Municipal", **{f"meta_alfabetizacao_{a}": float(a - 1960) for a in range(2024, 2031)}}
    return pd.DataFrame([
        {**linha, "ano": 2023, "taxa_alfabetizacao": 50.0},
        {**linha, "ano": 2024, "taxa_alfabetizacao": 55.0},
    ])


def test_desempilhar_metas_mantem_so_a_edicao_mais_recente():
    metas = desempilhar_metas(_metas_municipio(), "municipio", ["id_municipio"])
    assert len(metas) == 7                          # uma linha por ano de meta, não 14
    assert set(metas["ano"]) == {2024}              # edição mais recente
    assert metas["ano_meta"].tolist() == list(range(2024, 2031))
    assert (metas["abrangencia"] == "municipio").all()


def test_calcular_indicador_percentual_de_alfabetizados():
    alunos = pd.DataFrame({"id_municipio": ["1"] * 4 + ["2"] * 2,
                           "atingiu_ponto_corte": [True, True, True, False, False, False]})
    indicador = calcular_indicador(alunos, ["id_municipio"]).set_index("id_municipio")
    assert indicador.loc["1", "taxa_alfabetizacao_calculada"] == 75.0
    assert indicador.loc["2", "taxa_alfabetizacao_calculada"] == 0.0
    assert indicador.loc["1", "total_alunos_avaliados"] == 4


def test_comparar_com_meta_marca_quem_atingiu():
    indicador = pd.DataFrame({"id_municipio": ["1", "2"], "taxa_alfabetizacao_calculada": [70.0, 40.0]})
    metas = pd.DataFrame({"id_municipio": ["1", "2"], "sigla_uf": [None, None], "ano": [2024, 2024],
                          "rede": ["Municipal"] * 2, "meta_percentual": [65.0, 50.0],
                          "ano_meta": [2025, 2025], "abrangencia": ["municipio"] * 2})
    comparacao = comparar_com_meta(indicador, metas, ["id_municipio"], "municipio").set_index("id_municipio")
    assert comparacao.loc["1", "atingiu_meta"] and not comparacao.loc["2", "atingiu_meta"]
    assert comparacao.loc["2", "diferenca_percentual"] == pytest.approx(-10.0)


def test_checagens_de_qualidade_detectam_problemas():
    df = pd.DataFrame({"chave": [1, 1, 2], "valor": [1.0, None, 3.0]})
    assert not checar_duplicidade(df, ["chave"], "t")["passou"]
    assert not checar_valores_ausentes(df, ["valor"], "t")[0]["passou"]
    assert not checar_chave_estrangeira(df, pd.DataFrame({"chave": [1]}), "chave", "t")["passou"]
    assert checar_duplicidade(df.drop_duplicates("chave"), ["chave"], "t")["passou"]
