# Tech Challenge Fase 3 - Predição e Inteligência Analítica para Alfabetização no Brasil

> README em construção. As seções de insights consolidados, evoluções futuras e vídeo serão completadas na etapa final.

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

## Interpretação dos resultados

Notebook completo: [`notebooks/03_interpretabilidade.ipynb`](notebooks/03_interpretabilidade.ipynb).
Técnicas: **permutation importance**, **SHAP** (global, dependência e explicações locais) e
**SHAP agregado por tema**, que contorna a multicolinearidade entre variáveis socioeconômicas.

![Fatores por tema](images/int_04_shap_por_tema.png)

| Tema | % da importância | Variáveis principais |
|---|---|---|
| Trajetória escolar | **31%** | distorção idade-série, abandono, aprovação no 2º ano |
| Estado (UF) e região | **30%** | efeito da política/gestão estadual |
| Nível socioeconômico | **19%** | INSE, alunos com INSE baixo, pobreza infantil, renda |
| Porte da rede e do município | 6% | população, tamanho das escolas |
| Ruralidade e diversidade | 6% | escolas rurais, áreas indígenas/quilombolas/assentamentos |
| Infraestrutura escolar | 5% | biblioteca/sala de leitura, laboratório, tempo integral |
| Docentes e equipe | 4% | formação superior, adequação da formação, alunos por docente |

**Os efeitos têm limiares, não são lineares** (gráficos de dependência):
- A **distorção idade-série** ajuda até ~5% e prejudica acima de ~8%. Depois disso o efeito satura.
- **Qualquer abandono** acima de ~0,5% já muda o sinal.
- O **INSE** tem um degrau por volta de 4,8.

**O efeito do estado, descontado o contexto:**

![Efeito UF](images/int_05_efeito_uf.png)

- **Ceará (+1,06 em log-odds):** alfabetiza muito acima do que seu contexto prevê, o efeito
  associado ao PAIC, o regime de colaboração Estado-municípios em vigor desde 2007.
- **Goiás, Espírito Santo, Paraná e Pernambuco:** também entregam mais do que o contexto prevê.
- **Sergipe, Rio Grande do Norte, Tocantins e Bahia:** entregam menos.
- **Exemplo local:** um município cearense com **76% de pobreza infantil** e INSE baixo tem
  previsão de 95% de alfabetização, graças a uma rede com abandono zero, distorção de 1,9% e tempo
  integral.

## Aplicação estratégica

Notebook completo: [`notebooks/04_aplicacao_estrategica.ipynb`](notebooks/04_aplicacao_estrategica.ipynb).
Unidade de análise: a **rede municipal** de cada município, que tem metas oficiais.
Arquivos para os gestores, em `reports/`:
- `previsao_meta_2025.csv`: chance de cada rede atingir a meta de 2025.
- `ranking_risco_municipios_2024.csv`: índice de risco e seus componentes.
- `clusters_municipios.csv`: grupo de contexto e desvio em relação ao esperado.

**Modelo de metas:** aprende a transição "ano atual → ano seguinte".
- **Treino:** situação em 2023 → atingiu a meta de 2024?
- **Previsão:** situação em 2024 → vai atingir a meta de 2025?
- **Features:** taxa atual, meta, distância até a meta, tamanho da rede e contexto.

| Modelo | AUC (municípios novos) | AUC (estados novos) |
|---|---|---|
| Regra "já está acima da meta" | 0,50 | 0,50 |
| Regressão logística | 0,80 | 0,56 |
| **LightGBM** | **0,81** | **0,59** |

**Índice de risco:** média, em percentil, de três sinais:
1. a taxa observada;
2. a taxa esperada pelo contexto, segundo o modelo do aluno;
3. a probabilidade de não atingir a meta de 2025.

**Clusterização:** KMeans com k = 5 sobre 12 variáveis de **contexto**, sem o resultado da prova.

![Grupos de municípios](images/app_05_clusters.png)

## Respostas às perguntas de negócio

**Quais fatores mais impactam a alfabetização?**
Trajetória escolar (31%), estado/política estadual (30%) e nível socioeconômico (19%). Porte,
ruralidade, infraestrutura e formação docente têm peso menor. O contexto socioeconômico importa,
mas não determina o resultado: as alavancas mais fortes, fluxo escolar e regime de colaboração,
estão ao alcance da gestão pública.

**Quais variáveis possuem maior influência nos modelos?**
`sigla_uf` (sobretudo o Ceará), `tdi_ef_anos_iniciais` (distorção idade-série),
`taxa_abandono_ef_anos_iniciais`, `inse_medio` e `pct_alunos_inse_baixo`. SHAP e permutation
importance concordam no topo do ranking. Os coeficientes da logística foram descartados para
interpretação: com a multicolinearidade, alguns sinais se invertem.

**Quais municípios apresentam maior risco educacional?**
- **Por gravidade:** o risco é concentrado nas redes municipais da **Bahia** (82% delas no decil
  de maior risco, como Ilhéus, Juazeiro, Feira de Santana e Itabuna), além de **Sergipe, Rio Grande
  do Norte, Amazonas e Pará**.
