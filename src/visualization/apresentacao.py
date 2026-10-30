"""Gera a apresentação executiva (reports/apresentacao_executiva.pptx) usada no vídeo.

Um slide por pergunta de negócio, com a resposta e os dados que a sustentam.
As notas do apresentador trazem a fala de cada slide (~5 minutos no total).

Os números vêm dos notebooks 01 a 04 e de reports/; os gráficos, de images/.

Uso:
    python -m src.visualization.apresentacao
"""

from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from src.config import DIR_IMAGENS, DIR_REPORTS

# Paleta dos gráficos do projeto (src/visualization/graficos.py)
ESCURO = RGBColor(0x26, 0x46, 0x53)
CORAL = RGBColor(0xE7, 0x6F, 0x51)
TEAL = RGBColor(0x2A, 0x9D, 0x8F)
AMARELO = RGBColor(0xE9, 0xC4, 0x6A)
LARANJA = RGBColor(0xF4, 0xA2, 0x61)
TEXTO = RGBColor(0x1F, 0x2D, 0x33)
SUAVE = RGBColor(0x5B, 0x6B, 0x72)
CARTAO = RGBColor(0xEE, 0xF3, 0xF2)
BRANCO = RGBColor(0xFF, 0xFF, 0xFF)
CLARO = RGBColor(0xCF, 0xE3, 0xE0)

TITULO_FONTE = "Cambria"
CORPO_FONTE = "Calibri"

LARGURA, ALTURA = Inches(13.333), Inches(7.5)
MARGEM = Inches(0.6)


# ---------------------------------------------------------------------------
# Blocos de construção
# ---------------------------------------------------------------------------

def texto(slide, x, y, w, h, conteudo, tamanho=16, cor=TEXTO, negrito=False, fonte=CORPO_FONTE,
          alinhamento=PP_ALIGN.LEFT, ancora=MSO_ANCHOR.TOP, italico=False, espaco_depois=6):
    """Caixa de texto. `conteudo` pode ser str, lista de str (um parágrafo cada) ou
    lista de listas de (texto, {opções}) para misturar estilos no mesmo parágrafo."""
    caixa = slide.shapes.add_textbox(x, y, w, h)
    quadro = caixa.text_frame
    quadro.word_wrap = True
    quadro.margin_left = quadro.margin_right = quadro.margin_top = quadro.margin_bottom = 0
    quadro.vertical_anchor = ancora
    paragrafos = conteudo if isinstance(conteudo, list) else [conteudo]
    for i, paragrafo in enumerate(paragrafos):
        p = quadro.paragraphs[0] if i == 0 else quadro.add_paragraph()
        p.alignment = alinhamento
        p.space_after = Pt(espaco_depois)
        trechos = paragrafo if isinstance(paragrafo, list) else [(paragrafo, {})]
        for trecho, opcoes in trechos:
            run = p.add_run()
            run.text = trecho
            run.font.name = opcoes.get("fonte", fonte)
            run.font.size = Pt(opcoes.get("tamanho", tamanho))
            run.font.bold = opcoes.get("negrito", negrito)
            run.font.italic = opcoes.get("italico", italico)
            run.font.color.rgb = opcoes.get("cor", cor)
    return caixa


def lista(slide, x, y, w, h, itens, tamanho=15, cor=TEXTO, espaco_depois=8):
    """Lista com marcadores de verdade (não o caractere •)."""
    caixa = texto(slide, x, y, w, h, itens, tamanho=tamanho, cor=cor, espaco_depois=espaco_depois)
    for p in caixa.text_frame.paragraphs:
        pPr = p._p.get_or_add_pPr()
        pPr.set("marL", str(Emu(Inches(0.25))))
        pPr.set("indent", str(-Emu(Inches(0.25))))
        marcador = pPr.makeelement("{http://schemas.openxmlformats.org/drawingml/2006/main}buChar", {"char": "•"})
        pPr.append(marcador)
    return caixa


def cartao(slide, x, y, w, h, cor=CARTAO):
    forma = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    forma.adjustments[0] = 0.06
    forma.fill.solid()
    forma.fill.fore_color.rgb = cor
    forma.line.fill.background()
    forma.shadow.inherit = False
    return forma


def circulo(slide, x, y, diametro, rotulo, cor=CORAL, tamanho=16):
    forma = slide.shapes.add_shape(MSO_SHAPE.OVAL, x, y, diametro, diametro)
    forma.fill.solid()
    forma.fill.fore_color.rgb = cor
    forma.line.fill.background()
    forma.shadow.inherit = False
    quadro = forma.text_frame
    quadro.margin_left = quadro.margin_right = quadro.margin_top = quadro.margin_bottom = 0
    quadro.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = quadro.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = rotulo
    run.font.name = CORPO_FONTE
    run.font.size = Pt(tamanho)
    run.font.bold = True
    run.font.color.rgb = BRANCO
    return forma


