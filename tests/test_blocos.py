# SPDX-License-Identifier: GPL-3.0-or-later
"""Montagem de blocos: parágrafo, título, código, nota, lista, tabela e retomada (ADR-0004)."""

from __future__ import annotations

from tests.linhas_de_teste import ENTRELINHA, RECUO, linha, montar, resumo, texto_corrido


def test_linhas_do_mesmo_paragrafo_viram_um_bloco_so() -> None:
    pagina = [
        *texto_corrido(0.1),
        linha("Era uma vez um livro", 0.3, RECUO),
        linha("que virou áudio.", 0.3 + ENTRELINHA),
    ]
    assert resumo(montar(pagina))[-1:] == [("paragrafo", "Era uma vez um livro que virou áudio.")]


def test_recuo_da_primeira_linha_comeca_paragrafo_novo() -> None:
    pagina = [
        *texto_corrido(0.1),
        linha("Primeiro parágrafo", 0.3, RECUO),
        linha("termina aqui.", 0.3 + ENTRELINHA),
        linha("Segundo parágrafo", 0.3 + 2 * ENTRELINHA, RECUO),
        linha("começa recuado.", 0.3 + 3 * ENTRELINHA),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("paragrafo", "Primeiro parágrafo termina aqui."),
        ("paragrafo", "Segundo parágrafo começa recuado."),
    ]


def test_espaco_maior_entre_linhas_comeca_paragrafo_novo() -> None:
    # O Hard Parts separa parágrafo por espaço (0,028 contra 0,019), sem recuo.
    pagina = [
        *texto_corrido(0.1),
        linha("Um parágrafo sem recuo.", 0.3),
        linha("Outro, depois de um espaço.", 0.3 + 1.7 * ENTRELINHA),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("paragrafo", "Um parágrafo sem recuo."),
        ("paragrafo", "Outro, depois de um espaço."),
    ]


def test_citacao_com_todas_as_linhas_recuadas_vira_um_bloco_e_o_texto_seguinte_outro() -> None:
    pagina = [
        *texto_corrido(0.1),
        linha("Uma citação longa,", 0.3, 70),
        linha("toda recuada,", 0.3 + ENTRELINHA, 70),
        linha("em três linhas.", 0.3 + 2 * ENTRELINHA, 70),
        linha("O texto volta à margem.", 0.3 + 3 * ENTRELINHA),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("paragrafo", "Uma citação longa, toda recuada, em três linhas."),
        ("paragrafo", "O texto volta à margem."),
    ]


def test_ordem_das_linhas_segue_o_topo_da_pagina() -> None:
    # O pdfminer devolveu linhas fora de ordem: 41 no Competente e 226 no Hard Parts.
    pagina = [
        *texto_corrido(0.1),
        linha("que virou áudio.", 0.3 + ENTRELINHA),
        linha("Era uma vez um livro", 0.3, RECUO),
    ]
    assert resumo(montar(pagina))[-1:] == [("paragrafo", "Era uma vez um livro que virou áudio.")]


def test_fonte_grande_vira_titulo_e_linhas_seguidas_do_mesmo_tamanho_se_juntam() -> None:
    pagina = [
        linha("What Happens When There", 0.05, tamanho=25.2),
        linha("Are No Best Practices?", 0.09, tamanho=25.2),
        *texto_corrido(0.2),
    ]
    assert resumo(montar(pagina))[:1] == [
        (
            "titulo",
            "What Happens When There Are No Best Practices?",
        )
    ]


def test_linhas_monoespacadas_viram_bloco_de_codigo_com_quebra_de_linha() -> None:
    pagina = [
        *texto_corrido(0.1),
        linha("def f():", 0.3, mono=True),
        linha("    return 1", 0.3 + ENTRELINHA, mono=True),
    ]
    assert resumo(montar(pagina))[-1:] == [("codigo", "def f():\n    return 1")]


def test_fonte_menor_no_pe_vira_nota() -> None:
    pagina = [*texto_corrido(0.1), linha("1 Ver o capítulo 3.", 0.88, tamanho=8)]
    assert resumo(montar(pagina))[-1:] == [("nota", "1 Ver o capítulo 3.")]


