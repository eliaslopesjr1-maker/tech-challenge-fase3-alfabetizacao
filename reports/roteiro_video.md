# Roteiro - Vídeo executivo (até 5 minutos)

**Formato:** simulação de reunião com secretários de educação e a equipe do Compromisso Nacional
Criança Alfabetizada.
**Tom:** executivo e direto. Cada número precisa de uma consequência prática.
**Duração alvo:** 4min30s, com folga de 30s.

---

## 1. Abertura: o problema (0:00 - 0:40)

**Tela:** `images/eda_01_trajetoria_brasil.png`

> "Bom dia a todos. A meta do país é ter 80% das crianças alfabetizadas ao final do 2º ano até
> 2030. Em 2024 estávamos em 59%. O resultado de 2025 trouxe boa notícia, 66%, acima da meta do
> ano. Mas a média esconde o essencial."

**Tela:** `images/eda_02_taxa_por_uf.png`

> "Entre estados, a diferença chega a quase 50 pontos: de 36% na Bahia a 85% no Ceará. A pergunta
> que trouxemos é: **onde agir, e com qual alavanca?**"

## 2. O que fizemos (0:40 - 1:10)

**Tela:** diagrama simples, ou o README na seção "Base de dados"

> "Usamos os microdados de 3,3 milhões de crianças avaliadas em 2023 e 2024 e cruzamos com Censo
> Escolar, indicadores de fluxo, nível socioeconômico, PIB e IDHM. Construímos dois modelos de
> machine learning: um que estima o risco de cada criança não se alfabetizar e outro que antecipa
> quais redes municipais não devem bater a meta do próximo ano."

## 3. Insight 1: o contexto importa, mas não é destino (1:10 - 2:10)

**Tela:** `images/int_04_shap_por_tema.png`

> "O que mais pesa na alfabetização? Em primeiro lugar, **a trajetória escolar**: redes onde as
> crianças atrasam ou abandonam nos anos iniciais. Em segundo, **o estado**, ou seja, a política
> estadual. O nível socioeconômico vem só em terceiro."

**Tela:** `images/int_05_efeito_uf.png`

> "Descontado o contexto, o Ceará alfabetiza muito acima do que sua renda faria esperar. É o
> efeito de quase 20 anos de regime de colaboração entre Estado e municípios. No outro extremo,
> Sergipe, Rio Grande do Norte, Tocantins e Bahia entregam menos do que o contexto permitiria."

**Tela:** `images/int_09_local_menor_risco.png`

> "Um exemplo: um município cearense com 76% das crianças na pobreza tem previsão de 95% de
> alfabetização. A rede dele tem abandono zero, quase nenhuma distorção idade-série e tempo integral."

## 4. Insight 2: municípios parecidos, resultados diferentes (2:10 - 3:00)

**Tela:** `images/app_05_clusters.png`

> "Agrupamos os municípios por contexto. Os dois grupos vulneráveis têm a **mesma pobreza** e o
> mesmo nível socioeconômico, mas um alfabetiza 63% e o outro 42%. São 21 pontos de diferença,
> explicados pelo fluxo escolar e pela infraestrutura de leitura. E em todos os grupos há
> municípios 30 a 50 pontos acima do esperado, como Barreirinhas, no Maranhão, e Tartarugalzinho,
> no Amapá. Eles são nossas referências."

## 5. Insight 3: onde está o risco (3:00 - 3:50)

**Tela:** `images/app_03_mapa_risco.png`

> "O índice de risco combina o resultado atual, o contexto e a chance de não bater a meta. Ele
> aponta duas listas. Por **gravidade**: 82% das redes municipais da Bahia estão no grupo de maior
> risco, além de Sergipe, Rio Grande do Norte, Amazonas e Pará. Por **volume**: só a rede de São
> Paulo tem 21 mil crianças não alfabetizadas, seguida de Rio, Manaus e Salvador."

> "Para 2025, o modelo prevê que cerca de 1.400 redes têm menos de 40% de chance de atingir a
> meta, a maioria na Bahia, onde o risco é estrutural. No Rio Grande do Sul, a queda de 2024 foi
> um choque das enchentes, e o modelo foi desenhado para não projetar esse choque como tendência."

## 6. Recomendações e valor estratégico (3:50 - 4:40)

**Tela:** lista de recomendações (README, seção "Aplicação prática para políticas públicas")

> "Nossa proposta para a gestão:
> 1. **Priorizar recursos** com o ranking de risco: gravidade para a Bahia e o Nordeste, volume
>    para as grandes capitais.
> 2. **Atacar o fluxo escolar**: busca ativa, frequência e recomposição nos anos iniciais. É a
>    alavanca mais forte e está ao nosso alcance.
> 3. **Expandir o regime de colaboração** no modelo do Ceará, começando pelos estados abaixo do
>    esperado.
> 4. **Conectar municípios parecidos** às suas referências de desvio positivo.
> 5. **Usar o alerta de metas antes da prova**, para agir no mesmo ano."

## 7. Fechamento (4:40 - 5:00)

> "Os modelos não substituem o olhar das secretarias. Eles dizem **onde olhar primeiro**. Com os
> resultados de 2025, retreinamos tudo e o alerta fica mais preciso a cada ciclo. Obrigado."

---

### Dicas de gravação

- **Formato:** grave a tela com os gráficos em tela cheia e a câmera num canto, se possível.
- **Ritmo:** cerca de 130 palavras por minuto. O texto acima tem ~700 palavras, o que dá ~4min30s.
- **Ensaio:** ensaie as transições entre gráficos; abrir as imagens em abas facilita.
- **Depois de publicar:** coloque o link do vídeo na seção "Vídeo executivo" do README.
