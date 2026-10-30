"""Gera a apresentação executiva (reports/apresentacao_executiva.pptx) usada no vídeo.

Estrutura: abertura (problema e método), as 5 perguntas de negócio e o fechamento
(recomendações). Cada pergunta ocupa 1 ou 2 slides:
- o 1º traz a PERGUNTA como título, a resposta direta logo abaixo e o dado principal;
- o 2º (quando há) traz a evidência que sustenta ou detalha a resposta.

As notas do apresentador trazem a fala de cada slide (~5 minutos no total).
Os números vêm dos notebooks 01 a 04 e de reports/; os gráficos, de images/.

Uso:
    python -m src.visualization.apresentacao
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import (
    XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION, XL_TICK_LABEL_POSITION, XL_TICK_MARK,
)
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

from src.config import DIR_IMAGENS, DIR_RAW, DIR_REPORTS

AUTOR = "Elias Lopes Silva Junior"
FONTE_DADOS = ("Fonte: Inep (Avaliação de Alfabetização 2023-2024, metas e resultados 2025), via Base dos Dados; "
               "Censo Escolar, IBGE e Atlas do Desenvolvimento Humano. Elaboração própria.")

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
ESCURO_CARTAO = RGBColor(0x2F, 0x56, 0x65)

TITULO_FONTE = "Cambria"
CORPO_FONTE = "Calibri"

LARGURA, ALTURA = Inches(13.333), Inches(7.5)
MARGEM = Inches(0.6)
TOPO_PERGUNTA = Inches(2.4)    # início do conteúdo nos slides com pergunta + resposta
TOPO_EVIDENCIA = Inches(1.95)  # início do conteúdo nos demais slides


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


def novo_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def rodape(slide):
    texto(slide, MARGEM, Inches(7.08), LARGURA - 2 * MARGEM, Inches(0.3), FONTE_DADOS, tamanho=9, cor=SUAVE)


def cabecalho(slide, titulo, rotulo):
    """Slides de abertura e fechamento: rótulo coral + título."""
    rodape(slide)
    texto(slide, MARGEM, Inches(0.42), Inches(11), Inches(0.4), rotulo, tamanho=14, cor=CORAL, negrito=True,
          ancora=MSO_ANCHOR.MIDDLE)
    texto(slide, MARGEM, Inches(0.92), LARGURA - 2 * MARGEM, Inches(0.8), titulo, tamanho=30, cor=ESCURO,
          negrito=True, fonte=TITULO_FONTE)


def cabecalho_pergunta(slide, numero, pergunta, resposta=None, evidencia=None):
    """Slides das perguntas. O título fica sempre na mesma posição:
    - 1º slide: a pergunta é o título e a resposta direta vem logo abaixo;
    - 2º slide: o título é a evidência, e o rótulo lembra a qual pergunta ela responde."""
    rodape(slide)
    circulo(slide, MARGEM, Inches(0.38), Inches(0.42), str(numero), tamanho=15)
    rotulo = f"PERGUNTA {numero} DE 5" if evidencia is None else f"PERGUNTA {numero} · EVIDÊNCIA"
    texto(slide, MARGEM + Inches(0.55), Inches(0.42), Inches(10), Inches(0.4), rotulo, tamanho=14, cor=CORAL,
          negrito=True, ancora=MSO_ANCHOR.MIDDLE)
    texto(slide, MARGEM, Inches(0.92), LARGURA - 2 * MARGEM, Inches(0.8), evidencia or pergunta, tamanho=30,
          cor=ESCURO, negrito=True, fonte=TITULO_FONTE)
    if resposta:
        texto(slide, MARGEM, Inches(1.68), LARGURA - 2 * MARGEM, Inches(0.5),
              [[("Resposta: ", {"cor": CORAL, "negrito": True}), (resposta, {"cor": TEAL, "negrito": True})]],
              tamanho=20)


def imagem(slide, caminho, x, y, w_max, h_max, descricao, alinhar="centro"):
    """Insere a imagem no maior tamanho que cabe na caixa, mantendo a proporção,
    com texto alternativo descritivo (leitores de tela)."""
    largura_px, altura_px = Image.open(caminho).size
    escala = min(w_max / largura_px, h_max / altura_px)
    w, h = int(largura_px * escala), int(altura_px * escala)
    dx = (w_max - w) // 2 if alinhar == "centro" else 0
    figura = slide.shapes.add_picture(str(caminho), x + dx, y + (h_max - h) // 2, w, h)
    figura._element.nvPicPr.cNvPr.set("descr", descricao)
    return figura


# ---------------------------------------------------------------------------
# Mapas limpos (sem eixos de latitude/longitude), gerados a partir de reports/
# ---------------------------------------------------------------------------

CORES_GRUPO = {
    "Pequenos municípios desenvolvidos": "#264653",
    "Vulnerável com fluxo escolar regular": "#2a9d8f",
    "Urbano de maior porte": "#e9c46a",
    "Áreas diferenciadas e rurais": "#f4a261",
    "Vulnerável com fluxo escolar crítico": "#e76f51",
}


def _coordenadas():
    return pd.read_parquet(DIR_RAW / "diretorio_municipio.parquet",
                           columns=["id_municipio", "longitude", "latitude"]).astype({"id_municipio": str})


def _salvar_mapa(fig, nome):
    caminho = DIR_IMAGENS / nome
    fig.savefig(caminho, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return caminho


def mapa_risco():
    ranking = pd.read_csv(DIR_REPORTS / "ranking_risco_municipios_2024.csv", dtype={"id_municipio": str})
    dados = ranking.merge(_coordenadas(), on="id_municipio").sort_values("indice_risco")
    paleta = LinearSegmentedColormap.from_list("risco", ["#2a9d8f", "#e9c46a", "#e76f51", "#9b2226"])
    fig, ax = plt.subplots(figsize=(6, 6.2))
    pontos = ax.scatter(dados["longitude"], dados["latitude"], c=dados["indice_risco"], cmap=paleta, s=5,
                        linewidths=0)
    ax.set_aspect("equal")
    ax.axis("off")
    barra = fig.colorbar(pontos, ax=ax, orientation="horizontal", shrink=0.6, pad=0.02, aspect=30)
    barra.set_ticks([0.05, 0.95], labels=["menor risco", "maior risco"])
    barra.ax.tick_params(labelsize=11, length=0)
    barra.outline.set_visible(False)
    return _salvar_mapa(fig, "apr_mapa_risco.png")


def mapa_grupos():
    grupos = pd.read_csv(DIR_REPORTS / "clusters_municipios.csv", dtype={"id_municipio": str})
    dados = grupos.merge(_coordenadas(), on="id_municipio")
    fig, ax = plt.subplots(figsize=(6, 6.2))
    for grupo, cor in CORES_GRUPO.items():
        parte = dados[dados["grupo"] == grupo]
        ax.scatter(parte["longitude"], parte["latitude"], s=5, color=cor, linewidths=0, label=grupo)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=2, fontsize=9, markerscale=3, frameon=False)
    return _salvar_mapa(fig, "apr_mapa_grupos.png")


def numero_destaque(slide, x, y, w, valor, legenda, cor=CORAL, tamanho=44, cor_legenda=SUAVE):
    texto(slide, x, y, w, Inches(0.85), valor, tamanho=tamanho, cor=cor, negrito=True, fonte=TITULO_FONTE)
    texto(slide, x, y + Inches(0.82), w, Inches(0.7), legenda, tamanho=13, cor=cor_legenda)


def titulo_grafico(grafico, titulo):
    grafico.has_title = True
    grafico.chart_title.text_frame.text = titulo
    fonte = grafico.chart_title.text_frame.paragraphs[0].runs[0].font
    fonte.name, fonte.size, fonte.bold, fonte.color.rgb = CORPO_FONTE, Pt(14), True, ESCURO


def barras(slide, x, y, w, h, categorias, valores, titulo, formato='0"%"', cores=None, minimo=None, maximo=None,
           tamanho=13):
    """Barras horizontais nativas, no mesmo estilo em todo o deck. A primeira
    categoria fica embaixo (convenção do PowerPoint). Aceita valores negativos:
    o rótulo das categorias fica na borda esquerda para não colidir com as barras."""
    dados = CategoryChartData()
    dados.categories = categorias
    dados.add_series("valor", valores)
    grafico = slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, x, y, w, h, dados).chart
    grafico.font.name, grafico.font.size, grafico.font.color.rgb = CORPO_FONTE, Pt(tamanho), SUAVE
    grafico.has_legend = False
    titulo_grafico(grafico, titulo)
    grafico.value_axis.visible = False
    grafico.value_axis.has_major_gridlines = False
    if minimo is not None:
        grafico.value_axis.minimum_scale = minimo
    if maximo is not None:
        grafico.value_axis.maximum_scale = maximo
    eixo_categorias = grafico.category_axis
    eixo_categorias.format.line.fill.background()
    eixo_categorias.tick_label_position = XL_TICK_LABEL_POSITION.LOW
    eixo_categorias.major_tick_mark = XL_TICK_MARK.NONE
    plot = grafico.plots[0]
    plot.gap_width = 45
    serie = plot.series[0]
    serie.invert_if_negative = False
    for ponto, cor in zip(serie.points, cores or [ESCURO] * len(valores)):
        ponto.format.fill.solid()
        ponto.format.fill.fore_color.rgb = cor
    # Cada barra colorida vira um <c:dPt>, que por padrão inverte a cor quando o
    # valor é negativo (a barra fica branca). Desliga isso ponto a ponto.
    for dpt in serie._element.findall(qn("c:dPt")):
        inverter = dpt.makeelement(qn("c:invertIfNegative"), {"val": "0"})
        dpt.find(qn("c:idx")).addnext(inverter)
    # Mostra o rótulo de todas as categorias (sem isso o PowerPoint pula alguns em listas longas)
    eixo_categorias._element.append(eixo_categorias._element.makeelement(qn("c:tickLblSkip"), {"val": "1"}))
    rotulos = serie.data_labels
    rotulos.show_value = True
    rotulos.number_format = formato
    rotulos.number_format_is_linked = False
    rotulos.position = XL_LABEL_POSITION.OUTSIDE_END
    rotulos.font.size, rotulos.font.bold, rotulos.font.color.rgb = Pt(tamanho), True, TEXTO
    return grafico


def tabela(slide, x, y, w, cabecalhos, linhas, larguras, alinhamentos, altura_linha=Inches(0.42)):
    forma = slide.shapes.add_table(len(linhas) + 1, len(cabecalhos), x, y, w, altura_linha * (len(linhas) + 1))
    forma.table.first_row = True
    for j, largura in enumerate(larguras):
        forma.table.columns[j].width = largura
    for i, linha in enumerate([cabecalhos, *linhas]):
        forma.table.rows[i].height = altura_linha
        for j, valor in enumerate(linha):
            celula = forma.table.cell(i, j)
            celula.fill.solid()
            celula.fill.fore_color.rgb = ESCURO if i == 0 else (CARTAO if i % 2 else BRANCO)
            celula.margin_left = celula.margin_right = Inches(0.1)
            celula.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = celula.text_frame.paragraphs[0]
            p.alignment = alinhamentos[j]
            run = p.add_run()
            run.text = str(valor)
            run.font.name = CORPO_FONTE
            run.font.size = Pt(13 if i else 12)
            run.font.bold = i == 0
            run.font.color.rgb = BRANCO if i == 0 else TEXTO
    return forma


def notas(slide, fala):
    slide.notes_slide.notes_text_frame.text = fala


def pct(valor):
    return f"{valor:.0f}%".replace(".", ",")


# ---------------------------------------------------------------------------
# Abertura
# ---------------------------------------------------------------------------

def slide_capa(prs):
    s = novo_slide(prs)
    fundo(s, ESCURO)
    texto(s, MARGEM, Inches(1.3), Inches(7.6), Inches(0.4), "TECH CHALLENGE · FASE 3", tamanho=14, cor=CORAL, negrito=True)
    texto(s, MARGEM, Inches(1.85), Inches(7.9), Inches(2.4), "Alfabetização no Brasil: cinco perguntas para decidir onde agir",
          tamanho=36, cor=BRANCO, negrito=True, fonte=TITULO_FONTE)
    texto(s, MARGEM, Inches(3.55), Inches(7.2), Inches(1.0),
          "Predição e inteligência analítica a partir do Indicador Criança Alfabetizada", tamanho=18, cor=CLARO)
    texto(s, MARGEM, Inches(5.75), Inches(7.6), Inches(0.4), AUTOR, tamanho=18, cor=BRANCO, negrito=True)
    texto(s, MARGEM, Inches(6.2), Inches(7.6), Inches(0.4), "Reunião executiva com gestores públicos de educação",
          tamanho=13, cor=CLARO)
    cartao(s, Inches(8.9), Inches(1.6), Inches(3.8), Inches(4.2), cor=ESCURO_CARTAO)
    texto(s, Inches(9.3), Inches(2.1), Inches(3.1), Inches(1.4), "80%", tamanho=80, cor=CORAL, negrito=True,
          fonte=TITULO_FONTE)
    texto(s, Inches(9.3), Inches(3.7), Inches(3.1), Inches(1.6),
          "das crianças alfabetizadas ao fim do 2º ano até 2030: a meta nacional", tamanho=16, cor=BRANCO)
    notas(s, "Bom dia a todos. Vou responder cinco perguntas que ajudam a decidir onde agir para chegar a 80% "
             "de crianças alfabetizadas até 2030.")


def slide_agenda(prs):
    s = novo_slide(prs)
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
    notas(s, "O Brasil avançou de 56% em 2023 para 66% em 2025, mas ainda faltam 14 pontos até 2030. "
             "Estas são as cinco perguntas que vamos responder com dados.")


def slide_problema(prs):
    s = novo_slide(prs)
    cabecalho(s, "A média esconde quase 50 pontos de diferença entre estados", "O PROBLEMA")
    dados = CategoryChartData()
    dados.categories = ["2023", "2024", "2025", "2026", "2027", "2028", "2029", "2030"]
    dados.add_series("Resultado", (55.9, 59.2, 66.0, None, None, None, None, None))
    dados.add_series("Meta nacional", (None, 59.9, 63.8, 67.5, 71.0, 74.2, 77.2, 80.0))
    grafico = s.shapes.add_chart(XL_CHART_TYPE.LINE_MARKERS, MARGEM, Inches(1.95), Inches(6.4), Inches(4.6), dados).chart
    grafico.font.name, grafico.font.size, grafico.font.color.rgb = CORPO_FONTE, Pt(12), SUAVE
    titulo_grafico(grafico, "Brasil: % de crianças alfabetizadas x meta")
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
    rotulos = grafico.series[0].data_labels
    rotulos.show_value = True
    rotulos.number_format = '0.0"%"'
    rotulos.number_format_is_linked = False
    rotulos.position = XL_LABEL_POSITION.ABOVE
    rotulos.font.size, rotulos.font.bold, rotulos.font.color.rgb = Pt(12), True, CORAL
    imagem(s, DIR_IMAGENS / "eda_02_taxa_por_uf.png", Inches(7.3), Inches(1.85), Inches(5.4), Inches(5.2),
           "Barras com o percentual de crianças alfabetizadas por estado em 2024, de 36% na Bahia a 85% no Ceará")
    notas(s, "A média esconde a desigualdade: em 2024, 36% das crianças alfabetizadas na Bahia e 85% no Ceará.")


def slide_metodo(prs):
    s = novo_slide(prs)
    cabecalho(s, "Dados públicos, dois modelos e validação contra a realidade", "COMO CHEGAMOS ÀS RESPOSTAS")
    blocos = [
        ("1", "Dados", ["3,35 milhões de crianças avaliadas em 2023 e 2024",
                        "Censo Escolar, fluxo escolar, nível socioeconômico (INSE), PIB e IDHM",
                        "Contexto de 5,5 mil municípios e suas redes"],
         "5 fontes", "públicas integradas"),
        ("2", "Modelos", ["Risco de cada criança não se alfabetizar",
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
    notas(s, "Cruzamos os dados de 3,3 milhões de crianças com cinco bases públicas e construímos dois modelos: "
             "o risco de cada criança e a chance de cada rede bater a meta. Testamos com dados que o modelo nunca viu.")


# ---------------------------------------------------------------------------
# Pergunta 1 - fatores
# ---------------------------------------------------------------------------

def slide_p1_resposta(prs):
    s = novo_slide(prs)
    cabecalho_pergunta(s, 1, "Quais fatores mais impactam a alfabetização?",
                       resposta="trajetória escolar e política estadual pesam mais que a renda")
    temas = [("Docentes e equipe", 3.7), ("Infraestrutura escolar", 4.8), ("Ruralidade e diversidade", 5.9),
             ("Porte da rede e do município", 6.0), ("Nível socioeconômico", 19.0), ("Estado (UF) e região", 29.5),
             ("Trajetória escolar", 30.8)]
    barras(s, MARGEM, TOPO_PERGUNTA, Inches(7.2), Inches(4.5), [t for t, _ in temas], [v for _, v in temas],
           "Peso de cada tema na previsão do modelo (% do total)", cores=[ESCURO] * 5 + [CORAL] * 2)
    cartao(s, Inches(8.2), TOPO_PERGUNTA + Inches(0.4), Inches(4.5), Inches(3.45))
    lista(s, Inches(8.55), TOPO_PERGUNTA + Inches(0.75), Inches(3.85), Inches(2.9), [
        [("Trajetória escolar (31%): ", {"negrito": True}), ("redes com atraso e abandono nos anos iniciais alfabetizam menos", {})],
        [("Política estadual (30%): ", {"negrito": True}), ("o estado pesa tanto quanto o contexto", {})],
        [("Nível socioeconômico (19%): ", {"negrito": True}), ("importa, mas vem só em 3º lugar", {})],
        "Infraestrutura e formação docente pesam menos depois desses fatores",
    ], tamanho=15)
    notas(s, "Primeira pergunta: o que mais pesa? A trajetória escolar, com 31%, e a política estadual, com 30%. "
             "O nível socioeconômico vem só em terceiro. As duas alavancas mais fortes estão ao alcance da gestão.")


def slide_p1_exemplo(prs):
    s = novo_slide(prs)
    cabecalho_pergunta(s, 1, "", evidencia="Contexto não é destino: um município cearense")
    numero_destaque(s, MARGEM, Inches(2.0), Inches(2.6), "76%", "das crianças do município em situação de pobreza",
                    cor=SUAVE, tamanho=54)
    numero_destaque(s, Inches(3.4), Inches(2.0), Inches(2.6), "95%", "de chance prevista de alfabetização",
                    cor=TEAL, tamanho=54)
    cartao(s, MARGEM, Inches(4.0), Inches(5.4), Inches(2.2))
    texto(s, Inches(0.95), Inches(4.2), Inches(4.8), Inches(0.4), "O que a rede faz diferente", tamanho=16,
          cor=ESCURO, negrito=True)
    lista(s, Inches(0.95), Inches(4.7), Inches(4.8), Inches(1.4), [
        "Abandono zero e 100% de aprovação no 2º ano",
        "Distorção idade-série de apenas 1,9%",
        "78% das matrículas em tempo integral",
    ], tamanho=15, espaco_depois=4)
    # Contribuições da explicação local (notebook 03, seção 7), em escala relativa: Ceará = 100.
    # "Demais fatores" soma o restante, inclusive variáveis socioeconômicas correlacionadas.
    fatores = [("Nível socioeconômico (INSE 4,4)", -5), ("Demais fatores", 28), ("Aprovação de 100% no 2º ano", 5),
               ("Jornada de 7 horas/dia", 5), ("78% em tempo integral", 7), ("Abandono zero", 22),
               ("Distorção idade-série de 1,9%", 28), ("Estar no Ceará", 100)]
    barras(s, Inches(6.3), Inches(1.95), Inches(6.4), Inches(4.4), [f for f, _ in fatores], [v for _, v in fatores],
           "O que explica os 95% (peso relativo, Ceará = 100)", formato="+0;-0", minimo=-15, maximo=125,
           cores=[CORAL] + [SUAVE] + [TEAL] * 6, tamanho=12)
    texto(s, Inches(6.3), Inches(6.45), Inches(6.4), Inches(0.5),
          "É a rede de menor risco previsto entre 20 mil alunos analisados: o caso extremo, usado como ilustração.",
          tamanho=12, cor=SUAVE, italico=True)
    notas(s, "Um exemplo, o caso mais extremo: um município cearense com 76% das crianças na pobreza tem 95% de "
             "chance prevista, porque a rede tem abandono zero, quase nenhuma distorção e tempo integral.")


# ---------------------------------------------------------------------------
# Pergunta 2 - variáveis
# ---------------------------------------------------------------------------

def slide_p2_resposta(prs):
    s = novo_slide(prs)
    cabecalho_pergunta(s, 2, "Quais variáveis possuem maior influência nos modelos?",
                       resposta="estado, distorção idade-série, abandono e nível socioeconômico")
    # |SHAP| médio por variável no teste 2024 (notebook 03, seção 2), one-hot somado
    variaveis = [("Tamanho médio das escolas", 0.022), ("População rural (2010)", 0.032),
                 ("% alunos com INSE baixo", 0.033), ("Região", 0.044), ("INSE médio da rede", 0.071),
                 ("Abandono nos anos iniciais", 0.112), ("Distorção idade-série", 0.127), ("Estado (UF)", 0.348)]
    barras(s, MARGEM, TOPO_PERGUNTA, Inches(7.4), Inches(4.5), [v for v, _ in variaveis],
           [round(x / 0.348 * 100) for _, x in variaveis],
           "Influência de cada variável na previsão (estado = 100)", formato="0",
           cores=[ESCURO] * 4 + [TEAL] + [CORAL] * 3, maximo=120)
    cartao(s, Inches(8.4), TOPO_PERGUNTA + Inches(0.4), Inches(4.3), Inches(3.45))
    texto(s, Inches(8.75), TOPO_PERGUNTA + Inches(0.7), Inches(3.7), Inches(0.4), "Dois testes, o mesmo ranking",
          tamanho=16, cor=ESCURO, negrito=True)
    lista(s, Inches(8.75), TOPO_PERGUNTA + Inches(1.25), Inches(3.65), Inches(2.5), [
        [("Leitura da previsão: ", {"negrito": True}), ("quanto cada variável empurra a chance de cada criança", {})],
        [("Teste de retirada: ", {"negrito": True}), ("sem o estado, o modelo perde mais acerto do que sem qualquer outra variável", {})],
        "Variáveis parecidas (IDHM, renda, pobreza) dividem a influência; por isso a leitura por tema",
    ], tamanho=14)
    notas(s, "Segunda pergunta: as variáveis mais influentes são o estado, a distorção idade-série, o abandono e "
             "o nível socioeconômico. Dois testes diferentes chegam ao mesmo ranking.")


def slide_p2_evidencia(prs):
    s = novo_slide(prs)
    cabecalho_pergunta(s, 2, "", evidencia="O efeito do estado e os limiares que mudam a chance")
    # Efeito médio da UF na previsão (notebook 03, seção 4), em escala relativa: Ceará = 100
    efeito = [("SE", -65), ("RN", -48), ("TO", -46), ("BA", -38), ("SC", -23), ("AL", -22), ("MT", -18), ("MS", -17),
              ("MG", -12), ("SP", -8), ("DF", -7), ("AP", -7), ("RS", -6), ("PB", -6), ("RJ", -5), ("PI", -4),
              ("AM", -3), ("AC", -3), ("PA", -3), ("RO", 8), ("MA", 10), ("PE", 10), ("PR", 16), ("ES", 20),
              ("GO", 21), ("CE", 100)]
    barras(s, MARGEM, Inches(1.95), Inches(5.6), Inches(5.0), [uf for uf, _ in efeito], [v for _, v in efeito],
           "Efeito do estado além do contexto (Ceará = 100)", formato="+0;-0", minimo=-80, maximo=120,
           cores=[CORAL if v < 0 else TEAL for _, v in efeito], tamanho=10)
    texto(s, Inches(6.65), Inches(2.0), Inches(6.0), Inches(0.4), "Descontado o contexto", tamanho=16,
          cor=ESCURO, negrito=True)
    lista(s, Inches(6.65), Inches(2.5), Inches(6.0), Inches(1.8), [
        "O Ceará alfabetiza muito acima do que sua renda prevê",
        "GO, ES, PR e PE também entregam mais que o esperado",
        "SE, RN, TO e BA entregam menos do que poderiam",
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
    notas(s, "Descontado o contexto, o Ceará entrega muito mais do que sua renda prevê. E há limiares: acima de "
             "8% de distorção ou de meio por cento de abandono, a chance cai.")


# ---------------------------------------------------------------------------
# Pergunta 3 - regiões semelhantes
# ---------------------------------------------------------------------------

def slide_p3_resposta(prs):
    s = novo_slide(prs)
    cabecalho_pergunta(s, 3, "Quais regiões possuem padrões semelhantes?",
                       resposta="cinco perfis; com a mesma pobreza, 21 pontos de diferença")
    imagem(s, mapa_grupos(), MARGEM, TOPO_PERGUNTA - Inches(0.1), Inches(4.9), Inches(4.6),
           "Mapa do Brasil com cada município colorido pelo seu grupo de contexto")
    grupos = [("Fluxo escolar crítico", 41.9), ("Áreas diferenciadas e rurais", 50.0), ("Urbano de maior porte", 59.3),
              ("Vulnerável com fluxo regular", 62.9), ("Pequenos desenvolvidos", 70.5)]
    barras(s, Inches(5.9), TOPO_PERGUNTA, Inches(6.8), Inches(2.9), [g for g, _ in grupos], [v for _, v in grupos],
           "% de alfabetizados por grupo de contexto (2024)", cores=[CORAL, LARANJA, AMARELO, TEAL, ESCURO], maximo=85)
    cartao(s, Inches(5.9), Inches(5.45), Inches(6.8), Inches(1.25))
    texto(s, Inches(6.2), Inches(5.6), Inches(6.2), Inches(1.0), [
        [("Mesma pobreza infantil (~56%) e mesmo INSE: ", {"negrito": True}),
         ("o grupo com fluxo regular alfabetiza 63%; o com fluxo crítico, 42%. "
          "A diferença está na distorção idade-série: 6% contra 16%.", {})],
    ], tamanho=14)
    notas(s, "Terceira pergunta: agrupamos os municípios em cinco perfis de contexto. Dois grupos têm a mesma "
             "pobreza, mas um alfabetiza 63% e o outro 42%. A diferença de 21 pontos está no fluxo escolar.")


def slide_p3_referencias(prs):
    s = novo_slide(prs)
    cabecalho_pergunta(s, 3, "", evidencia="Em todo perfil há municípios que superam o esperado")
    # Desvio positivo (notebook 04, seção 3): redes com 50+ alunos e participação de 80%+ na prova
    referencias = [
        ("Fluxo escolar crítico", "Tartarugalzinho", "AP", 94.2, 43.7),
        ("Fluxo escolar crítico", "Itaueira", "PI", 85.9, 43.7),
        ("Vulnerável com fluxo regular", "Jequiá da Praia", "AL", 95.7, 51.2),
        ("Vulnerável com fluxo regular", "Taperoá", "PB", 90.6, 47.6),
        ("Áreas diferenciadas e rurais", "Barreirinhas", "MA", 78.5, 46.6),
        ("Áreas diferenciadas e rurais", "Atalaia do Norte", "AM", 84.1, 49.3),
        ("Urbano de maior porte", "Corinto", "MG", 85.8, 53.3),
        ("Pequenos desenvolvidos", "Carlinda", "MT", 99.0, 60.9),
    ]
    linhas = [(g, m, uf, pct(real), pct(esperado), f"+{real - esperado:.0f} p.p.")
              for g, m, uf, real, esperado in referencias]
    tabela(s, MARGEM, Inches(2.0), Inches(8.3),
           ["Grupo de contexto", "Município", "UF", "Real", "Esperado", "Acima"], linhas,
           [Inches(2.75), Inches(1.85), Inches(0.6), Inches(0.9), Inches(1.1), Inches(1.1)],
           [PP_ALIGN.LEFT, PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT])
    cartao(s, Inches(9.3), Inches(2.0), Inches(3.4), Inches(3.2))
    texto(s, Inches(9.6), Inches(2.25), Inches(2.8), Inches(0.4), "Como usar", tamanho=17, cor=CORAL, negrito=True)
    lista(s, Inches(9.6), Inches(2.8), Inches(2.85), Inches(2.9), [
        "Comparar cada rede com seus pares de contexto, não com a média do país",
        "Estudar e visitar as referências do mesmo grupo",
        "Validar com as secretarias antes de difundir",
    ], tamanho=14)
    texto(s, MARGEM, Inches(6.0), Inches(8.3), Inches(0.6),
          "Esperado = taxa prevista pelo modelo para o contexto da rede. Redes com 50+ alunos avaliados e "
          "participação de 80%+ na prova.", tamanho=11, cor=SUAVE, italico=True)
    notas(s, "E em todo perfil há municípios que alfabetizam 30 a 50 pontos acima do esperado, como Tartarugalzinho, "
             "no Amapá, e Barreirinhas, no Maranhão. São referências para os pares do mesmo grupo.")


# ---------------------------------------------------------------------------
# Pergunta 4 - risco
# ---------------------------------------------------------------------------

def slide_p4_resposta(prs):
    s = novo_slide(prs)
    cabecalho_pergunta(s, 4, "Quais municípios apresentam maior risco educacional?",
                       resposta="gravidade concentrada na Bahia; volume nas grandes capitais")
    imagem(s, mapa_risco(), MARGEM, TOPO_PERGUNTA - Inches(0.1), Inches(5.0), Inches(4.6),
           "Mapa do Brasil com o índice de risco de cada rede municipal; o risco alto se concentra na Bahia e no Norte")
    for coluna, (titulo, subtitulo, itens) in enumerate([
        ("Por gravidade", "% das redes no decil de maior risco",
         [("Bahia", "84%"), ("Sergipe", "43%"), ("Amazonas", "31%"), ("Rio Grande do Norte", "30%"), ("Pará", "29%")]),
        ("Por volume", "crianças não alfabetizadas (rede municipal)",
         [("São Paulo", "21,6 mil"), ("Rio de Janeiro", "15,7 mil"), ("Manaus", "9,3 mil"), ("Salvador", "7,7 mil")]),
    ]):
        x = Inches(5.95) + coluna * Inches(3.5)
        cartao(s, x, TOPO_PERGUNTA, Inches(3.25), Inches(4.45))
        texto(s, x + Inches(0.3), TOPO_PERGUNTA + Inches(0.2), Inches(2.7), Inches(0.4), titulo, tamanho=18, cor=CORAL,
              negrito=True)
        texto(s, x + Inches(0.3), TOPO_PERGUNTA + Inches(0.62), Inches(2.75), Inches(0.5), subtitulo, tamanho=12,
              cor=SUAVE)
        for i, (nome, valor) in enumerate(itens):
            y = TOPO_PERGUNTA + Inches(1.15) + i * Inches(0.6)
            texto(s, x + Inches(0.3), y, Inches(2.0), Inches(0.5), nome, tamanho=15, ancora=MSO_ANCHOR.MIDDLE)
            texto(s, x + Inches(1.75), y, Inches(1.2), Inches(0.5), valor, tamanho=17, cor=ESCURO, negrito=True,
                  alinhamento=PP_ALIGN.RIGHT, ancora=MSO_ANCHOR.MIDDLE)
    texto(s, Inches(9.75), TOPO_PERGUNTA + Inches(3.65), Inches(2.75), Inches(0.7),
          "São Paulo alfabetiza 48%; o contexto previa 56%", tamanho=13, cor=TEXTO, italico=True)
    notas(s, "Quarta pergunta: onde está o risco? Por gravidade, 84% das redes da Bahia estão no grupo de maior "
             "risco. Por volume, só São Paulo tem 21 mil crianças não alfabetizadas, seguida de Rio, Manaus e Salvador.")


def slide_p4_foco(prs):
    s = novo_slide(prs)
    cabecalho_pergunta(s, 4, "", evidencia="Gravidade e volume juntos: 37 redes, 58 mil crianças")
    ranking = pd.read_csv(DIR_REPORTS / "ranking_risco_municipios_2024.csv")
    foco = ranking[(ranking["indice_risco"] >= 0.85) & (ranking["alunos_avaliados"] >= 1000)]
    foco = foco.sort_values("criancas_nao_alfabetizadas", ascending=False)
    linhas = [
        (r.nome_municipio, r.sigla_uf, pct(r.taxa_alfabetizacao), pct(r.taxa_esperada_contexto),
         pct(r.proba_nao_atingir_meta * 100), f"{r.criancas_nao_alfabetizadas / 1000:.1f} mil".replace(".", ","))
        for r in foco.head(8).itertuples()
    ]
    tabela(s, MARGEM, Inches(2.0), Inches(8.3),
           ["Rede municipal", "UF", "Taxa 2024", "Esperado", "Risco de não bater a meta", "Não alfabetizadas"],
           linhas, [Inches(2.4), Inches(0.6), Inches(1.05), Inches(1.05), Inches(1.6), Inches(1.6)],
           [PP_ALIGN.LEFT, PP_ALIGN.CENTER, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT, PP_ALIGN.RIGHT])
    numero_destaque(s, Inches(9.3), Inches(2.0), Inches(3.4), f"{len(foco)} redes",
                    "com índice de risco alto (≥ 0,85) e 1.000+ alunos avaliados", cor=CORAL, tamanho=36)
    numero_destaque(s, Inches(9.3), Inches(3.75), Inches(3.4),
                    f"{foco['criancas_nao_alfabetizadas'].sum() / 1000:.0f} mil".replace(".", ","),
                    "crianças não alfabetizadas nessas redes", cor=ESCURO, tamanho=36)
    cartao(s, Inches(9.3), Inches(5.35), Inches(3.4), Inches(1.15))
    texto(s, Inches(9.55), Inches(5.5), Inches(2.95), Inches(0.95),
          "Destaque: a Baixada Fluminense (Nova Iguaçu, Duque de Caxias, São Gonçalo, Belford Roxo)",
          tamanho=13, cor=TEXTO)
    notas(s, "Onde gravidade e volume se encontram, há 37 redes grandes e de alto risco, com 58 mil crianças não "
             "alfabetizadas: Salvador, Maceió e a Baixada Fluminense. É por onde começar.")


# ---------------------------------------------------------------------------
# Pergunta 5 - metas futuras
# ---------------------------------------------------------------------------

def slide_p5_resposta(prs):
    s = novo_slide(prs)
    cabecalho_pergunta(s, 5, "Como prever municípios que podem não atingir metas futuras?",
                       resposta="um modelo de transição que vira alerta de prioridade, não sentença")
    passos = [("Aprende", "como as redes de 2023 se saíram frente à meta de 2024"),
              ("Projeta", "a chance de cada rede bater a meta de 2025, com os dados de 2024"),
              ("Protege", "estados com choque atípico, como o RS nas enchentes, não viram tendência")]
    for i, (verbo, descricao) in enumerate(passos):
        y = TOPO_PERGUNTA + i * Inches(0.95)
        circulo(s, MARGEM, y, Inches(0.55), str(i + 1), cor=ESCURO, tamanho=16)
        texto(s, MARGEM + Inches(0.75), y - Inches(0.05), Inches(4.6), Inches(0.9),
              [[(verbo + ": ", {"negrito": True, "cor": ESCURO}), (descricao, {})]], tamanho=15)
    numero_destaque(s, MARGEM, Inches(5.35), Inches(2.6), "54%", "das redes devem bater a meta de 2025", cor=TEAL)
    numero_destaque(s, Inches(3.3), Inches(5.35), Inches(2.6), "1.431", "redes com menos de 40% de chance", cor=CORAL)
    # Variação 2023 -> 2024 da rede municipal descontada a nacional (notebook 04, sensibilidade)
    choques = [("RS", -21.9), ("RO", -5.1), ("PR", -5.0), ("AM", -4.8), ("BA", -3.4), ("PA", -2.3), ("CE", -1.5),
               ("SC", -0.5), ("PE", -0.3), ("RN", 0.1), ("MA", 0.8), ("RJ", 1.0), ("ES", 1.1), ("PB", 2.8), ("AL", 2.9),
               ("MT", 3.4), ("GO", 3.7), ("TO", 4.2), ("AP", 4.7), ("PI", 5.0), ("SE", 5.3), ("MS", 6.5), ("MG", 10.3)]
    barras(s, Inches(6.3), TOPO_PERGUNTA - Inches(0.1), Inches(6.4), Inches(4.65), [uf for uf, _ in choques],
           [round(v) for _, v in choques], "Variação 2023-2024 acima ou abaixo do Brasil (pontos)", formato="+0;-0;0",
           minimo=-27, maximo=15, cores=[CORAL if abs(v) > 10 else ESCURO for _, v in choques], tamanho=10)
    notas(s, "Quinta pergunta: o modelo aprende como as redes se saíram de um ano para o outro e projeta a chance "
             "de bater a meta de 2025. Cerca de 1.400 redes têm menos de 40%. A queda do Rio Grande do Sul nas "
             "enchentes, fora da curva, não vira tendência.")


def slide_p5_validacao(prs):
    s = novo_slide(prs)
    cabecalho_pergunta(s, 5, "", evidencia="Em 2025, o modelo acertou a direção e foi conservador no nível")
    imagem(s, DIR_IMAGENS / "eda_12_metas_estaduais.png", MARGEM, Inches(1.85), Inches(5.4), Inches(5.2),
           "Resultado de 2024 e de 2025 de cada estado comparado com a meta de 2025; 20 de 26 estados bateram a meta")
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
    notas(s, "Conferimos com 2025: o modelo acertou a direção, mas foi conservador, porque 2025 teve um avanço "
             "amplo. A Bahia deu o maior salto do país e merece ser estudada. O modelo serve para priorizar.")


# ---------------------------------------------------------------------------
# Fechamento
# ---------------------------------------------------------------------------

def slide_recomendacoes(prs):
    s = novo_slide(prs)
    cabecalho(s, "Cinco recomendações para a gestão", "VALOR ESTRATÉGICO PARA AS POLÍTICAS PÚBLICAS")
    recomendacoes = [
        ("Priorizar recursos com o ranking de risco",
         "Gravidade para a Bahia e o Nordeste; volume para as grandes redes urbanas"),
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
    notas(s, "Nossas recomendações: priorizar recursos com o ranking de risco, atacar o fluxo escolar, expandir o "
             "regime de colaboração no modelo do Ceará, conectar municípios às suas referências e usar o alerta "
             "de metas antes da prova.")


def slide_encerramento(prs):
    s = novo_slide(prs)
    fundo(s, ESCURO)
    texto(s, MARGEM, Inches(1.4), Inches(11.5), Inches(0.4), "MENSAGEM FINAL", tamanho=14, cor=CORAL, negrito=True)
    texto(s, MARGEM, Inches(1.95), Inches(11.5), Inches(1.6), "Os modelos dizem onde olhar primeiro",
          tamanho=40, cor=BRANCO, negrito=True, fonte=TITULO_FONTE)
    proximos = [("Retreinar", "com os resultados municipais de 2025"),
                ("Validar", "as referências com as secretarias antes de difundi-las"),
                ("Acompanhar", "o efeito das ações nas redes priorizadas a cada ciclo")]
    for i, (verbo, descricao) in enumerate(proximos):
        x = MARGEM + i * Inches(4.1)
        cartao(s, x, Inches(4.0), Inches(3.8), Inches(1.9), cor=ESCURO_CARTAO)
        texto(s, x + Inches(0.35), Inches(4.25), Inches(3.1), Inches(0.5), verbo, tamanho=20, cor=CORAL, negrito=True)
        texto(s, x + Inches(0.35), Inches(4.8), Inches(3.1), Inches(1.0), descricao, tamanho=15, cor=BRANCO)
    texto(s, MARGEM, Inches(6.5), Inches(11.5), Inches(0.4), "Obrigado.", tamanho=16, cor=CLARO)
    notas(s, "Os modelos não substituem o olhar das secretarias: eles dizem onde olhar primeiro. Obrigado.")


SLIDES = [
    slide_capa, slide_agenda, slide_problema, slide_metodo,
    slide_p1_resposta, slide_p1_exemplo,
    slide_p2_resposta, slide_p2_evidencia,
    slide_p3_resposta, slide_p3_referencias,
    slide_p4_resposta, slide_p4_foco,
    slide_p5_resposta, slide_p5_validacao,
    slide_recomendacoes, slide_encerramento,
]


def gerar() -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = LARGURA, ALTURA
    prs.core_properties.title = "Alfabetização no Brasil: cinco perguntas para decidir onde agir"
    prs.core_properties.author = "eliaslopesjr1-maker"
    for construir in SLIDES:
        construir(prs)
    destino = DIR_REPORTS / "apresentacao_executiva.pptx"
    prs.save(destino)
    print(f"apresentação gerada: {destino} ({len(prs.slides)} slides)")
    return destino


if __name__ == "__main__":
    gerar()
