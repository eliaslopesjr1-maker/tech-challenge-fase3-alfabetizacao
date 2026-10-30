"""Garantias contra data leakage: nenhuma feature derivada da prova e nenhuma
fonte externa posterior à avaliação."""

import pandas as pd

from src.modeling import modelo_metas
from src.modeling.dados import ALVO, FEATURES_CATEGORICAS, NAO_FEATURES, features_numericas
from src.preprocessing import construir_features

COLUNAS_DA_PROVA = {"proficiencia", "alfabetizado", "atingiu_ponto_corte", "taxa_alfabetizacao",
                    "alunos_avaliados", "alunos_alfabetizados", "taxa_ano_anterior"}


def test_features_do_aluno_excluem_colunas_da_prova():
    painel = pd.DataFrame({coluna: [1.0] for coluna in COLUNAS_DA_PROVA | {"ano", "inse_medio", "idhm"}})
    numericas = features_numericas(painel)
    assert set(numericas) == {"inse_medio", "idhm"}
    assert not COLUNAS_DA_PROVA & set(numericas + FEATURES_CATEGORICAS)
    assert ALVO not in numericas


def test_colunas_de_resultado_estao_na_lista_de_exclusao():
    assert {"alunos_avaliados", "alunos_alfabetizados", "taxa_alfabetizacao", "taxa_ano_anterior"} <= NAO_FEATURES


def test_fontes_externas_sao_anteriores_a_avaliacao():
    for mapa in [construir_features.ANO_INDICADORES, construir_features.ANO_INSE, construir_features.ANO_IBGE]:
        for ano_avaliacao, ano_fonte in mapa.items():
            assert ano_fonte < ano_avaliacao, (mapa, ano_avaliacao)


def test_replicacao_por_ano_usa_o_ano_de_referencia():
    fonte = pd.DataFrame({"ano": [2021, 2023], "id_municipio": ["1", "1"], "inse_medio": [4.0, 5.0]})
    replicada = construir_features._por_ano_avaliacao(fonte, construir_features.ANO_INSE).set_index("ano")
    assert replicada.loc[2023, "inse_medio"] == 4.0   # avaliação 2023 usa a edição 2021
    assert replicada.loc[2024, "inse_medio"] == 5.0   # avaliação 2024 usa a edição 2023


def test_choque_estadual_descontado_da_variacao_nacional():
    treino = pd.DataFrame({
        "sigla_uf": ["RS", "RS", "SP", "SP"],
        "alunos_avaliados": [100, 100, 100, 100],
        "taxa_atual": [60.0, 60.0, 50.0, 50.0],
        "taxa_ano_seguinte": [40.0, 40.0, 52.0, 52.0],   # RS cai 20, SP sobe 2; Brasil -9
    })
    choques = modelo_metas.choques_estaduais(treino)
    assert choques["RS"] == -11.0 and choques["SP"] == 11.0
    assert (choques.abs() > modelo_metas.LIMITE_CHOQUE_PP).all()


def test_modelo_de_metas_nao_usa_o_resultado_do_ano_previsto():
    assert "taxa_ano_seguinte" not in modelo_metas.FEATURES_SITUACAO
    assert modelo_metas.ALVO not in modelo_metas.FEATURES_SITUACAO
