# Checklist de entrega - Tech Challenge Fase 3

Cada exigência do enunciado e onde ela é atendida no repositório.

## Objetivo e base de dados

| Exigência | Onde está |
|---|---|
| Modelo supervisionado que prevê aluno alfabetizado / não alfabetizado | `src/modeling/treinar_aluno.py`, `notebooks/02_modelagem_aluno.ipynb` |
| Variáveis educacionais, territoriais e socioeconômicas | 47 features numéricas + UF, região e rede (`src/preprocessing/construir_features.py`) |
| Dados da camada Gold da Fase 2 | `src/preprocessing/construir_gold.py` reproduz a Silver/Gold da Fase 2 |
| Indicador e metas **nacionais** | `notebooks/01_eda.ipynb`, seção 1 (trajetória Brasil x meta) |
| Metas **estaduais** | `notebooks/01_eda.ipynb`, seção 5b (UFs 2023-2025 x meta); `notebooks/04`, validação externa |
| Metas **municipais** | `notebooks/01_eda.ipynb`, seção 5; `notebooks/04`, modelo de metas |
| Dados territoriais, socioeconômicos, populacionais e indicadores temporais | `data/gold/painel_municipio_rede.parquet` (2023-2024, taxa do ano anterior) |
| Enriquecimento com fontes externas | Censo Escolar, Indicadores Educacionais, INSE, IBGE (PIB, população), Atlas IDHM (`src/preprocessing/extrair_enriquecimento.py`) |

## Etapas esperadas

| Exigência | Onde está |
|---|---|
| EDA: comportamento, padrões, distribuições, correlações, variáveis relevantes | `notebooks/01_eda.ipynb`, seções 1 a 6 |
| Hipóteses analíticas que apoiam a modelagem | `notebooks/01_eda.ipynb`, seção 7 (H1 a H5) |
| Imputação de valores faltantes numéricos | `SimpleImputer(median, add_indicator=True)` em `src/modeling/pipeline.py` |
| Transformação de variáveis numéricas e categóricas / feature encoding | `StandardScaler` + `OneHotEncoder` em `src/modeling/pipeline.py` |
| Feature engineering | agregações por município × rede, percentuais ponderados, PIB per capita, log da população, distância até a meta |
| Tratamento de data leakage | split temporal, features anteriores à prova, exclusão de `proficiencia`, `GroupKFold`, limiar escolhido no treino (`notebooks/02`, seção 2) |
| Pré-processamento integrado ao modelo | `Pipeline` + `ColumnTransformer` (`src/modeling/pipeline.py`) |
| Separação treino / validação / teste | treino 2023 com validação cruzada, teste 2024 |
| Otimização e validação contra overfitting | `RandomizedSearchCV` + `GroupKFold`, análise do gap entre treino e validação (`notebooks/02`, seção 3) |
| Replicabilidade e generalização | `random_state=42`, versões fixas, `python -m src.pipeline` (testado do zero com métricas idênticas), teste temporal |
| Comparação de algoritmos | logística, HistGradientBoosting, LightGBM e LightGBM ponderado (`notebooks/02`, seção 7) |
| Boas práticas de ambiente produtivo | 18 testes automatizados (`tests/`, `python -m pytest`) |
| Feature Importance e SHAP | `notebooks/03_interpretabilidade.ipynb` |

## Perguntas de negócio

| Pergunta | Onde está |
|---|---|
| Quais fatores mais impactam a alfabetização? | `notebooks/03`, seções 3 e 8; README |
| Quais municípios apresentam maior risco educacional? | `notebooks/04`, seção 2; `reports/ranking_risco_municipios_2024.csv`; README |
| Quais regiões possuem padrões semelhantes? | `notebooks/04`, seção 3; `reports/clusters_municipios.csv`; README |
| Como prever municípios que podem não atingir metas futuras? | `notebooks/04`, seção 1; `reports/previsao_meta_2025.csv`; README |
| Quais variáveis possuem maior influência nos modelos? | `notebooks/03`, seções 1, 2 e 8; README |

## Repositório

| Exigência | Onde está |
|---|---|
| `data/`, `notebooks/`, `src/{preprocessing,modeling,evaluation,visualization}`, `reports/`, `images/` | estrutura do repositório |
| `requirements.txt`, `README.md`, `.gitignore` | raiz |
| Histórico de commits, branches, pull requests | PRs #1 a #7 (seção "Como o Git foi usado" do README) |
| Documentação das decisões analíticas | `docs/decisoes.md` (D1 a D16) |

## README

| Item | Seção |
|---|---|
| Contexto do problema | "Contexto do problema" |
| Objetivo analítico | "Objetivo analítico" |
| Descrição da base utilizada | "Base de dados" |
| Etapas de modelagem | "Etapas de modelagem" |
| Escolha do algoritmo | "Escolha do algoritmo" |
| Métricas de avaliação | "Métricas de avaliação" |
| Interpretação dos resultados | "Interpretação dos resultados" |
| Insights encontrados | "Insights encontrados" |
| Limitações do projeto | "Limitações do projeto" |
| Aplicação prática para políticas públicas | "Aplicação prática para políticas públicas" |
| Possíveis evoluções futuras | "Possíveis evoluções futuras" |

## Entregáveis finais

| Entregável | Situação |
|---|---|
| Repositório Git completo | ✅ |
| Código-fonte organizado | ✅ `src/` |
| Notebooks ou scripts | ✅ 4 notebooks executados + scripts |
| README detalhado | ✅ |
| Documentação técnica | ✅ `docs/decisoes.md`, docstrings dos módulos |
| Pipeline reproduzível | ✅ `python -m src.pipeline --notebooks`; sem Google Cloud: `TC_AMOSTRA=1` com a amostra versionada |
| Análises e visualizações | ✅ `images/` (EDA, modelagem, SHAP, mapas) |
| **Vídeo executivo (até 5 min)** | ⏳ roteiro pronto em `reports/roteiro_video.md`; **falta gravar e colocar o link no README** |
