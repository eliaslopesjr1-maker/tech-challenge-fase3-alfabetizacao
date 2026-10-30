# Tech Challenge Fase 3 - Predição e Inteligência Analítica para Alfabetização no Brasil

> README em construção. As seções de interpretabilidade, aplicação estratégica e evoluções futuras serão completadas nas próximas etapas.

Continuação do [Tech Challenge Fase 2](https://github.com/eliaslopesjr1-maker/tech-challenge-fase2-alfabetizacao).
A camada Gold construída lá é usada aqui para análise exploratória e modelos de Machine Learning
sobre o **Indicador Criança Alfabetizada**.

## Contexto do problema

O Compromisso Nacional Criança Alfabetizada tem como meta que **80% das crianças estejam
alfabetizadas ao final do 2º ano do ensino fundamental até 2030**. O Inep considera alfabetizada a
criança com proficiência ≥ 743 pontos na avaliação de alfabetização. Em 2024, só 59,2% chegaram
lá, com diferenças de quase 50 pontos percentuais entre estados.

## Objetivo analítico

1. Prever se um aluno será **alfabetizado ou não**, a partir de variáveis educacionais, territoriais e socioeconômicas.
2. Identificar **quais fatores mais pesam** e **quais municípios estão em maior risco**.
3. Agrupar **regiões com padrões semelhantes** e antecipar **quem não deve atingir as metas futuras**.

## Base de dados

| Base | Granularidade | Origem |
|---|---|---|
| `gold/alunos` | aluno avaliado (3,35 mi em 2023-2024) | Gold da Fase 2 - Base dos Dados / Inep |
| `gold/painel_municipio_rede` | município × rede × ano (12,4 mil) | Gold + enriquecimento externo |
| `gold/indicador_*`, `gold/comparacao_meta_resultado` | município, UF, Brasil | Gold da Fase 2 |

Fontes externas usadas no enriquecimento, todas via Base dos Dados: **Censo Escolar**
(infraestrutura, matrículas, docentes), **Indicadores Educacionais do Inep** (distorção idade-série,
abandono, formação docente), **INSE** (nível socioeconômico), **IBGE** (PIB e população) e
**Atlas do Desenvolvimento Humano** (IDHM, pobreza, desigualdade).

Detalhes e justificativas: [`docs/decisoes.md`](docs/decisoes.md).

## Principais achados da análise exploratória

Notebook completo: [`notebooks/01_eda.ipynb`](notebooks/01_eda.ipynb).

![Taxa por UF](images/eda_02_taxa_por_uf.png)

- **Desigualdade territorial enorme:** de 36% (BA) a 85% (CE). O Ceará tem nível socioeconômico
  abaixo da média e o melhor resultado do país, o que indica que a política estadual pesa tanto
  quanto a renda.
- **A trajetória escolar é o fator mais associado:** distorção idade-série e abandono têm correlação
  de -0,39 e -0,40 com a taxa. Em seguida vêm o nível socioeconômico (INSE, pobreza infantil, IDHM),
  a infraestrutura pedagógica (biblioteca e sala de leitura) e a formação docente.
- **Redes rurais e de áreas diferenciadas** (indígenas, quilombolas, assentamentos) e com mais
  alunos por docente têm resultados piores.
- **O histórico prevê o futuro, com ruído:** a correlação entre 2023 e 2024 é de 0,67, com forte
  regressão à média em redes pequenas.
- **Só 53% das redes municipais atingiram a meta de 2024**, e no Sul apenas 34%.

## Etapas de modelagem

Notebook completo: [`notebooks/02_modelagem_aluno.ipynb`](notebooks/02_modelagem_aluno.ipynb).
Treino: `python -m src.modeling.treinar_aluno`.

| Etapa | Como foi feito |
|---|---|
| **Alvo** | `alfabetizado` = proficiência ≥ 743 (1) ou não (0), para cada aluno avaliado |
| **Features** | 47 numéricas de contexto (Censo Escolar, indicadores educacionais, INSE, IBGE, IDHM) + 3 categóricas (UF, região, rede), todas do município × rede do aluno |
| **Split** | **temporal**: treino com a avaliação de 2023 e teste com a de 2024 (300 mil alunos em cada) |
| **Imputação** | `SimpleImputer(strategy="median", add_indicator=True)` |
| **Transformação** | `StandardScaler` nas numéricas (logística) e `OneHotEncoder(handle_unknown="ignore", min_frequency=20)` nas categóricas |
| **Pipeline** | `ColumnTransformer` + modelo num único `Pipeline` do scikit-learn: o pré-processamento é ajustado só no treino de cada fold |
| **Validação** | `GroupKFold(5)` por município: mede a generalização para municípios não vistos |
| **Otimização** | `RandomizedSearchCV` com 12 combinações de hiperparâmetros do LightGBM (60 ajustes) |
| **Limiar** | escolhido nas predições *out-of-fold* do treino, para identificar 80% dos não alfabetizados |

**Prevenção de data leakage:**
- `proficiencia` e `alfabetizado` da fonte nunca entram como features. O resultado agregado do
  próprio ano (taxa, alunos avaliados) também fica fora.
- Todas as fontes externas usam a edição anterior à prova.
- O teste de 2024 não é usado em nenhuma decisão: nem no tuning, nem na escolha do limiar.
- O `GroupKFold` impede que alunos do mesmo município estejam no treino e na validação ao mesmo tempo.

## Escolha do algoritmo

| Critério | Regressão logística (baseline) | **LightGBM (escolhido)** |
|---|---|---|
| AUC validação cruzada | 0,647 ± 0,014 | **0,648 ± 0,008** |
| AUC teste 2024 | 0,621 | **0,631** |
| PR-AUC dos não alfabetizados | 0,516 | **0,526** |
| Brier (calibração) | 0,229 | **0,227** |

O LightGBM foi escolhido por ser melhor em todas as métricas do teste, mais estável entre os folds
e capaz de aprender interações (rede × UF) sem engenharia manual, além de ter boa interpretação
via SHAP. A busca selecionou a configuração mais conservadora (16 folhas, mínimo de 921 alunos por
folha), que tem o **menor gap entre treino e validação (0,03)**. As mais complexas superajustavam.

## Métricas de avaliação

Resultados no **teste de 2024**, com dados nunca vistos:

| Métrica | Valor | Por que importa |
|---|---|---|
| ROC-AUC | **0,631** | capacidade de ordenar alunos por risco |
| Teto teórico (AUC) | 0,698 | máximo possível com features de contexto; o modelo captura **66% do sinal disponível** |
| Recall dos não alfabetizados (limiar 0,645) | **78%** | de cada 10 crianças que não se alfabetizaram, o modelo sinaliza 8 |
| Precisão dos não alfabetizados | 46% | contra 40% de um sorteio: é triagem, não diagnóstico |
| Brier / calibração | 0,227 | as probabilidades são confiáveis: quando o modelo prevê 70%, ~70% se alfabetizam |

![Calibração](images/mod_02_calibracao.png)

**Interpretação:** o contexto explica parte relevante do risco, mas não define o destino de cada
criança. O que diferencia alunos da mesma rede no mesmo município (família, professora, turma) não
está nos dados públicos. Por isso o modelo é usado de duas formas: como **triagem** no nível
individual e como **taxa esperada calibrada** no nível município × rede, o nível certo para
priorizar recursos.

## Limitações do projeto

- **Features só de contexto:** o `id_escola` dos microdados é anonimizado pelo Inep e não cruza
  com o Censo Escolar, e não há dados socioeconômicos do aluno. Isso limita o AUC individual ao
  teto de ~0,70.
- **Só dois ciclos de avaliação (2023 e 2024):** pouca história para capturar tendências. A taxa do
  ano anterior só existe para 2024.
- **Choques não previsíveis:** em 2024 o modelo superestimou o Sul (68% previsto, 61% real), ano
  das enchentes no RS. Eventos assim pedem retreino a cada ciclo.
- **Qualidade da fonte:** os Indicadores Educacionais de 2023 na Base dos Dados estão com colunas
  deslocadas, então foi usada a edição de 2022.
- **Amostra de 300 mil alunos por ano**, por limite de memória da máquina de desenvolvimento.
  Como as features são do município × rede, a perda de informação é mínima.
- **IDHM de 2010:** é o último Atlas municipal disponível e pode não refletir mudanças recentes.

## Como reproduzir

Pré-requisitos: Python 3.13 e acesso a um projeto do Google Cloud. A consulta à Base dos Dados fica
dentro da cota gratuita do BigQuery.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

gcloud auth application-default login
set GCP_PROJECT_ID=<seu-projeto>   # opcional; padrão em src/config.py

python -m src.preprocessing.extrair_dados           # Bronze: tabelas do Inep -> data/raw/
python -m src.preprocessing.extrair_enriquecimento  # fontes externas -> data/raw/
python -m src.preprocessing.construir_gold          # Silver + Gold -> data/gold/
python -m src.preprocessing.construir_features      # painel analítico -> data/gold/
python -m src.modeling.treinar_aluno                # modelo do aluno -> models/ e reports/ (~30 min)
```

Depois é só abrir os notebooks em `notebooks/`, em ordem. Todos usam `random_state=42`.

## Estrutura

```
├── data/            # raw/ (Bronze) e gold/ - gerados pelos scripts, fora do Git
├── notebooks/       # 01_eda, modelagem, interpretabilidade, aplicação estratégica
├── src/
│   ├── preprocessing/   # extração (BigQuery), Gold, features e checagens de qualidade
│   ├── modeling/        # base de modelagem, pipelines e treino
│   ├── evaluation/      # métricas e gráficos de avaliação
│   └── visualization/   # funções de gráfico
├── reports/
├── images/          # gráficos usados no README e no vídeo
├── docs/            # decisões analíticas
└── models/          # modelos treinados - fora do Git
```

## Como o Git foi usado

- A `main` contém sempre a versão estável e revisada.
- Cada etapa é desenvolvida numa branch própria (`feature/eda`, `feature/modelagem`, ...) e
  integrada por **Pull Request**, com a descrição do que foi feito e das decisões tomadas.
- Os commits são pequenos e descrevem o *porquê* da mudança.
- As decisões analíticas ficam registradas em [`docs/decisoes.md`](docs/decisoes.md).
