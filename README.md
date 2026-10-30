# Tech Challenge Fase 3 - Predição e Inteligência Analítica para Alfabetização no Brasil

> README em construção - será completado ao longo do projeto.

Continuação do [Tech Challenge Fase 2](https://github.com/eliaslopesjr1-maker/tech-challenge-fase2-alfabetizacao):
a camada Gold construída lá é usada aqui para análise exploratória e modelos de
Machine Learning sobre o **Indicador Criança Alfabetizada**.

## Como reproduzir

Pré-requisitos: Python 3.13 e acesso a um projeto do Google Cloud (a consulta à
Base dos Dados fica dentro da cota gratuita do BigQuery).

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

gcloud auth application-default login
set GCP_PROJECT_ID=<seu-projeto>   # opcional; padrão em src/config.py

python -m src.preprocessing.extrair_dados    # Bronze: baixa as tabelas para data/raw/
python -m src.preprocessing.construir_gold   # Silver + Gold: gera data/gold/
```

## Estrutura

```
├── data/            # raw/ (Bronze) e gold/ - gerados pelos scripts, fora do Git
├── notebooks/       # EDA, modelagem, interpretabilidade, aplicação estratégica
├── src/
│   ├── preprocessing/   # extração (BigQuery) e construção da Gold
│   ├── modeling/
│   ├── evaluation/
│   └── visualization/
├── reports/
├── images/
├── docs/            # decisões analíticas
└── models/          # modelos treinados - fora do Git
```

## Decisões já tomadas

- **Gold reconstruída localmente em pandas** (Databricks indisponível): mesmas regras da Fase 2
  (deduplicação, ponto de corte de 743, desempilhamento das metas). A parte de streaming
  simulado da Fase 2 não é reproduzida - só dados reais.
- **Validação contra o número oficial**: a taxa nacional de 2024 ponderada por `peso_aluno`
  é 59,2%, exatamente o valor publicado pelo Inep. A taxa sem ponderação (como na Fase 2)
  fica em 59,8% - por isso as análises agregadas da Fase 3 usam a versão ponderada.