def test_paragrafo_continua_na_pagina_seguinte_sem_recuo() -> None:
    pagina1 = [*texto_corrido(0.1), linha("Uma frase que atravessa", 0.8, RECUO)]
    pagina2 = [linha("a quebra de página.", 0.1), *texto_corrido(0.2)]
    textos = [texto for _, texto in resumo(montar(pagina1, pagina2))]
    assert "Uma frase que atravessa a quebra de página." in textos


def test_pagina_seguinte_com_recuo_comeca_paragrafo_novo() -> None:
    pagina1 = [*texto_corrido(0.1), linha("Um parágrafo termina.", 0.8, RECUO)]
    pagina2 = [
        linha("Outro começa recuado", 0.1, RECUO),
        linha("na outra página.", 0.1 + ENTRELINHA),
    ]
    textos = [texto for _, texto in resumo(montar(pagina1, pagina2))]
    assert textos[-2:] == ["Um parágrafo termina.", "Outro começa recuado na outra página."]


def test_item_de_lista_com_recuo_deslocado_fica_inteiro() -> None:
    # Competente e Hard Parts: o item começa em x = 58 e continua em x = 70. Recuar mais que a
    # primeira linha não é parágrafo novo quando ela não fechou a frase.
    pagina = [
        *texto_corrido(0.1),
        linha("\u2013 a profissional que leu que o trabalho", 0.3, 58),
        linha("dela vai acabar;", 0.3 + ENTRELINHA, 70),
        linha("\u2013 o pai que viu um vídeo sobre", 0.3 + 2 * ENTRELINHA, 58),
        linha("a inteligência superior.", 0.3 + 3 * ENTRELINHA, 70),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("paragrafo", "\u2013 a profissional que leu que o trabalho dela vai acabar;"),
        ("paragrafo", "\u2013 o pai que viu um vídeo sobre a inteligência superior."),
    ]


def test_paragrafo_de_uma_linha_seguido_de_recuo_comeca_outro() -> None:
    pagina = [
        *texto_corrido(0.1),
        linha("Era uma vez.", 0.3),
        linha("Outro parágrafo começa", 0.3 + ENTRELINHA, RECUO),
        linha("recuado.", 0.3 + 2 * ENTRELINHA),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("paragrafo", "Era uma vez."),
        ("paragrafo", "Outro parágrafo começa recuado."),
    ]


def test_celulas_na_mesma_altura_viram_uma_linha_da_tabela() -> None:
    # Hard Parts: cada célula vinha como linha própria, e cada uma virava um parágrafo.
    pagina = [
        *texto_corrido(0.1),
        linha("Epic Saga", 0.5, 76),
        linha("synchronous", 0.5, 174),
        linha("atomic", 0.5, 239),
        linha("Fairy Tale", 0.5 + ENTRELINHA, 76),
        linha("asynchronous", 0.5 + ENTRELINHA, 174),
        linha("eventual", 0.5 + ENTRELINHA, 239),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("paragrafo", "Epic Saga synchronous atomic"),
        ("paragrafo", "Fairy Tale asynchronous eventual"),
    ]


def test_aspa_no_fim_da_linha_nao_fecha_a_frase_do_item() -> None:
    # Competente p. 11: "uma “transformação com IA”" seguia na linha de baixo, e a aspa de
    # fechamento contada como fim de frase partia o item ao meio.
    pagina = [
        *texto_corrido(0.1),
        linha("\u2013 a gerente a quem vendem uma “transformação”", 0.3, 58),
        linha("que ninguém explica;", 0.3 + ENTRELINHA, 70),
    ]
    assert resumo(montar(pagina))[-1:] == [
        ("paragrafo", "\u2013 a gerente a quem vendem uma “transformação” que ninguém explica;")
    ]


def test_item_de_lista_recuado_4_pontos_comeca_paragrafo_novo() -> None:
    # Competente: o primeiro item da lista fica em x = 58, só 4 pt dentro da margem (794 linhas).
    pagina = [
        *texto_corrido(0.1),
        linha(
            "\u2013 um item curto;", 0.1 + 6 * ENTRELINHA, 58.2
        ),  # logo abaixo: só o recuo separa
    ]
    assert resumo(montar(pagina))[-1:] == [("paragrafo", "\u2013 um item curto;")]


