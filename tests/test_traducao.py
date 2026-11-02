# SPDX-License-Identifier: GPL-3.0-or-later
"""Os pedidos de tradução por lote (ADR-0006)."""

from __future__ import annotations

import pytest

from earbook.dominio.segmento import Papel, Segmento
from earbook.dominio.traducao import (
    Pedido,
    TrocaDeIdioma,
    idioma_indefinido,
    novos_pedidos,
    precisa_traduzir,
)


def _segmento(posicao: int, palavras: int) -> Segmento:
    return Segmento(f"c005-s{posicao:04d}", Papel.PARAGRAFO, " ".join(["palavra"] * palavras))


def _ids(pedidos: tuple[Pedido, ...]) -> list[tuple[str, list[str]]]:
    return [(p.lote, [s.id for s in p.segmentos]) for p in pedidos]


def test_lote_junta_segmentos_ate_o_limite_de_palavras() -> None:
    limpos = [_segmento(1, 40), _segmento(2, 50), _segmento(3, 20)]
    assert _ids(novos_pedidos("c005", limpos, [], 100)) == [
        ("c005-l001", ["c005-s0001", "c005-s0002"]),
        ("c005-l002", ["c005-s0003"]),
    ]


def test_segmento_maior_que_o_limite_vai_sozinho_e_inteiro() -> None:
    limpos = [_segmento(1, 10), _segmento(2, 300), _segmento(3, 10)]
    assert _ids(novos_pedidos("c005", limpos, [], 100)) == [
        ("c005-l001", ["c005-s0001"]),
        ("c005-l002", ["c005-s0002"]),
        ("c005-l003", ["c005-s0003"]),
    ]


def test_o_que_ja_foi_pedido_nao_e_pedido_de_novo_e_a_numeracao_continua() -> None:
    # É assim que se retoma: rodar o `traduzir` de novo não refaz nenhum lote.
    limpos = [_segmento(1, 10), _segmento(2, 10), _segmento(3, 10)]
    ja = [Pedido("c005-l002", (limpos[0],))]
    assert _ids(novos_pedidos("c005", limpos, ja, 100)) == [
        ("c005-l003", ["c005-s0002", "c005-s0003"]),
    ]


def test_capitulo_todo_pedido_nao_gera_lote() -> None:
    limpos = [_segmento(1, 10)]
    assert novos_pedidos("c005", limpos, [Pedido("c005-l001", tuple(limpos))], 100) == ()


def test_capitulo_vazio_nao_gera_lote() -> None:
    assert novos_pedidos("c001", [], [], 100) == ()


@pytest.mark.parametrize("idioma", ["en", "en-US", "fr", "eng", "en_US"])
def test_livro_que_nao_esta_em_portugues_precisa_de_traducao(idioma: str) -> None:
    assert precisa_traduzir(idioma)


@pytest.mark.parametrize("idioma", ["pt-BR", "pt", "PT-br", "pt-PT", "por", "pt_BR", "POR"])
def test_livro_em_portugues_nao_e_traduzido(idioma: str) -> None:
    # A2 da auditoria: "por" (ISO 639-2) e "pt_BR" viravam livro a traduzir.
    assert not precisa_traduzir(idioma)


@pytest.mark.parametrize("idioma", ["und", "", "  ", "UND"])
def test_livro_de_idioma_indefinido_nao_e_traduzido(idioma: str) -> None:
    # Decisão do Mateus (2026-11-01): monta o texto limpo, como antes do ADR-0006, e o
    # `traduzir` pede o idioma. O PDF importado sem --idioma é "und".
    assert idioma_indefinido(idioma)
    assert not precisa_traduzir(idioma)


def test_portugues_e_ingles_nao_sao_idioma_indefinido() -> None:
    assert not idioma_indefinido("pt-BR")
    assert not idioma_indefinido("en")


def test_troca_de_idioma_troca_a_lingua_do_original_com_qualquer_regiao() -> None:
    troca = TrocaDeIdioma("en", "pt-BR")
    assert [troca.trocar(v) for v in ["en", "en-US", "EN-gb", "fr", "la"]] == [
        "pt-BR",
        "pt-BR",
        "pt-BR",
        "fr",
        "la",
    ]


def test_troca_de_idioma_reconhece_o_codigo_de_tres_letras() -> None:
    # A3 da auditoria: com "eng" no OPF, o `lang="en"` do XHTML ficava em inglês.
    troca = TrocaDeIdioma("eng", "pt-BR")
    assert [troca.trocar(v) for v in ["en", "en_US", "eng", "fra"]] == [
        "pt-BR",
        "pt-BR",
        "pt-BR",
        "fra",
    ]


def test_numeracao_continua_depois_da_resposta_que_perdeu_o_pedido() -> None:
    # Achado da code-review: apagado só o pedido do último lote, o novo reusava o nome e
    # casava com a resposta velha, que passava no `conferir`.
    limpos = [_segmento(1, 10), _segmento(2, 10)]
    ja = [Pedido("c005-l001", (limpos[0],))]
    assert _ids(novos_pedidos("c005", limpos, ja, 100, respondidos=["c005-l002"])) == [
        ("c005-l003", ["c005-s0002"]),
    ]


def test_segmento_maior_que_o_limite_no_comeco_nao_deixa_lote_vazio() -> None:
    limpos = [_segmento(1, 300), _segmento(2, 10)]
    assert _ids(novos_pedidos("c005", limpos, [], 100)) == [
        ("c005-l001", ["c005-s0001"]),
        ("c005-l002", ["c005-s0002"]),
    ]


def test_cada_lote_conta_as_palavras_do_zero() -> None:
    limpos = [_segmento(1, 60), _segmento(2, 50), _segmento(3, 50), _segmento(4, 50)]
    assert _ids(novos_pedidos("c005", limpos, [], 100)) == [
        ("c005-l001", ["c005-s0001"]),
        ("c005-l002", ["c005-s0002", "c005-s0003"]),
        ("c005-l003", ["c005-s0004"]),
    ]


def test_numeracao_continua_depois_do_maior_lote_e_nao_do_primeiro() -> None:
    limpos = [_segmento(1, 10), _segmento(2, 10), _segmento(3, 10)]
    ja = [Pedido("c005-l003", (limpos[1],)), Pedido("c005-l001", (limpos[0],))]
    assert _ids(novos_pedidos("c005", limpos, ja, 100)) == [("c005-l004", ["c005-s0003"])]


def test_lote_de_outro_capitulo_nao_conta_na_numeracao() -> None:
    limpos = [_segmento(1, 10)]
    respondidos = ["c006-l009"]
    assert _ids(novos_pedidos("c005", limpos, [], 100, respondidos)) == [
        ("c005-l001", ["c005-s0001"])
    ]


@pytest.mark.parametrize("idioma", ["Portuguese", "Português", "portugues"])
def test_idioma_por_extenso_em_portugues_nao_e_traduzido(idioma: str) -> None:
    # Fora do padrão BCP 47, mas visto em OPF feito à mão (observação da pós-auditoria).
    assert not precisa_traduzir(idioma)


def test_idioma_ingles_por_extenso_troca_o_lang_do_xhtml() -> None:
    assert TrocaDeIdioma("English", "pt-BR").trocar("en") == "pt-BR"
