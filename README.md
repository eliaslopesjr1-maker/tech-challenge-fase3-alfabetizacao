# Tech Challenge Fase 3 - Predição e Inteligência Analítica para Alfabetização no Brasil

> README em construção. As seções de modelagem, resultados e aplicação serão completadas nas próximas etapas.

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
```

Depois é só abrir os notebooks em `notebooks/`, em ordem.

## Estrutura

```
├── data/            # raw/ (Bronze) e gold/ - gerados pelos scripts, fora do Git
├── notebooks/       # 01_eda, modelagem, interpretabilidade, aplicação estratégica
├── src/
│   ├── preprocessing/   # extração (BigQuery), Gold, features e checagens de qualidade
│   ├── modeling/
│   ├── evaluation/
│   └── visualization/   # funções de gráfico
├── reports/
├── images/          # gráficos usados no README e no vídeo
├── docs/            # decisões analíticas
└── models/          # modelos treinados - fora do Git
```
