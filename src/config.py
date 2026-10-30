"""Configurações compartilhadas do projeto (caminhos, projeto GCP, constantes)."""

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DIR_DADOS = RAIZ / "data"

# Com TC_AMOSTRA=1, notebooks e funções leem a amostra versionada em data/amostra/
# (gerada por src/preprocessing/gerar_amostra.py), sem precisar do BigQuery.
USAR_AMOSTRA = os.environ.get("TC_AMOSTRA") == "1"
DIR_AMOSTRA = DIR_DADOS / "amostra"
DIR_RAW = (DIR_AMOSTRA if USAR_AMOSTRA else DIR_DADOS) / "raw"
DIR_GOLD = (DIR_AMOSTRA if USAR_AMOSTRA else DIR_DADOS) / "gold"
DIR_MODELOS = RAIZ / "models"
DIR_REPORTS = RAIZ / "reports"
DIR_IMAGENS = RAIZ / "images"

# Projeto do Google Cloud usado só para "pagar" as consultas na Base dos Dados
# (dentro da cota gratuita de 1 TB/mês do BigQuery). Pode ser sobrescrito pela
# variável de ambiente GCP_PROJECT_ID.
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "tech-challenge-alfabet-3340")

# Regra oficial do Inep para o Indicador Criança Alfabetizada (mesma da Fase 2).
PONTO_DE_CORTE_ALFABETIZACAO = 743

ANOS_META = list(range(2024, 2031))

SEED = 42