def test_item_de_lista_no_alto_da_pagina_nova_comeca_paragrafo_novo() -> None:
    # Competente pp. 10-11: o parágrafo terminava em ":" e o primeiro item, no alto da página
    # seguinte, começa com travessão, não com maiúscula.
    pagina1 = [*texto_corrido(0.1), linha("Talvez você seja:", 0.8, RECUO)]
    pagina2 = [linha("\u2013 a profissional que leu;", 0.1, 58.2), *texto_corrido(0.2)]
    textos = [texto for _, texto in resumo(montar(pagina1, pagina2))]
    assert "\u2013 a profissional que leu;" in textos


def test_item_numerado_comeca_paragrafo_mesmo_com_pouco_espaco() -> None:
    # Hard Parts p. 45: os itens vinham a 1,32 entrelinha um do outro, abaixo do limiar de
    # 1,35, e o "3." grudava no "2."; o "systems." recuado do item 3 então partia o bloco.
    pagina = [
        *texto_corrido(0.1),
        linha("2. Analyze how they are coupled.", 0.3, 77.3),
        linha("3. Assess trade-offs by determining the impact on", 0.3 + 1.32 * ENTRELINHA, 77.3),
        linha("systems.", 0.3 + 2.32 * ENTRELINHA, 90),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("paragrafo", "2. Analyze how they are coupled."),
        ("paragrafo", "3. Assess trade-offs by determining the impact on systems."),
    ]


def test_ano_no_comeco_da_linha_nao_e_item_de_lista() -> None:
    pagina = [
        *texto_corrido(0.1),
        linha("A crise começou em", 0.3, RECUO),
        linha("2020. Depois veio o resto.", 0.3 + ENTRELINHA),
    ]
    assert resumo(montar(pagina))[-1:] == [
        ("paragrafo", "A crise começou em 2020. Depois veio o resto.")
    ]


def test_linha_partida_em_dois_pedacos_na_mesma_altura_segue_no_paragrafo() -> None:
    # Hard Parts p. 60: o pdfminer partiu "…understanding commun" (x 72) e "in" (x 423) na
    # mesma altura; tratar como tabela cortava o parágrafo na linha seguinte.
    pagina = [
        *texto_corrido(0.1),
        linha("We focus on dynamic coupling and communication patterns", 0.3, RECUO),
        linha("in", 0.3, 423),
        linha("microservices.", 0.3 + ENTRELINHA),
    ]
    assert resumo(montar(pagina))[-1:] == [
        ("paragrafo", "We focus on dynamic coupling and communication patterns in microservices.")
    ]


def test_texto_que_contorna_figura_e_volta_a_margem_segue_no_paragrafo() -> None:
    # Hard Parts p. 60: a fala começa em x = 114, ao lado de um ícone, e continua em x = 72
    # depois dele, no meio da frase.
    pagina = [
        *texto_corrido(0.1),
        linha("Addison laughed, I know what you mean. I struggle", 0.4, 114),
        linha("with it, but when you ground it in practical", 0.4 + ENTRELINHA, 114),
        linha("perspectives.", 0.4 + 2 * ENTRELINHA, 72),
    ]
    assert resumo(montar(pagina))[-1:] == [
        (
            "paragrafo",
            (
                "Addison laughed, I know what you mean. I struggle with it, but when you ground"
                " it in practical perspectives."
            ),
        )
    ]


def test_legenda_no_meio_do_paragrafo_vai_para_depois_dele() -> None:
    # Competente p. 33: o parágrafo contorna a figura, e a legenda (8,5 pt) caía entre as
    # duas metades da frase. A legenda fica depois do parágrafo inteiro.
    pagina = [
        *texto_corrido(0.1),
        linha("Escalar o modelo pede mais", 0.3, RECUO),
        linha("Figura 1.2 O custo de cada salto.", 0.5, tamanho=8.5),
        linha("memória e mais energia.", 0.7),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("paragrafo", "Escalar o modelo pede mais memória e mais energia."),
        ("nota", "Figura 1.2 O custo de cada salto."),
    ]


