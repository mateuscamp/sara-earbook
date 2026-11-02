# SPDX-License-Identifier: GPL-3.0-or-later
"""Subtítulo em negrito do tamanho do corpo: título, e não começo do parágrafo (ADR-0004)."""

from __future__ import annotations

import pytest

from earbook.dominio.capitulos import dividir_em_capitulos
from tests.linhas_de_teste import ENTRELINHA, em_negrito, linha, montar, resumo, texto_corrido


def test_subtitulo_em_negrito_do_tamanho_do_corpo_vira_titulo_fora_do_paragrafo() -> None:
    # Competente: "Pedaços de palavra O modelo não enxerga letras…" saía num parágrafo só.
    pagina = [
        *texto_corrido(0.1),
        em_negrito(linha("Pedaços de palavra", 0.3)),
        linha("O modelo não enxerga letras nem palavras", 0.3 + ENTRELINHA * 1.2),
        linha("inteiras, e sim pedaços.", 0.3 + ENTRELINHA * 2.2),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("titulo", "Pedaços de palavra"),
        ("paragrafo", "O modelo não enxerga letras nem palavras inteiras, e sim pedaços."),
    ]


def test_secao_em_negrito_maior_que_o_corpo_e_menor_que_titulo_vira_titulo() -> None:
    # Competente: a seção de 12 pt, com corpo de 10,5, ficava abaixo de 1,2 vez o corpo e
    # saía como parágrafo ("O corretor do celular, só que enorme").
    pagina = [
        *texto_corrido(0.1),
        em_negrito(linha("O corretor do celular, só que enorme", 0.3, tamanho=12)),
        *texto_corrido(0.35),
    ]
    assert resumo(montar(pagina))[1] == ("titulo", "O corretor do celular, só que enorme")


def test_subtitulo_em_negrito_de_duas_linhas_vira_um_titulo_so() -> None:
    pagina = [
        *texto_corrido(0.1),
        em_negrito(linha("Um modelo de IA dentro do teste", 0.3)),
        em_negrito(linha("de integração", 0.3 + ENTRELINHA)),
        linha("O teste do capítulo roda sozinho.", 0.3 + ENTRELINHA * 2.2),
    ]
    assert resumo(montar(pagina))[-2:] == [
        ("titulo", "Um modelo de IA dentro do teste de integração"),
        ("paragrafo", "O teste do capítulo roda sozinho."),
    ]


def test_negrito_menor_que_o_corpo_nao_vira_titulo() -> None:
    # Hard Parts: o cabeçalho de tabela ("Instances", p. 160) e o rodapé de seção vêm em
    # semibold de 9 pt, com corpo de 10,5, acima de 0,85 do corpo. Subtítulo nunca é menor que
    # o corpo nos livros medidos.
    pagina = [*texto_corrido(0.1), em_negrito(linha("Instances", 0.3, 174, tamanho=9))]
    assert resumo(montar(pagina))[-1:] == [("paragrafo", "Instances")]


def test_codigo_em_negrito_continua_codigo() -> None:
    pagina = [*texto_corrido(0.1), em_negrito(linha("def f(): pass", 0.3, mono=True))]
    assert resumo(montar(pagina))[-1:] == [("codigo", "def f(): pass")]


def test_pedaco_em_negrito_ao_lado_de_pedaco_comum_segue_paragrafo() -> None:
    # Hard Parts p. 129: "Ticket Shared" em negrito ao lado de "ss.ticket.shared" na mesma
    # altura. A linha visual é negrito só se todo pedaço for.
    pagina = [
        *texto_corrido(0.1),
        em_negrito(linha("Ticket Shared", 0.3)),
        linha("ss.ticket.shared", 0.3, 200),
    ]
    assert resumo(montar(pagina))[-1:] == [("paragrafo", "Ticket Shared ss.ticket.shared")]


def test_livro_com_o_corpo_em_negrito_continua_em_paragrafos() -> None:
    # Revisão nº 1: com o corpo inteiro numa fonte de nome negrito ("-Semibold"), toda linha
    # virava título, e o livro saía sem nenhum parágrafo.
    pagina = [em_negrito(corpo) for corpo in [*texto_corrido(0.1), *texto_corrido(0.3)]]
    assert [tipo for tipo, _ in resumo(montar(pagina))] == ["paragrafo", "paragrafo"]


def test_item_de_lista_em_negrito_comeca_titulo_novo() -> None:
    # Revisão nº 2: no sumário do Hard Parts, "Preface … xi" e "1. What Happens…" eram dois
    # parágrafos (o "1." abre item de lista) e viraram um título só.
    pagina = [
        *texto_corrido(0.1),
        em_negrito(linha("Preface . . . xi", 0.3, tamanho=12)),
        em_negrito(linha("1. What Happens . . . 1", 0.3 + ENTRELINHA, tamanho=12)),
        *texto_corrido(0.4),
    ]
    assert resumo(montar(pagina))[1:3] == [
        ("titulo", "Preface . . . xi"),
        ("titulo", "1. What Happens . . . 1"),
    ]


