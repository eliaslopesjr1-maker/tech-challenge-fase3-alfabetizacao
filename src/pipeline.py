"""Executa o projeto de ponta a ponta com um único comando.

Etapas (na ordem):
1. extrair_dados          - tabelas do Inep e diretórios (BigQuery) -> data/raw/
2. extrair_enriquecimento - Censo Escolar, indicadores, INSE, IBGE, Atlas -> data/raw/
3. construir_gold         - Silver + Gold da Fase 2 em pandas -> data/gold/
4. construir_features     - painel município x rede x ano -> data/gold/
5. treinar_aluno          - modelo supervisionado do aluno -> models/, reports/
6. notebooks (opcional)   - executa os 4 notebooks, regenerando gráficos e relatórios

Uso:
    python -m src.pipeline                 # etapas 1 a 5 (~40 min na primeira vez)
    python -m src.pipeline --notebooks     # etapas 1 a 6
    python -m src.pipeline --a-partir-de treinar_aluno --notebooks
"""

import argparse
import subprocess
import sys
import time

from src.config import RAIZ
from src.modeling import treinar_aluno
from src.preprocessing import construir_features, construir_gold, extrair_dados, extrair_enriquecimento

ETAPAS = {
    "extrair_dados": extrair_dados.extrair,
    "extrair_enriquecimento": extrair_enriquecimento.extrair,
    "construir_gold": construir_gold.construir,
    "construir_features": construir_features.construir,
    "treinar_aluno": treinar_aluno.treinar,
}

NOTEBOOKS = [
    "01_eda.ipynb",
    "02_modelagem_aluno.ipynb",
    "03_interpretabilidade.ipynb",
    "04_aplicacao_estrategica.ipynb",
]


def executar_notebooks() -> None:
    for notebook in NOTEBOOKS:
        print(f"\n>>> executando notebooks/{notebook}")
        subprocess.run(
            [sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace",
             notebook, "--ExecutePreprocessor.timeout=1800"],
            cwd=RAIZ / "notebooks", check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--a-partir-de", choices=list(ETAPAS), default="extrair_dados",
                        help="pula as etapas anteriores (os arquivos delas precisam existir)")
    parser.add_argument("--notebooks", action="store_true", help="executa também os notebooks no final")
    argumentos = parser.parse_args()

    nomes = list(ETAPAS)
    for nome in nomes[nomes.index(argumentos.a_partir_de):]:
        inicio = time.time()
        print(f"\n===== {nome}")
        ETAPAS[nome]()
        print(f"===== {nome} concluída em {(time.time() - inicio) / 60:.1f} min")

    if argumentos.notebooks:
        executar_notebooks()


if __name__ == "__main__":
    main()