def test_paragrafo_que_fechou_a_frase_nao_e_retomado_depois_da_nota() -> None:
    pagina = [
        *texto_corrido(0.1),
        linha("O parágrafo terminou.", 0.3, RECUO),
        linha("Figura 1.2 Uma legenda.", 0.5, tamanho=8.5),
        linha("e esta linha começa outro bloco", 0.7),
    ]
    assert resumo(montar(pagina))[-3:] == [
        ("paragrafo", "O parágrafo terminou."),
        ("nota", "Figura 1.2 Uma legenda."),
        ("paragrafo", "e esta linha começa outro bloco"),
    ]


def test_paragrafo_aberto_nao_e_retomado_depois_de_titulo() -> None:
    # Revisão nº 1: com título aberto, a linha minúscula colava no parágrafo de antes do
    # título, e o título ia parar depois do texto da seção seguinte.
    pagina = [
        *texto_corrido(0.1),
        linha("Uma frase que fica sem ponto", 0.3, RECUO),
        linha("Seção Nova", 0.4, tamanho=19),
        linha("continua em minúscula.", 0.45, RECUO),
    ]
    assert resumo(montar(pagina))[-3:] == [
        ("paragrafo", "Uma frase que fica sem ponto"),
        ("titulo", "Seção Nova"),
        ("paragrafo", "continua em minúscula."),
    ]


def test_pedacos_na_mesma_altura_se_juntam_da_esquerda_para_a_direita() -> None:
    # Revisão nº 2: Hard Parts tem 618 pedaços (células de tabela, "October 2021: First
    # Edition") cujo da direita fica um pouco mais alto e vinha primeiro.
    pagina = [
        *texto_corrido(0.1),
        linha("A linha começa aqui e", 0.3, RECUO),
        linha("termina ali.", 0.3 - 0.002, 300),
    ]
    assert resumo(montar(pagina))[-1:] == [("paragrafo", "A linha começa aqui e termina ali.")]


def test_titulo_encerra_o_paragrafo_interrompido_mesmo_com_nota_depois() -> None:
    # A4 da auditoria (M14): parágrafo sem ponto, título, epígrafe em letra pequena e linha
    # minúscula. O título fecha a retomada; senão o parágrafo pulava o título e a nota.
    pagina = [
        *texto_corrido(0.1),
        linha("Uma frase que fica sem ponto", 0.3, RECUO),
        linha("Seção Nova", 0.4, tamanho=19),
        linha("Uma epígrafe curta.", 0.45, tamanho=8.5),
        linha("continua em minúscula.", 0.5, RECUO),
    ]
    assert resumo(montar(pagina))[-4:] == [
        ("paragrafo", "Uma frase que fica sem ponto"),
        ("titulo", "Seção Nova"),
        ("nota", "Uma epígrafe curta."),
        ("paragrafo", "continua em minúscula."),
    ]


def test_linha_de_tabela_nao_entra_no_paragrafo_aberto() -> None:
    # A4 da auditoria (M15): parágrafo sem ponto seguido de linha de tabela na margem.
    pagina = [
        *texto_corrido(0.1),
        linha("A tabela abaixo mostra", 0.3, RECUO),
        linha("Epic", 0.3 + ENTRELINHA),
        linha("sync", 0.3 + ENTRELINHA, 200),
        linha("atomic", 0.3 + ENTRELINHA, 350),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("paragrafo", "A tabela abaixo mostra"),
        ("paragrafo", "Epic sync atomic"),
    ]


def test_prosa_e_codigo_na_mesma_altura_seguem_no_paragrafo() -> None:
    # A4 da auditoria (M18): a linha visual só é código se todos os pedaços são.
    pagina = [
        *texto_corrido(0.1),
        linha("O componente fica no", 0.3, RECUO),
        linha("namespace", 0.3 + ENTRELINHA),
        linha("ss.survey", 0.3 + ENTRELINHA, 120, mono=True),
        linha("antes de tudo.", 0.3 + 2 * ENTRELINHA),
    ]
    texto = "O componente fica no namespace ss.survey antes de tudo."
    assert resumo(montar(pagina))[-1:] == [("paragrafo", texto)]
