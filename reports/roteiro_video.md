# Roteiro - Vídeo executivo (até 5 minutos)

**Material de apoio:** [`apresentacao_executiva.pptx`](apresentacao_executiva.pptx), com 13 slides.
A fala de cada slide também está nas **notas do apresentador** do PowerPoint (modo Apresentador).
Para regenerar: `python -m src.visualization.apresentacao`.

**Formato:** reunião simulada com secretários de educação e a equipe do Compromisso Nacional
Criança Alfabetizada.
**Duração:** ~600 palavras, cerca de **4min30s** a 135 palavras por minuto.

## O que o enunciado exige no vídeo e onde aparece

| Exigência do PDF | Slides |
|---|---|
| O problema educacional | 2 e 3 |
| Os principais insights | 5 a 11 (as 5 perguntas de negócio) |
| O valor estratégico da solução | 4, 11 e 12 |
| Como os modelos apoiam políticas públicas | 9, 10 e 12 |
| Simular uma reunião executiva com gestores | tom e fala de todos os slides |

## Roteiro slide a slide

| # | Slide | Tempo | Fala |
|---|---|---|---|
| 1 | Capa: "onde agir e com qual alavanca" | 0:00 | "Bom dia a todos. Vou apresentar o que os dados de alfabetização nos dizem sobre onde agir e com qual alavanca para chegar à meta de 80% de crianças alfabetizadas até 2030." |
| 2 | Onde estamos e as 5 perguntas | 0:15 | "O Brasil avançou: de 56% em 2023 para 66% em 2025, acima da meta do ano. Mas ainda faltam 14 pontos até 2030, e a média esconde o essencial. Trouxemos respostas para cinco perguntas de negócio." |
| 3 | O problema: desigualdade entre estados | 0:30 | "A diferença entre estados chega a quase 50 pontos: 36% na Bahia e 85% no Ceará em 2024. A pergunta que trouxemos é onde agir, e com qual alavanca." |
| 4 | Como chegamos às respostas | 0:45 | "Usamos os microdados de 3,3 milhões de crianças e cruzamos com Censo Escolar, fluxo escolar, nível socioeconômico, PIB e IDHM. Construímos dois modelos: um estima o risco de cada criança e outro antecipa quais redes não devem bater a meta. Tudo foi validado com dados que o modelo nunca viu." |
| 5 | **Pergunta 1:** quais fatores mais impactam? | 1:10 | "O que mais pesa? Em primeiro lugar, a trajetória escolar: redes onde as crianças atrasam ou abandonam nos anos iniciais. Em segundo, o estado, ou seja, a política estadual. O nível socioeconômico vem só em terceiro. As duas alavancas mais fortes estão ao alcance da gestão." |
| 6 | **Pergunta 2:** quais variáveis mais influenciam? | 1:30 | "Descontado o contexto, o Ceará alfabetiza muito acima do que sua renda faria esperar, efeito associado a quase 20 anos de regime de colaboração com os municípios. Sergipe, Rio Grande do Norte, Tocantins e Bahia entregam menos do que poderiam. E os efeitos têm limiares: acima de 8% de distorção ou de meio por cento de abandono, a chance cai." |
| 7 | Contexto não é destino | 1:55 | "Um exemplo: um município cearense com 76% das crianças na pobreza tem previsão de 95% de alfabetização. A rede tem abandono zero, quase nenhuma distorção idade-série e tempo integral. O contexto importa, mas não decide sozinho." |
| 8 | **Pergunta 3:** quais regiões são semelhantes? | 2:10 | "Agrupamos os municípios por contexto. Os dois grupos vulneráveis têm a mesma pobreza e o mesmo nível socioeconômico, mas um alfabetiza 63% e o outro 42%. São 21 pontos, explicados pelo fluxo escolar. E em todo grupo há municípios-referência, como Barreirinhas, no Maranhão." |
| 9 | **Pergunta 4:** quais municípios têm maior risco? | 2:30 | "O índice de risco combina o resultado atual, o contexto e a chance de não bater a meta. Por gravidade, 84% das redes municipais da Bahia estão no grupo de maior risco. Por volume, só a rede de São Paulo tem 21 mil crianças não alfabetizadas, abaixo do que o contexto permitiria, seguida de Rio, Manaus e Salvador." |
| 10 | **Pergunta 5:** como prever quem não vai bater a meta? | 2:55 | "Para as metas, o modelo aprende como as redes se saíram de um ano para o outro e projeta a chance de cada uma bater a meta de 2025. Cerca de 1.400 redes têm menos de 40% de chance. O Rio Grande do Sul caiu 22 pontos em 2024 por causa das enchentes, e o modelo foi desenhado para não projetar esse choque como tendência." |
| 11 | Validação com 2025 | 3:25 | "Comparamos a previsão com o que aconteceu em 2025 nos estados. O modelo acertou a direção: os estados apontados como mais seguros bateram a meta. Mas foi conservador, porque 2025 teve um avanço muito maior que o esperado. A Bahia, a mais crítica, deu o maior salto do país. Ela continua entre as menores taxas e precisa de prioridade, e o que mudou lá merece ser estudado." |
| 12 | Cinco recomendações | 3:55 | "Nossa proposta: primeiro, priorizar recursos com o ranking de risco. Segundo, atacar o fluxo escolar nos anos iniciais. Terceiro, expandir o regime de colaboração no modelo do Ceará. Quarto, conectar municípios parecidos às suas referências. E quinto, usar o alerta de metas antes da prova, para agir no mesmo ano." |
| 13 | Mensagem final | 4:20 | "Os modelos não substituem o olhar das secretarias: eles dizem onde olhar primeiro. Com os resultados de 2025, retreinamos tudo, e o alerta fica mais preciso a cada ciclo. Obrigado." |

## Dicas de gravação

- **Modo Apresentador:** abra o .pptx em "Apresentação de Slides → Usar o modo de exibição do
  apresentador". A fala aparece nas notas, só para você.
- **Gravação:** o próprio PowerPoint grava ("Gravar → Do início"), com sua voz e, se quiser,
  sua câmera no canto. Depois, exporte com "Arquivo → Exportar → Criar um vídeo". Também dá para
  usar OBS, Teams ou Zoom, gravando a tela.
- **Ensaio:** ensaie uma vez cronometrando. Se passar de 5 minutos, encurte as falas dos slides
  6, 10 e 11, que são as mais longas.
- **Depois de publicar:** coloque o link na seção "Vídeo executivo" do README.