@pytest.mark.parametrize(
    ("tamanho", "tipo"), [(10.0, "titulo"), (9.9, "paragrafo")], ids=["no-piso", "abaixo"]
)
def test_negrito_ate_meio_ponto_abaixo_do_corpo_ainda_e_titulo(tamanho: float, tipo: str) -> None:
    # Revisão nº 5: o cabeçalho de tabela do Hard Parts tem 10 pt, com corpo de 10,5.
    pagina = [*texto_corrido(0.1), em_negrito(linha("Advantages", 0.3, tamanho=tamanho))]
    assert resumo(montar(pagina))[-1:] == [(tipo, "Advantages")]


def test_itens_em_negrito_separados_por_vao_de_paragrafo_nao_viram_um_titulo_so() -> None:
    # A1 da auditoria: no sumário do Hard Parts (p. 12), "A. Concept…", "B. Architecture…",
    # "C. Trade-Off…" e "Index", em negrito de 12 pt a 2 entrelinhas um do outro, eram quatro
    # parágrafos e saíam num título só.
    pagina = [
        *texto_corrido(0.1),
        em_negrito(linha("A. Concept and Term References . . . 417", 0.3, tamanho=12)),
        em_negrito(linha("B. Architecture References . . . 419", 0.3 + ENTRELINHA * 2, tamanho=12)),
        *texto_corrido(0.4),
    ]
    assert resumo(montar(pagina))[1:3] == [
        ("titulo", "A. Concept and Term References . . . 417"),
        ("titulo", "B. Architecture References . . . 419"),
    ]


def test_sem_entrelinha_medida_o_titulo_de_duas_linhas_segue_junto() -> None:
    # Sem duas linhas de parágrafo seguidas na página não há entrelinha, e o vão do título
    # (A1 da auditoria) não tem régua: o título segue junto, como antes.
    pagina = [
        em_negrito(linha("Um título", 0.3)),
        em_negrito(linha("de duas linhas", 0.3 + ENTRELINHA * 2)),
        linha("Uma linha só de texto corrido, bem mais longa que o título inteiro.", 0.4),
    ]
    assert resumo(montar(pagina))[:1] == [("titulo", "Um título de duas linhas")]


def test_letra_de_tamanho_zero_nao_derruba_a_montagem() -> None:
    # Um PDF com o texto todo em tamanho 0 (camada invisível) mede corpo 0: toda linha é
    # título grande perto dele, e as duas seguem num título só, sem conta com o corpo.
    pagina = [linha("Camada", 0.3, tamanho=0), linha("invisível", 0.3 + ENTRELINHA, tamanho=0)]
    assert resumo(montar(pagina)) == [("titulo", "Camada invisível")]


# N1 da pós-auditoria: o item de lista e o vão de parágrafo quebram só o título da faixa do
# subtítulo; o título grande em duas linhas é um título só, e um capítulo só.
TITULO_GRANDE = 24.0
ENTRELINHA_DO_TITULO = ENTRELINHA * TITULO_GRANDE / 10.5


def test_rotulo_e_nome_do_capitulo_separados_por_linha_em_branco_seguem_um_titulo() -> None:
    pagina = [
        linha("CAPÍTULO 1", 0.1, tamanho=TITULO_GRANDE),
        linha("O começo", 0.1 + 2 * ENTRELINHA_DO_TITULO, tamanho=TITULO_GRANDE),
        *texto_corrido(0.3),
    ]
    assert resumo(montar(pagina))[:1] == [("titulo", "CAPÍTULO 1 O começo")]


def test_titulo_grande_que_quebra_antes_do_travessao_segue_um_titulo() -> None:
    pagina = [
        linha("Arquitetura de software", 0.1, tamanho=TITULO_GRANDE),
        linha("— as partes difíceis", 0.1 + ENTRELINHA_DO_TITULO, tamanho=TITULO_GRANDE),
        *texto_corrido(0.3),
    ]
    esperado = [("titulo", "Arquitetura de software — as partes difíceis")]
    assert resumo(montar(pagina))[:1] == esperado


def test_capitulo_de_titulo_em_duas_linhas_nao_vira_dois_capitulos() -> None:
    paginas = [
        [
            linha(f"CAPÍTULO {n}", 0.1, tamanho=TITULO_GRANDE),
            linha("O começo", 0.1 + 2 * ENTRELINHA_DO_TITULO, tamanho=TITULO_GRANDE),
            *texto_corrido(0.3),
        ]
        for n in range(1, 4)
    ]
    assert len(dividir_em_capitulos(montar(*paginas).blocos)) == 3
