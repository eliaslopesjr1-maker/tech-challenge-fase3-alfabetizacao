"""Fontes externas de enriquecimento (também da Base dos Dados / BigQuery).

A tabela de alunos só traz ano, rede, município e um `id_escola` ANONIMIZADO
pelo Inep (códigos sequenciais 60000001..60042811 que não existem no Censo
Escolar). Por isso não dá para ligar o aluno à sua escola real, e o contexto
escolar entra no modelo agregado por **município x rede** (estadual/municipal) -
que é exatamente a unidade de gestão das políticas de alfabetização.

Fontes:
- Censo Escolar (escola): infraestrutura, localização, matrículas, docentes, turmas
  - só escolas com turma de 2º ano, ponderado pelas matrículas de 2º ano
- Indicadores Educacionais do Inep (município x rede): fluxo, distorção idade-série,
  formação docente
- INSE (escola): Indicador de Nível Socioeconômico, média ponderada por alunos
- IBGE: PIB e população do município
- Atlas do Desenvolvimento Humano (Censo 2010): IDHM, pobreza, desigualdade

As agregações são feitas no BigQuery para baixar só algumas dezenas de milhares
de linhas (a máquina de desenvolvimento tem pouca memória livre).

Uso:
    python -m src.preprocessing.extrair_enriquecimento [--forcar]
"""

import argparse

from google.cloud import bigquery

from src.config import DIR_RAW, GCP_PROJECT_ID


def _pct_ponderado(coluna: str, apelido: str) -> str:
    """% de alunos do 2º ano em escolas onde `coluna` = 1."""
    return (f"SAFE_DIVIDE(SUM(IF({coluna} = 1, quantidade_matricula_fundamental_2_ano, 0)), "
            f"SUM(quantidade_matricula_fundamental_2_ano)) AS {apelido}")


FLAGS_CENSO = {
    "agua_potavel": "pct_agua_potavel",
    "esgoto_rede_publica": "pct_esgoto_rede_publica",
    "internet_alunos": "pct_internet_alunos",
    "banda_larga": "pct_banda_larga",
    "laboratorio_informatica": "pct_laboratorio_informatica",
    "quadra_esportes": "pct_quadra_esportes",
    "parque_infantil": "pct_parque_infantil",
    "material_pedagogico_infantil": "pct_material_pedagogico_infantil",
    "profissional_coordenador": "pct_coordenador_pedagogico",
    "profissional_psicologo": "pct_psicologo",
    "profissional_bibliotecario": "pct_bibliotecario",
    "educacao_indigena": "pct_educacao_indigena",
}

