# SPDX-License-Identifier: GPL-3.0-or-later
"""Os lotes da adaptação e as siglas candidatas (ADR-0009)."""

from __future__ import annotations

from earbook.dominio.adaptacao import em_lotes_por_frase, pedidos_da_adaptacao
from earbook.dominio.glossario import EntradaDoGlossario
from earbook.dominio.segmento import Papel, Segmento
from earbook.dominio.siglas import CandidatoASigla, siglas_candidatas
from earbook.dominio.traducao import Pedido


def _paragrafo(posicao: int, palavras: int, fim: str = ".", comeco: str = "Palavra") -> Segmento:
    texto = " ".join([comeco, *["palavra"] * (palavras - 2), "fim"]) + fim
    return Segmento(f"c005-s{posicao:04d}", Papel.PARAGRAFO, texto)


def _titulo(posicao: int) -> Segmento:
    return Segmento(f"c005-s{posicao:04d}", Papel.TITULO, "Distimia")


def _ids(pedidos: tuple[Pedido, ...]) -> list[list[str]]:
    return [[s.id for s in p.segmentos] for p in pedidos]


def test_lote_termina_antes_do_titulo_que_esta_depois_da_metade() -> None:
    limpos = [_paragrafo(1, 40), _paragrafo(2, 40), _titulo(3), _paragrafo(4, 40)]
    assert _ids(pedidos_da_adaptacao("c005", limpos, [], 100)) == [
        ["c005-s0001", "c005-s0002"],
        ["c005-s0003", "c005-s0004"],
    ]


def test_lote_nao_parte_a_frase_que_o_destaque_interrompe() -> None:
    """ "…no período da ma-" | destaque | "nhã…": o grupo que emenda a frase fica num lote."""
    limpos = [
        _paragrafo(1, 45, fim=" ma-"),
        _paragrafo(2, 30),
        _paragrafo(3, 30, comeco="nhã"),
        _paragrafo(4, 30),
    ]
    assert _ids(pedidos_da_adaptacao("c005", limpos, [], 100)) == [
        ["c005-s0001", "c005-s0002", "c005-s0003"],
        ["c005-s0004"],
    ]


def test_lote_corta_entre_frases_quando_nao_ha_titulo() -> None:
    limpos = [_paragrafo(1, 30), _paragrafo(2, 30), _paragrafo(3, 30, fim=",")]
    limpos += [_paragrafo(4, 30, comeco="e")]
    assert _ids(pedidos_da_adaptacao("c005", limpos, [], 100)) == [
        ["c005-s0001", "c005-s0002"],
        ["c005-s0003", "c005-s0004"],
    ]


def test_capitulo_que_cabe_num_lote_vai_inteiro_e_numerado() -> None:
    limpos = [_titulo(1), _paragrafo(2, 10)]
    pedidos = pedidos_da_adaptacao("c005", limpos, [], 100)
    assert [(p.lote, len(p.segmentos)) for p in pedidos] == [("c005-l001", 2)]


def _segmentos(*textos: str) -> list[Segmento]:
    return [Segmento(f"c001-s{n:04d}", Papel.PARAGRAFO, t) for n, t in enumerate(textos, 1)]


def test_sigla_candidata_traz_vezes_exemplo_e_o_extenso_que_o_livro_da() -> None:
    segmentos = _segmentos(
        "O sistema reticular ativador ascendente (SRAA) regula a vigília.",
        "O SRAA se origina no tronco cerebral, segundo a OMS.",
    )
    assert siglas_candidatas(segmentos, ()) == (
        CandidatoASigla("SRAA", 2, "c001-s0001", "sistema reticular ativador ascendente"),
        CandidatoASigla("OMS", 1, "c001-s0002", ""),
    )


def test_extenso_pula_preposicao_e_parte_na_barra() -> None:
    segmentos = _segmentos("O transtorno de déficit de atenção/hiperatividade (TDAH) é comum.")
    assert [c.extenso for c in siglas_candidatas(segmentos, ())] == [
        "transtorno de déficit de atenção/hiperatividade"
    ]


def test_extenso_que_nao_bate_com_a_inicial_fica_vazio() -> None:
    segmentos = _segmentos("Os pacientes do estudo de campo (TB) melhoraram.")
    assert [c.extenso for c in siglas_candidatas(segmentos, ())] == [""]


def test_palavra_em_caixa_alta_que_o_livro_escreve_em_minuscula_nao_e_sigla() -> None:
    segmentos = _segmentos(
        "SINTOMAS AFETIVOS DA DEPRESSÃO",
        "Os sintomas da depressão e o DSM-IV, no CAPÍTULO de sintomas.",
        "O capítulo diz.",
    )
    assert [c.sigla for c in siglas_candidatas(segmentos, ())] == ["DSM-IV"]


def test_algarismo_romano_e_sigla_do_glossario_ficam_de_fora() -> None:
    segmentos = _segmentos("O tipo II e o tipo IV, segundo a OMS e o QI medido.")
    glossario = (EntradaDoGlossario("OMS", "OMS"),)
    assert [c.sigla for c in siglas_candidatas(segmentos, glossario)] == ["QI"]


def test_lote_sem_corte_seguro_nao_passa_de_duas_vezes_o_limite() -> None:
    """A5 da auditoria: a lista sem ponto e sem título fazia um lote do capítulo inteiro."""
    itens = [_paragrafo(n, 26, fim="", comeco="\u2013 item") for n in range(1, 301)]
    lotes = em_lotes_por_frase(itens, 2000)
    assert len(lotes) > 1
    assert max(sum(len(s.texto.split()) for s in lote) for lote in lotes) <= 4000


def test_lote_nao_corta_antes_da_metade_e_cresce_ate_o_corte_seguro() -> None:
    """Abaixo da metade do limite, o corte entre frases deixaria um lote de 10 palavras."""
    limpos = [_paragrafo(1, 10), _paragrafo(2, 80, fim=","), _paragrafo(3, 30, comeco="e")]
    assert _ids(pedidos_da_adaptacao("c005", limpos, [], 100)) == [
        ["c005-s0001", "c005-s0002", "c005-s0003"]
    ]


def test_titulo_ganha_do_corte_entre_frases() -> None:
    limpos = [_paragrafo(1, 30), _paragrafo(2, 30), _titulo(3), _paragrafo(4, 30)]
    limpos += [_paragrafo(5, 30)]
    assert _ids(pedidos_da_adaptacao("c005", limpos, [], 100)) == [
        ["c005-s0001", "c005-s0002"],
        ["c005-s0003", "c005-s0004", "c005-s0005"],
    ]