def fundo(slide, cor):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = cor


def cabecalho(slide, titulo, rotulo=None, numero=None):
    """Título na mesma posição em todos os slides de conteúdo; acima dele, a
    pergunta de negócio (com o número no círculo coral, o motivo visual do deck)."""
    if rotulo:
        x_rotulo = MARGEM
        if numero:
            circulo(slide, MARGEM, Inches(0.38), Inches(0.42), str(numero), tamanho=15)
            x_rotulo = MARGEM + Inches(0.55)
        texto(slide, x_rotulo, Inches(0.42), Inches(11), Inches(0.4), rotulo, tamanho=14, cor=CORAL, negrito=True,
              ancora=MSO_ANCHOR.MIDDLE)
    texto(slide, MARGEM, Inches(0.92), LARGURA - 2 * MARGEM, Inches(0.8), titulo, tamanho=30, cor=ESCURO,
          negrito=True, fonte=TITULO_FONTE)


def imagem(slide, caminho, x, y, w_max, h_max, alinhar="centro"):
    """Insere a imagem no maior tamanho que cabe na caixa, mantendo a proporção."""
    largura_px, altura_px = Image.open(caminho).size
    escala = min(w_max / largura_px, h_max / altura_px)
    w, h = int(largura_px * escala), int(altura_px * escala)
    dx = (w_max - w) // 2 if alinhar == "centro" else 0
    return slide.shapes.add_picture(str(caminho), x + dx, y + (h_max - h) // 2, w, h)


def numero_destaque(slide, x, y, w, valor, legenda, cor=CORAL, tamanho=44, cor_legenda=SUAVE):
    texto(slide, x, y, w, Inches(0.85), valor, tamanho=tamanho, cor=cor, negrito=True, fonte=TITULO_FONTE)
    texto(slide, x, y + Inches(0.82), w, Inches(0.7), legenda, tamanho=13, cor=cor_legenda)


def estilizar_grafico(grafico, tamanho=12):
    grafico.font.name = CORPO_FONTE
    grafico.font.size = Pt(tamanho)
    grafico.font.color.rgb = SUAVE


def notas(slide, fala):
    slide.notes_slide.notes_text_frame.text = fala


# ---------------------------------------------------------------------------
# Slides
# ---------------------------------------------------------------------------

def slide_capa(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    fundo(s, ESCURO)
    texto(s, MARGEM, Inches(1.3), Inches(7.6), Inches(0.4), "TECH CHALLENGE · FASE 3", tamanho=14, cor=CORAL, negrito=True)
    texto(s, MARGEM, Inches(1.85), Inches(7.6), Inches(2.4), "Alfabetização no Brasil: onde agir e com qual alavanca",
          tamanho=40, cor=BRANCO, negrito=True, fonte=TITULO_FONTE)
    texto(s, MARGEM, Inches(4.35), Inches(7.2), Inches(1.0),
          "Predição e inteligência analítica a partir do Indicador Criança Alfabetizada", tamanho=18, cor=CLARO)
    texto(s, MARGEM, Inches(6.35), Inches(7.2), Inches(0.4), "Reunião executiva com gestores públicos de educação",
          tamanho=13, cor=CLARO)
    cartao(s, Inches(8.9), Inches(1.6), Inches(3.8), Inches(4.2), cor=RGBColor(0x2F, 0x56, 0x65))
    texto(s, Inches(9.3), Inches(2.1), Inches(3.1), Inches(1.4), "80%", tamanho=80, cor=CORAL, negrito=True,
          fonte=TITULO_FONTE)
    texto(s, Inches(9.3), Inches(3.7), Inches(3.1), Inches(1.6),
          "das crianças alfabetizadas ao fim do 2º ano até 2030: a meta nacional", tamanho=16, cor=BRANCO)
    notas(s, "Bom dia a todos. Vou apresentar o que os dados de alfabetização nos dizem sobre onde agir "
             "e com qual alavanca para chegar à meta de 80% de crianças alfabetizadas até 2030.")


def slide_agenda(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecalho(s, "Avançamos, mas ainda faltam 14 pontos até a meta", "ONDE ESTAMOS E O QUE VAMOS RESPONDER")
    for i, (valor, legenda, cor) in enumerate([
        ("55,9%", "crianças alfabetizadas em 2023", SUAVE),
        ("59,2%", "em 2024, abaixo da meta do ano (59,9%)", ESCURO),
        ("66%", "em 2025, acima da meta do ano (63,8%)", TEAL),
    ]):
        numero_destaque(s, MARGEM, Inches(2.0) + i * Inches(1.6), Inches(4.2), valor, legenda, cor=cor)
    perguntas = [
        "Quais fatores mais impactam a alfabetização?",
        "Quais variáveis possuem maior influência nos modelos?",
        "Quais regiões possuem padrões semelhantes?",
        "Quais municípios apresentam maior risco educacional?",
        "Como prever municípios que podem não atingir metas futuras?",
    ]
    cartao(s, Inches(5.3), Inches(1.95), Inches(7.4), Inches(4.9))
    texto(s, Inches(5.7), Inches(2.2), Inches(6.6), Inches(0.4), "As cinco perguntas de negócio", tamanho=18,
          cor=ESCURO, negrito=True)
    for i, pergunta in enumerate(perguntas):
        y = Inches(2.85) + i * Inches(0.78)
        circulo(s, Inches(5.7), y, Inches(0.5), str(i + 1), tamanho=16)
        texto(s, Inches(6.4), y, Inches(5.9), Inches(0.5), pergunta, tamanho=16, ancora=MSO_ANCHOR.MIDDLE)
    notas(s, "O Brasil avançou: de 56% em 2023 para 66% em 2025, acima da meta do ano. "
             "Mas ainda faltam 14 pontos até 2030, e a média esconde o essencial. "
             "Trouxemos respostas para cinco perguntas de negócio.")


def slide_problema(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecalho(s, "A média esconde quase 50 pontos de diferença entre estados", "O PROBLEMA")
    dados = CategoryChartData()
    dados.categories = ["2023", "2024", "2025", "2026", "2027", "2028", "2029", "2030"]
    dados.add_series("Resultado", (55.9, 59.2, 66.0, None, None, None, None, None))
    dados.add_series("Meta nacional", (None, 59.9, 63.8, 67.5, 71.0, 74.2, 77.2, 80.0))
    grafico = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, MARGEM, Inches(1.95), Inches(6.4), Inches(4.6), dados).chart
    estilizar_grafico(grafico)
    grafico.has_title = True
    grafico.chart_title.text_frame.text = "Brasil: % de crianças alfabetizadas x meta"
    grafico.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(14)
    grafico.chart_title.text_frame.paragraphs[0].runs[0].font.bold = True
    grafico.chart_title.text_frame.paragraphs[0].runs[0].font.color.rgb = ESCURO
    grafico.has_legend = True
    grafico.legend.position = XL_LEGEND_POSITION.BOTTOM
    grafico.legend.include_in_layout = False
    eixo = grafico.value_axis
    eixo.minimum_scale, eixo.maximum_scale = 40, 85
    eixo.major_gridlines.format.line.color.rgb = RGBColor(0xDD, 0xE3, 0xE2)
    eixo.format.line.fill.background()
    for serie, cor in zip(grafico.series, [CORAL, SUAVE]):
        serie.format.line.color.rgb = cor
        serie.format.line.width = Pt(2.5 if cor == CORAL else 1.5)
        serie.marker.format.fill.solid()
        serie.marker.format.fill.fore_color.rgb = cor
        serie.marker.format.line.color.rgb = cor
        serie.smooth = False
    resultado = grafico.series[0]
    resultado.data_labels.show_value = True
    resultado.data_labels.number_format = '0.0"%"'
    resultado.data_labels.number_format_is_linked = False
    resultado.data_labels.position = XL_LABEL_POSITION.ABOVE
    resultado.data_labels.font.size = Pt(12)
    resultado.data_labels.font.bold = True
    resultado.data_labels.font.color.rgb = CORAL
    imagem(s, DIR_IMAGENS / "eda_02_taxa_por_uf.png", Inches(7.3), Inches(1.85), Inches(5.4), Inches(5.3))
    notas(s, "A diferença entre estados chega a quase 50 pontos: 36% na Bahia e 85% no Ceará em 2024. "
             "A pergunta que trouxemos é onde agir, e com qual alavanca.")


def slide_metodo(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecalho(s, "Dados públicos, dois modelos e validação contra a realidade", "COMO CHEGAMOS ÀS RESPOSTAS")
    blocos = [
        ("1", "Dados", ["3,35 milhões de crianças avaliadas em 2023 e 2024",
                        "Censo Escolar, fluxo escolar, nível socioeconômico (INSE), PIB e IDHM",
                        "Contexto de 5,5 mil municípios e suas redes"],
         "5 fontes", "públicas integradas"),
        ("2", "Modelos", ["Risco de cada criança não se alfabetizar (LightGBM)",
                          "Chance de cada rede municipal bater a meta do ano seguinte",
                          "Grupos de municípios com contexto parecido"],
         "66%", "do sinal possível capturado pelo modelo"),
        ("3", "Validação", ["Treino com 2023, teste com 2024: dados que o modelo nunca viu",
                            "Probabilidades calibradas: 70% previsto ≈ 70% real",
                            "Previsões comparadas com os resultados estaduais de 2025"],
         "2 testes", "contra dados reais: 2024 e 2025"),
    ]
    largura = Inches(3.85)
    for i, (num, titulo, itens, destaque, legenda) in enumerate(blocos):
        x = MARGEM + i * (largura + Inches(0.33))
        cartao(s, x, Inches(2.0), largura, Inches(4.75))
        circulo(s, x + Inches(0.35), Inches(2.35), Inches(0.6), num, tamanho=20)
        texto(s, x + Inches(1.1), Inches(2.4), largura - Inches(1.3), Inches(0.5), titulo, tamanho=22, cor=ESCURO,
              negrito=True, ancora=MSO_ANCHOR.MIDDLE)
        lista(s, x + Inches(0.35), Inches(3.2), largura - Inches(0.7), Inches(2.3), itens, tamanho=15)
        texto(s, x + Inches(0.35), Inches(5.45), largura - Inches(0.7), Inches(0.6), destaque, tamanho=28, cor=CORAL,
              negrito=True, fonte=TITULO_FONTE)
        texto(s, x + Inches(0.35), Inches(6.1), largura - Inches(0.7), Inches(0.5), legenda, tamanho=13, cor=SUAVE)
    notas(s, "Usamos os microdados de 3,3 milhões de crianças e cruzamos com Censo Escolar, fluxo escolar, "
             "nível socioeconômico, PIB e IDHM. Construímos dois modelos: um estima o risco de cada criança "
             "e outro antecipa quais redes não devem bater a meta. Tudo foi validado com dados que o modelo nunca viu.")


def slide_fatores(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecalho(s, "Trajetória escolar e política estadual pesam mais que a renda",
              "QUAIS FATORES MAIS IMPACTAM A ALFABETIZAÇÃO?", numero=1)
    temas = [("Docentes e equipe", 3.7), ("Infraestrutura escolar", 4.8), ("Ruralidade e diversidade", 5.9),
             ("Porte da rede e do município", 6.0), ("Nível socioeconômico", 19.0), ("Estado (UF) e região", 29.5),
             ("Trajetória escolar", 30.8)]
    dados = CategoryChartData()
    dados.categories = [t for t, _ in temas]
    dados.add_series("% da importância", [v for _, v in temas])
    grafico = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, MARGEM, Inches(1.95), Inches(7.2), Inches(4.9), dados).chart
    estilizar_grafico(grafico, 13)
    grafico.has_legend = False
    grafico.has_title = True
    grafico.chart_title.text_frame.text = "Peso de cada tema na previsão (SHAP agregado, % do total)"
    rotulo = grafico.chart_title.text_frame.paragraphs[0].runs[0].font
    rotulo.size, rotulo.bold, rotulo.color.rgb = Pt(14), True, ESCURO
    grafico.value_axis.visible = False
    grafico.value_axis.has_major_gridlines = False
    grafico.category_axis.format.line.fill.background()
    plot = grafico.plots[0]
    plot.gap_width = 45
    plot.vary_by_categories = False
    serie = plot.series[0]
    serie.format.fill.solid()
    serie.format.fill.fore_color.rgb = ESCURO
    for i in (5, 6):
        ponto = serie.points[i]
        ponto.format.fill.solid()
        ponto.format.fill.fore_color.rgb = CORAL
    serie.data_labels.show_value = True
    serie.data_labels.number_format = '0"%"'
    serie.data_labels.number_format_is_linked = False
    serie.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    serie.data_labels.font.size = Pt(13)
    serie.data_labels.font.bold = True
    serie.data_labels.font.color.rgb = TEXTO

    cartao(s, Inches(8.2), Inches(1.95), Inches(4.5), Inches(4.9))
    texto(s, Inches(8.55), Inches(2.25), Inches(3.8), Inches(0.4), "Resposta", tamanho=18, cor=CORAL, negrito=True)
    lista(s, Inches(8.55), Inches(2.8), Inches(3.85), Inches(3.9), [
        [("Trajetória escolar (31%): ", {"negrito": True}), ("redes com atraso e abandono nos anos iniciais alfabetizam menos", {})],
        [("Política estadual (30%): ", {"negrito": True}), ("o estado pesa tanto quanto o contexto", {})],
        [("Nível socioeconômico (19%): ", {"negrito": True}), ("importa, mas vem só em 3º lugar", {})],
        "Infraestrutura e formação docente têm peso menor depois desses fatores",
    ], tamanho=15)
    notas(s, "O que mais pesa? Em primeiro lugar, a trajetória escolar: redes onde as crianças atrasam ou "
             "abandonam nos anos iniciais. Em segundo, o estado, ou seja, a política estadual. "
             "O nível socioeconômico vem só em terceiro. As duas alavancas mais fortes estão ao alcance da gestão.")


def slide_variaveis(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecalho(s, "O Ceará entrega muito mais do que seu contexto prevê",
              "QUAIS VARIÁVEIS POSSUEM MAIOR INFLUÊNCIA NOS MODELOS?", numero=2)
    imagem(s, DIR_IMAGENS / "int_05_efeito_uf.png", MARGEM, Inches(1.85), Inches(5.6), Inches(5.35))
    texto(s, Inches(6.65), Inches(2.0), Inches(6.0), Inches(0.4), "Variáveis mais influentes (SHAP e permutação)",
          tamanho=16, cor=ESCURO, negrito=True)
    lista(s, Inches(6.65), Inches(2.5), Inches(6.0), Inches(1.8), [
        "Estado (UF), com destaque para o Ceará",
        "Distorção idade-série e abandono nos anos iniciais",
        "Nível socioeconômico dos alunos (INSE)",
    ], tamanho=15, espaco_depois=4)
    texto(s, Inches(6.65), Inches(4.15), Inches(6.0), Inches(0.4), "Os efeitos funcionam por limiares", tamanho=16,
          cor=ESCURO, negrito=True)
    for i, (valor, legenda) in enumerate([("> 8%", "de distorção idade-série derruba a chance"),
                                          ("> 0,5%", "de abandono já muda o sinal"),
                                          ("< 4,8", "de INSE: degrau socioeconômico")]):
        x = Inches(6.65) + i * Inches(2.05)
        cartao(s, x, Inches(4.65), Inches(1.9), Inches(2.1))
        texto(s, x + Inches(0.2), Inches(4.8), Inches(1.6), Inches(0.7), valor, tamanho=30, cor=CORAL, negrito=True,
              fonte=TITULO_FONTE)
        texto(s, x + Inches(0.2), Inches(5.55), Inches(1.55), Inches(1.1), legenda, tamanho=13, cor=TEXTO)
    notas(s, "Descontado o contexto, o Ceará alfabetiza muito acima do que sua renda faria esperar, efeito "
             "associado a quase 20 anos de regime de colaboração com os municípios. Sergipe, Rio Grande do Norte, "
             "Tocantins e Bahia entregam menos do que poderiam. E os efeitos têm limiares: acima de 8% de distorção "
             "ou de meio por cento de abandono, a chance cai.")


def slide_exemplo(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecalho(s, "Contexto não é destino: um município cearense", "EXEMPLO DE EXPLICAÇÃO INDIVIDUAL")
    numero_destaque(s, MARGEM, Inches(2.0), Inches(2.6), "76%", "das crianças do município em situação de pobreza",
                    cor=SUAVE, tamanho=54)
    numero_destaque(s, Inches(3.4), Inches(2.0), Inches(2.6), "95%", "de chance prevista de alfabetização",
                    cor=TEAL, tamanho=54)
    cartao(s, MARGEM, Inches(4.0), Inches(5.4), Inches(2.2))
    texto(s, Inches(0.95), Inches(4.2), Inches(4.8), Inches(0.4), "O que a rede faz diferente", tamanho=16,
          cor=ESCURO, negrito=True)
    lista(s, Inches(0.95), Inches(4.7), Inches(4.8), Inches(2.0), [
        "Abandono zero e 100% de aprovação no 2º ano",
        "Distorção idade-série de apenas 1,9%",
        "78% das matrículas em tempo integral",
    ], tamanho=15, espaco_depois=4)
    imagem(s, DIR_IMAGENS / "int_09_local_menor_risco.png", Inches(6.3), Inches(1.9), Inches(6.45), Inches(5.0))
    notas(s, "Um exemplo: um município cearense com 76% das crianças na pobreza tem previsão de 95% de "
             "alfabetização. A rede tem abandono zero, quase nenhuma distorção idade-série e tempo integral. "
             "O contexto importa, mas não decide sozinho.")


def slide_grupos(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecalho(s, "Mesma pobreza, 21 pontos de diferença na alfabetização",
              "QUAIS REGIÕES POSSUEM PADRÕES SEMELHANTES?", numero=3)
    mapa = DIR_IMAGENS / "_mapa_grupos.png"
    Image.open(DIR_IMAGENS / "app_05_clusters.png").crop((0, 0, 930, 950)).save(mapa)
    imagem(s, mapa, MARGEM, Inches(1.85), Inches(5.3), Inches(5.3))
    grupos = [("Fluxo escolar crítico", 41.9), ("Áreas diferenciadas e rurais", 50.0), ("Urbano de maior porte", 59.3),
              ("Vulnerável com fluxo regular", 62.9), ("Pequenos desenvolvidos", 70.5)]
    dados = CategoryChartData()
    dados.categories = [g for g, _ in grupos]
    dados.add_series("Taxa 2024", [v for _, v in grupos])
    grafico = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(6.2), Inches(1.95), Inches(6.5), Inches(3.0),
                                 dados).chart
    estilizar_grafico(grafico, 12)
    grafico.has_legend = False
    grafico.has_title = True
    grafico.chart_title.text_frame.text = "% de alfabetizados por grupo de contexto (2024)"
    rotulo = grafico.chart_title.text_frame.paragraphs[0].runs[0].font
    rotulo.size, rotulo.bold, rotulo.color.rgb = Pt(14), True, ESCURO
    grafico.value_axis.visible = False
    grafico.value_axis.has_major_gridlines = False
    grafico.value_axis.maximum_scale = 85
    grafico.category_axis.format.line.fill.background()
    plot = grafico.plots[0]
    plot.gap_width = 40
    serie = plot.series[0]
    for ponto, cor in zip(serie.points, [CORAL, LARANJA, AMARELO, TEAL, ESCURO]):
        ponto.format.fill.solid()
        ponto.format.fill.fore_color.rgb = cor
    serie.data_labels.show_value = True
    serie.data_labels.number_format = '0"%"'
    serie.data_labels.number_format_is_linked = False
    serie.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    serie.data_labels.font.size = Pt(13)
    serie.data_labels.font.bold = True
    serie.data_labels.font.color.rgb = TEXTO
    cartao(s, Inches(6.2), Inches(5.15), Inches(6.5), Inches(1.45))
    texto(s, Inches(6.5), Inches(5.3), Inches(5.9), Inches(1.2), [
        [("Os dois grupos vulneráveis têm ~56% de pobreza infantil e o mesmo INSE. ", {"negrito": True}),
         ("O que separa 63% de 42% é o fluxo escolar: distorção de 6% contra 16%. "
          "Em todos os grupos há municípios-referência, 30 a 50 pontos acima do esperado.", {})],
    ], tamanho=14)
    notas(s, "Agrupamos os municípios por contexto. Os dois grupos vulneráveis têm a mesma pobreza e o mesmo "
             "nível socioeconômico, mas um alfabetiza 63% e o outro 42%. São 21 pontos, explicados pelo fluxo "
             "escolar. E em todo grupo há municípios-referência, como Barreirinhas, no Maranhão.")


def slide_risco(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecalho(s, "Gravidade concentrada na Bahia, volume nas grandes capitais",
              "QUAIS MUNICÍPIOS APRESENTAM MAIOR RISCO EDUCACIONAL?", numero=4)
    imagem(s, DIR_IMAGENS / "app_03_mapa_risco.png", MARGEM, Inches(1.85), Inches(5.0), Inches(5.3))
    cartao(s, Inches(5.95), Inches(1.95), Inches(3.25), Inches(4.85))
    texto(s, Inches(6.25), Inches(2.2), Inches(2.7), Inches(0.4), "Por gravidade", tamanho=18, cor=CORAL, negrito=True)
    texto(s, Inches(6.25), Inches(2.65), Inches(2.75), Inches(0.6), "% das redes no decil de maior risco", tamanho=12,
          cor=SUAVE)
    for i, (uf, valor) in enumerate([("Bahia", "84%"), ("Sergipe", "43%"), ("Amazonas", "31%"),
                                     ("Rio Grande do Norte", "30%"), ("Pará", "29%")]):
        y = Inches(3.2) + i * Inches(0.66)
        texto(s, Inches(6.25), y, Inches(2.0), Inches(0.5), uf, tamanho=15, ancora=MSO_ANCHOR.MIDDLE)
        texto(s, Inches(8.1), y, Inches(0.9), Inches(0.5), valor, tamanho=17, cor=ESCURO, negrito=True,
              alinhamento=PP_ALIGN.RIGHT, ancora=MSO_ANCHOR.MIDDLE)
    cartao(s, Inches(9.45), Inches(1.95), Inches(3.25), Inches(4.85))
    texto(s, Inches(9.75), Inches(2.2), Inches(2.7), Inches(0.4), "Por volume", tamanho=18, cor=CORAL, negrito=True)
    texto(s, Inches(9.75), Inches(2.65), Inches(2.75), Inches(0.6), "crianças não alfabetizadas (rede municipal)",
          tamanho=12, cor=SUAVE)
    for i, (cidade, valor) in enumerate([("São Paulo", "21,6 mil"), ("Rio de Janeiro", "15,7 mil"),
                                         ("Manaus", "9,3 mil"), ("Salvador", "7,7 mil")]):
        y = Inches(3.2) + i * Inches(0.66)
        texto(s, Inches(9.75), y, Inches(1.5), Inches(0.5), cidade, tamanho=15, ancora=MSO_ANCHOR.MIDDLE)
        texto(s, Inches(11.2), y, Inches(1.2), Inches(0.5), valor, tamanho=17, cor=ESCURO, negrito=True,
              alinhamento=PP_ALIGN.RIGHT, ancora=MSO_ANCHOR.MIDDLE)
    texto(s, Inches(9.75), Inches(5.95), Inches(2.75), Inches(0.75),
          "São Paulo alfabetiza 48%; o contexto previa 56%", tamanho=13, cor=TEXTO, italico=True)
    notas(s, "O índice de risco combina o resultado atual, o contexto e a chance de não bater a meta. "
             "Por gravidade, 84% das redes municipais da Bahia estão no grupo de maior risco. "
             "Por volume, só a rede de São Paulo tem 21 mil crianças não alfabetizadas, abaixo do que o "
             "contexto permitiria, seguida de Rio, Manaus e Salvador.")


def slide_metas(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecalho(s, "Prever metas é um alerta para priorizar, não uma sentença",
              "COMO PREVER MUNICÍPIOS QUE PODEM NÃO ATINGIR METAS FUTURAS?", numero=5)
    passos = [("Aprende", "como as redes de 2023 se saíram frente à meta de 2024"),
              ("Projeta", "a chance de cada rede bater a meta de 2025, com os dados de 2024"),
              ("Protege", "estados com choque atípico, como o RS nas enchentes, não viram tendência")]
    for i, (verbo, descricao) in enumerate(passos):
        y = Inches(2.0) + i * Inches(1.05)
        circulo(s, MARGEM, y, Inches(0.55), str(i + 1), cor=ESCURO, tamanho=16)
        texto(s, MARGEM + Inches(0.75), y - Inches(0.05), Inches(4.6), Inches(1.0),
              [[(verbo + ": ", {"negrito": True, "cor": ESCURO}), (descricao, {})]], tamanho=15)
    numero_destaque(s, MARGEM, Inches(5.25), Inches(2.6), "54%", "das redes devem bater a meta de 2025", cor=TEAL)
    numero_destaque(s, Inches(3.3), Inches(5.25), Inches(2.6), "1.431", "redes com menos de 40% de chance", cor=CORAL)
    imagem(s, DIR_IMAGENS / "app_00_choques_estaduais.png", Inches(6.1), Inches(1.85), Inches(6.6), Inches(5.3))
    notas(s, "Para as metas, o modelo aprende como as redes se saíram de um ano para o outro e projeta a chance "
             "de cada uma bater a meta de 2025. Cerca de 1.400 redes têm menos de 40% de chance. "
             "O Rio Grande do Sul caiu 22 pontos em 2024 por causa das enchentes, e o modelo foi desenhado para "
             "não projetar esse choque como tendência.")


def slide_validacao(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecalho(s, "Em 2025, o modelo acertou a direção e foi conservador no nível", "VALIDAÇÃO COM O QUE ACONTECEU")
    imagem(s, DIR_IMAGENS / "eda_12_metas_estaduais.png", MARGEM, Inches(1.85), Inches(5.4), Inches(5.35))
    numero_destaque(s, Inches(6.4), Inches(2.0), Inches(3.0), "0,43",
                    "correlação entre a chance prevista e o estado ter batido a meta", cor=TEAL)
    numero_destaque(s, Inches(9.6), Inches(2.0), Inches(3.1), "52% → 76%",
                    "chance média prevista x estados que bateram a meta", cor=CORAL, tamanho=36)
    cartao(s, Inches(6.4), Inches(3.85), Inches(6.3), Inches(2.5))
    lista(s, Inches(6.75), Inches(4.1), Inches(5.7), Inches(2.2), [
        [("Direção certa: ", {"negrito": True}), ("CE, GO, ES e MG, apontados como seguros, bateram a meta", {})],
        [("Nível conservador: ", {"negrito": True}), ("2025 teve um avanço amplo que nenhum dado anterior antecipava", {})],
        [("Bahia: ", {"negrito": True}), ("menor chance prevista e maior salto do país, de 36% para 55%", {})],
    ], tamanho=15)
    notas(s, "Comparamos a previsão com o que aconteceu em 2025 nos estados. O modelo acertou a direção: "
             "os estados apontados como mais seguros bateram a meta. Mas foi conservador, porque 2025 teve um "
             "avanço muito maior que o esperado. A Bahia, a mais crítica, deu o maior salto do país. "
             "Ela continua entre as menores taxas e precisa de prioridade, e o que mudou lá merece ser estudado.")


def slide_recomendacoes(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cabecalho(s, "Cinco recomendações para a gestão", "VALOR ESTRATÉGICO PARA AS POLÍTICAS PÚBLICAS")
    recomendacoes = [
        ("Priorizar recursos com o ranking de risco",
         "Gravidade para a Bahia e o Nordeste; volume para as grandes capitais"),
        ("Atacar o fluxo escolar nos anos iniciais",
         "Busca ativa, frequência e recomposição: a alavanca mais forte e acionável"),
        ("Expandir o regime de colaboração Estado-municípios",
         "No modelo do Ceará, começando pelos estados abaixo do esperado"),
        ("Conectar municípios parecidos às suas referências",
         "Intercâmbio com quem alfabetiza muito acima do esperado no mesmo grupo"),
        ("Usar o alerta de metas antes da prova",
         "Agir no mesmo ano e retreinar o modelo a cada novo resultado"),
    ]
    for i, (titulo, descricao) in enumerate(recomendacoes):
        y = Inches(1.95) + i * Inches(0.98)
        cartao(s, MARGEM, y, LARGURA - 2 * MARGEM, Inches(0.84))
        circulo(s, MARGEM + Inches(0.25), y + Inches(0.15), Inches(0.54), str(i + 1), tamanho=17)
        texto(s, MARGEM + Inches(1.05), y, Inches(5.0), Inches(0.84), titulo, tamanho=17, cor=ESCURO, negrito=True,
              ancora=MSO_ANCHOR.MIDDLE)
        texto(s, MARGEM + Inches(6.2), y, Inches(5.7), Inches(0.84), descricao, tamanho=15,
              ancora=MSO_ANCHOR.MIDDLE)
    notas(s, "Nossa proposta: primeiro, priorizar recursos com o ranking de risco. Segundo, atacar o fluxo "
             "escolar nos anos iniciais. Terceiro, expandir o regime de colaboração no modelo do Ceará. "
             "Quarto, conectar municípios parecidos às suas referências. E quinto, usar o alerta de metas "
             "antes da prova, para agir no mesmo ano.")


def slide_encerramento(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    fundo(s, ESCURO)
    texto(s, MARGEM, Inches(1.4), Inches(11.5), Inches(0.4), "MENSAGEM FINAL", tamanho=14, cor=CORAL, negrito=True)
    texto(s, MARGEM, Inches(1.95), Inches(11.5), Inches(1.6), "Os modelos dizem onde olhar primeiro",
          tamanho=40, cor=BRANCO, negrito=True, fonte=TITULO_FONTE)
    proximos = [("Retreinar", "com os resultados municipais de 2025"),
                ("Validar", "as referências com as secretarias antes de difundi-las"),
                ("Acompanhar", "o efeito das ações nas redes priorizadas a cada ciclo")]
    for i, (verbo, descricao) in enumerate(proximos):
        x = MARGEM + i * Inches(4.1)
        cartao(s, x, Inches(4.0), Inches(3.8), Inches(1.9), cor=RGBColor(0x2F, 0x56, 0x65))
        texto(s, x + Inches(0.35), Inches(4.25), Inches(3.1), Inches(0.5), verbo, tamanho=20, cor=CORAL, negrito=True)
        texto(s, x + Inches(0.35), Inches(4.8), Inches(3.1), Inches(1.0), descricao, tamanho=15, cor=BRANCO)
    texto(s, MARGEM, Inches(6.5), Inches(11.5), Inches(0.4), "Obrigado.", tamanho=16, cor=CLARO)
    notas(s, "Os modelos não substituem o olhar das secretarias: eles dizem onde olhar primeiro. "
             "Com os resultados de 2025, retreinamos tudo, e o alerta fica mais preciso a cada ciclo. Obrigado.")


def gerar() -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = LARGURA, ALTURA
    prs.core_properties.title = "Alfabetização no Brasil: onde agir e com qual alavanca"
    prs.core_properties.author = "eliaslopesjr1-maker"
    for construir in [slide_capa, slide_agenda, slide_problema, slide_metodo, slide_fatores, slide_variaveis,
                      slide_exemplo, slide_grupos, slide_risco, slide_metas, slide_validacao, slide_recomendacoes,
                      slide_encerramento]:
        construir(prs)
    destino = DIR_REPORTS / "apresentacao_executiva.pptx"
    prs.save(destino)
    (DIR_IMAGENS / "_mapa_grupos.png").unlink(missing_ok=True)
    print(f"apresentação gerada: {destino} ({len(prs.slides)} slides)")
    return destino


if __name__ == "__main__":
    gerar()