CONSULTAS = {
    "censo_municipio_rede": f"""
        SELECT
            ano, id_municipio, rede,
            COUNT(*) AS escolas_com_2_ano,
            SUM(quantidade_matricula_fundamental_2_ano) AS matriculas_2_ano,
            SAFE_DIVIDE(SUM(IF(tipo_localizacao = '2', quantidade_matricula_fundamental_2_ano, 0)),
                        SUM(quantidade_matricula_fundamental_2_ano)) AS pct_alunos_escola_rural,
            SAFE_DIVIDE(SUM(IF(SAFE_CAST(tipo_localizacao_diferenciada AS FLOAT64) IN (1, 2, 3), quantidade_matricula_fundamental_2_ano, 0)),
                        SUM(quantidade_matricula_fundamental_2_ano)) AS pct_alunos_area_diferenciada,
            SAFE_DIVIDE(SUM(IF(biblioteca = 1 OR sala_leitura = 1, quantidade_matricula_fundamental_2_ano, 0)),
                        SUM(quantidade_matricula_fundamental_2_ano)) AS pct_biblioteca_ou_sala_leitura,
            {", ".join(_pct_ponderado(c, a) for c, a in FLAGS_CENSO.items())},
            SAFE_DIVIDE(SUM(quantidade_matricula_fundamental_anos_iniciais),
                        SUM(quantidade_turma_fundamental_anos_iniciais)) AS alunos_por_turma_ai,
            SAFE_DIVIDE(SUM(quantidade_matricula_fundamental_anos_iniciais),
                        SUM(quantidade_docente_fundamental_anos_iniciais)) AS alunos_por_docente_ai,
            SAFE_DIVIDE(SUM(quantidade_matricula_fundamental_anos_iniciais_integral),
                        SUM(quantidade_matricula_fundamental_anos_iniciais)) AS pct_matricula_integral_ai,
            SAFE_DIVIDE(SUM(quantidade_matricula_zona_residencia_rural),
                        SUM(quantidade_matricula_educacao_basica)) AS pct_residencia_rural,
            SAFE_DIVIDE(SUM(quantidade_matricula_utiliza_transporte_publico),
                        SUM(quantidade_matricula_educacao_basica)) AS pct_transporte_escolar,
            AVG(quantidade_matricula_educacao_basica) AS tamanho_medio_escola
        FROM `basedosdados.br_inep_censo_escolar.escola`
        WHERE ano IN (2023, 2024)
          AND rede IN ('2', '3')
          AND quantidade_matricula_fundamental_2_ano > 0
        GROUP BY ano, id_municipio, rede
    """,
    # Só 2022: na Base dos Dados, a edição 2023 dos indicadores está com as
    # colunas deslocadas (ex: abandono médio de 23% nos anos iniciais e jornada
    # de 0,4 h/dia), então 2022 - o último ano íntegro e anterior às duas
    # avaliações - é usado para 2023 e 2024. Em 2022 os rótulos de rede e
    # localização vêm em minúsculas.
    "indicadores_municipio_rede": f"""
        SELECT
            ano, id_municipio,
            CASE rede WHEN 'estadual' THEN '2' WHEN 'municipal' THEN '3' END AS rede,
            {", ".join(f"SAFE_CAST({c} AS FLOAT64) AS {c}" for c in [
                "atu_ef_2_ano", "had_ef_anos_iniciais", "tdi_ef_anos_iniciais",
                "taxa_aprovacao_ef_2_ano", "taxa_abandono_ef_anos_iniciais",
                "dsu_ef_anos_iniciais", "afd_ef_anos_iniciais_grupo_1",
            ])}
        FROM `basedosdados.br_inep_indicadores_educacionais.municipio`
        WHERE ano = 2022 AND localizacao = 'total' AND rede IN ('estadual', 'municipal')
    """,
    # Edições 2021 e 2023: cada avaliação usa a edição publicada ANTES dela.
    "inse_municipio_rede": """
        SELECT
            ano, id_municipio, rede,
            SAFE_DIVIDE(SUM(inse * quantidade_alunos_inse), SUM(quantidade_alunos_inse)) AS inse_medio,
            SAFE_DIVIDE(SUM((percentual_nivel_1 + percentual_nivel_2) * quantidade_alunos_inse),
                        SUM(quantidade_alunos_inse)) AS pct_alunos_inse_baixo
        FROM `basedosdados.br_inep_indicador_nivel_socioeconomico.escola`
        WHERE ano IN (2021, 2023) AND rede IN ('2', '3')
        GROUP BY ano, id_municipio, rede
    """,
    "pib_municipio": """
        SELECT ano, id_municipio, pib
        FROM `basedosdados.br_ibge_pib.municipio`
        WHERE ano IN (2022, 2023)
    """,
    "populacao_municipio": """
        SELECT ano, id_municipio, populacao
        FROM `basedosdados.br_ibge_populacao.municipio`
        WHERE ano IN (2022, 2023, 2024)
    """,
    "adh_municipio": """
        SELECT id_municipio, idhm, idhm_e, idhm_l, idhm_r, indice_gini, renda_pc,
               prop_pobreza_criancas, taxa_analfabetismo_15_mais, taxa_criancas_dom_sem_fund,
               taxa_freq_4_5, SAFE_DIVIDE(populacao_rural, populacao) AS pct_populacao_rural_2010
        FROM `basedosdados.mundo_onu_adh.municipio`
        WHERE ano = 2010
    """,
}


def extrair(forcar: bool = False) -> None:
    DIR_RAW.mkdir(parents=True, exist_ok=True)
    cliente = bigquery.Client(project=GCP_PROJECT_ID)

    for nome, consulta in CONSULTAS.items():
        destino = DIR_RAW / f"{nome}.parquet"
        if destino.exists() and not forcar:
            print(f"já existe, pulando: {destino.name}")
            continue

        print(f"baixando {nome}...")
        df = cliente.query(consulta).to_dataframe()
        df.to_parquet(destino, index=False)
        print(f"OK: {destino.name} ({len(df):,} linhas)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--forcar", action="store_true", help="baixa de novo mesmo se o arquivo já existir")
    extrair(parser.parse_args().forcar)
