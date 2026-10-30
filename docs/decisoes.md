# Decisões analíticas e técnicas

Registro das decisões tomadas ao longo do projeto, com a justificativa de cada uma.

## Dados

### D1. Gold reconstruída localmente, sem Databricks
A conta Databricks usada na Fase 2 ficou sem acesso a compute. Como a fonte original é a Base dos
Dados no BigQuery, as regras de Silver e Gold da Fase 2 foram reescritas em pandas
(`src/preprocessing/construir_gold.py`), mantendo a mesma lógica: deduplicação determinística de
alunos, ponto de corte de 743 pontos e desempilhamento das metas mantendo a edição mais recente.
A ingestão de streaming simulado da Fase 2 não foi reproduzida, porque gerava dados fictícios.

### D2. Taxas ponderadas por `peso_aluno`
A Gold da Fase 2 calculava a taxa como média simples dos alunos. Com o peso amostral, a taxa
nacional de 2024 fica em **59,2%, exatamente o valor oficial do Inep** (sem peso: 59,8%). Todas as
análises agregadas da Fase 3 usam a versão ponderada.

### D3. Contexto escolar agregado por município × rede
O `id_escola` dos microdados de alfabetização é **anonimizado** pelo Inep: são códigos sequenciais
de 60000001 a 60042811, que não existem no Censo Escolar. Por isso não é possível ligar o aluno à
sua escola real. As variáveis de escola (Censo, INSE) foram agregadas por **município × rede**, com
peso pelas matrículas do 2º ano. Essa é a unidade que executa a política de alfabetização (a rede
municipal ou a estadual de cada município).

### D4. Indicadores educacionais de 2022
Na Base dos Dados, a edição de 2023 dos Indicadores Educacionais do Inep está com as colunas
deslocadas. Exemplos: abandono médio de 23% nos anos iniciais (o real é ~1%) e jornada de 0,4 h/dia
(o real é ~4,8). A edição de 2022 é coerente e anterior às duas avaliações, então foi usada para
2023 e para 2024.

### D5. Nenhuma feature posterior à avaliação
| Fonte | Avaliação 2023 | Avaliação 2024 |
|---|---|---|
| Censo Escolar | 2023 (maio) | 2024 (maio) |
| Indicadores educacionais | 2022 | 2022 |
| INSE | edição 2021 | edição 2023 |
| PIB / população | 2022 | 2023 |
| Atlas IDHM | 2010 | 2010 |

As provas de alfabetização são aplicadas em outubro/novembro, depois da coleta do Censo.

## Modelagem

### D6. Validação temporal (treino 2023 → teste 2024)
Simula o uso real do modelo, que é prever o próximo ciclo de avaliação com o que se sabe hoje, e
impede que qualquer informação do teste influencie o treino. Dentro do treino, a validação cruzada
usa `GroupKFold` por município, para medir a generalização para municípios não vistos (alunos do
mesmo município compartilham as mesmas features e inflariam a métrica num split aleatório).

### D7. Exclusões contra data leakage
- `proficiencia` e `alfabetizado` (da fonte) definem o alvo e nunca entram como features.
- As metas municipais não entram no modelo de alunos, porque a meta de 2024 foi calculada a partir
  do resultado de 2023.
- A `taxa_ano_anterior` só existe para 2024 e entra apenas no modelo de metas municipais.

### D8. Imputação dentro do pipeline
Os valores ausentes são poucos (< 5%, sobretudo INSE). São imputados pela mediana com
`SimpleImputer(add_indicator=True)` dentro do `Pipeline`, então a mediana é calculada só nos dados
de treino de cada fold.
