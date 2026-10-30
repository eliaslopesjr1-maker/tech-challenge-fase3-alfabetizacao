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

### D9. LightGBM conservador e limiar escolhido no treino
A busca de hiperparâmetros escolheu árvores rasas (16 folhas) com folhas grandes (921 alunos), a
configuração com o menor gap entre treino e validação. Faz sentido porque as features são do
município × rede: folhas pequenas decorariam municípios. O limiar de decisão (0,645) foi fixado
nas predições *out-of-fold* do treino para identificar 80% dos não alfabetizados. No teste de
2024 ele identificou 78%.

### D10. Quatro candidatos e peso amostral
Logística, HistGradientBoosting, LightGBM e LightGBM com `sample_weight=peso_aluno` foram
comparados com a mesma validação e o mesmo teste, medindo o AUC simples e o ponderado. Os dois
boostings empatam (AUC de 0,631 no teste) e o peso amostral não muda o resultado. O LightGBM sem
peso foi mantido: o limite está nos dados, e a conclusão vale para a população de alunos.

### D11. Testes automatizados e amostra versionada
18 testes com pytest cobrem as regras da Gold, a qualidade, as garantias contra leakage, os
pipelines, as métricas e as regras do modelo de metas. Eles encontraram dois problemas, ambos
corrigidos: o limiar era arredondado depois de testado, e a lista de colunas proibidas não citava
explicitamente a nota e o alvo do aluno. A amostra em `data/amostra/` (6 MB) e os modelos finais
são versionados para que os notebooks rodem com `TC_AMOSTRA=1`, sem conta no Google Cloud.

### D12. Interpretação por tema, não por coeficiente
Com variáveis socioeconômicas quase redundantes, os coeficientes da logística trocam de sinal.
As conclusões usam o SHAP somado por tema, em que efeitos de variáveis correlacionadas se compensam
dentro do grupo.

## Aplicação estratégica

### D13. Modelo de metas como transição "ano atual → ano seguinte"
Treinado com a situação de 2023 (taxa, meta de 2024, contexto) para prever se a rede atingiu a
meta de 2024, e aplicado à situação de 2024 para prever a meta de 2025. A validação é feita de duas
formas: estratificada (municípios novos, AUC 0,81) e por UF (estados novos, AUC 0,59). A UF foi
mantida por ter a melhor validação, e a dependência do território está documentada numa análise
de sensibilidade. Com uma só transição, choques como as enchentes no RS em 2024 contaminam a
previsão de 2025.

### D14. Índice de risco com três componentes
Média dos percentis de: (1) taxa observada, (2) taxa esperada pelo contexto (modelo do aluno) e
(3) probabilidade de não atingir a meta. Redes com menos de 20 alunos avaliados ficam fora dos
rankings exibidos, porque a taxa delas é instável. O ranking por número de crianças não
alfabetizadas complementa o índice, mostrando alcance em vez de gravidade.

### D15. Previsão de metas conservadora diante de choques estaduais
Com uma única transição de treino, o modelo completo repete o que aconteceu em cada estado
naquele ano. Retirar a UF não resolve, porque o contexto também identifica o perfil regional. A
regra adotada usa o **cenário neutro** (só taxa, meta, distância e tamanho da rede) nos estados
cuja variação 2023 → 2024 se afastou da nacional em mais de 10 p.p. (RS, -22 p.p., ano das
enchentes; MG, +10 p.p.). Os estados sem histórico (SP e AC) ficam com confiança baixa. O limite de
10 p.p. é uma escolha de projeto: os demais estados ficaram dentro de ±7 p.p.

### D16. Clusterização só com contexto, k = 5
O KMeans usa 12 variáveis de contexto padronizadas, sem o resultado da prova, para que dê para
comparar o desempenho de municípios parecidos. A silhueta é estável (~0,15) de k = 4 a 8. O k = 5
foi escolhido porque separa as áreas indígenas, quilombolas e de assentamento, que pedem política
própria. Os nomes dos grupos são atribuídos por regras fixas sobre o perfil, para não dependerem da
numeração do KMeans.