- **Por volume de crianças:** em crianças não alfabetizadas, as prioridades são **São Paulo
  (~21,6 mil), Rio de Janeiro (~15,7 mil), Manaus (~9,3 mil) e Salvador (~7,7 mil)**.
- **Abaixo do esperado:** São Paulo (48% contra 56% esperados) e Guarulhos (44% contra 61%)
  alfabetizam bem menos do que o contexto deles prevê.

![Mapa de risco](images/app_03_mapa_risco.png)

**Quais regiões possuem padrões semelhantes?**
Cinco perfis de contexto:

| Grupo | Onde está | Taxa 2024 | Característica marcante |
|---|---|---|---|
| Pequenos municípios desenvolvidos | Sul/Sudeste | 71% | baixa distorção, biblioteca em todas as escolas |
| Vulnerável com fluxo escolar regular | Nordeste | 63% | pobreza infantil de 57%, mas distorção de 6% e mais tempo integral |
| Urbano de maior porte | Sudeste/Sul | 59% | contexto favorável, resultado abaixo dos pequenos |
| Áreas diferenciadas e rurais | Nordeste/Norte | 50% | 33% dos alunos em áreas indígenas, quilombolas ou de assentamento |
| Vulnerável com fluxo escolar crítico | Nordeste/Norte | 42% | distorção de 16%, abandono de 1,9%, pouca infraestrutura de leitura |

Os dois grupos vulneráveis têm **a mesma pobreza e o mesmo INSE**, mas **21 pontos de diferença**,
explicados pelo fluxo escolar. Em todos os grupos há **referências de desvio positivo**, municípios
30 a 50 pontos acima do esperado, como Tartarugalzinho (AP), Jequiá da Praia (AL) e Barreirinhas (MA).

**Como prever municípios que podem não atingir metas futuras?**
- **Com o modelo de transição.** A previsão é que **55% das redes atinjam a meta de 2025**, e
  **1.504 redes (28%) têm chance abaixo de 40%**, concentradas no **RS e na BA**.
- **Cuidado com o RS:** com uma única transição de treino (2023 → 2024, o ano das enchentes no RS),
  a previsão do RS significa "risco alto se o padrão de 2024 se repetir". A análise de
  sensibilidade, com e sem UF, está no notebook. O modelo deve ser retreinado com os resultados
  municipais de 2025.

## Aplicação prática para políticas públicas

1. **Priorização de recursos:** o ranking de risco orienta o apoio técnico e financeiro do
   Compromisso Nacional Criança Alfabetizada. O índice prioriza **gravidade**; o número de crianças
   prioriza **alcance**.
2. **Alerta precoce:** a previsão de metas identifica, **antes da prova**, as redes que precisam de
   reforço: formação de alfabetizadores, avaliação diagnóstica e material estruturado.
3. **Foco no fluxo escolar:** distorção idade-série e abandono são os fatores mais fortes e mais
   acionáveis. As ações indicadas são busca ativa, acompanhamento de frequência e recomposição de
   aprendizagem nos anos iniciais.
4. **Regime de colaboração Estado-municípios:** o efeito do Ceará indica que política estadual
   estruturada multiplica o resultado. BA, SE, RN e TO, abaixo do esperado, são candidatos a
   programas desse tipo.
5. **Aprendizagem entre pares:** os grupos de contexto e as referências de desvio positivo
   permitem montar redes de intercâmbio entre municípios parecidos.
6. **Estratégias diferenciadas:** áreas indígenas, quilombolas e de assentamento precisam de
   política específica (material bilíngue, calendário próprio), não apenas de mais recursos.

## Limitações do projeto

- **Features só de contexto:** o `id_escola` dos microdados é anonimizado pelo Inep e não cruza
  com o Censo Escolar, e não há dados socioeconômicos do aluno. Isso limita o AUC individual ao
  teto de ~0,70.
- **Só dois ciclos de avaliação (2023 e 2024):** pouca história para capturar tendências. A taxa do
  ano anterior só existe para 2024.
- **Choques não previsíveis:** em 2024 o modelo superestimou o Sul (68% previsto, 61% real), ano
  das enchentes no RS. Eventos assim pedem retreino a cada ciclo.
- **Modelo de metas com uma só transição:** treinado só com 2023 → 2024, não separa choque
  passageiro de tendência. Nos estados novos o AUC cai para 0,59.
- **Qualidade da fonte:** os Indicadores Educacionais de 2023 na Base dos Dados estão com colunas
  deslocadas, então foi usada a edição de 2022.
- **Amostra de 300 mil alunos por ano**, por limite de memória da máquina de desenvolvimento.
  Como as features são do município × rede, a perda de informação é mínima.
- **IDHM de 2010:** é o último Atlas municipal disponível e pode não refletir mudanças recentes.
- **Associação, não causalidade:** o SHAP explica o modelo, não o mundo. O "efeito UF" captura
  tudo o que é comum ao estado e não está nas features, e a ligação com programas como o PAIC é uma
  hipótese consistente com a literatura, não uma prova causal.

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
