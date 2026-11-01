# SPDX-License-Identifier: GPL-3.0-or-later
"""O `conferir` cobra que cada ID de origem foi mantido, removido ou juntado (ADR-0005)."""

from __future__ import annotations

from earbook.dominio.conferencia import (
    CapituloParaConferir,
    Problema,
    conferir,
    conferir_textos,
)
from earbook.dominio.segmento import Papel, Segmento

ORIGEM = ("c001-s0001", "c001-s0002", "c001-s0003", "c001-s0004")


def _capitulo(
    mantidos: tuple[str, ...], marcados: tuple[str, ...] = ORIGEM
) -> CapituloParaConferir:
    return CapituloParaConferir("c001", ORIGEM, mantidos, marcados)


def test_livro_inteiro_mantido_removido_ou_juntado_nao_tem_problema() -> None:
    capitulo = _capitulo(("c001-s0001", "c001-s0002"))
    juntados = [("c001-s0004", "c001-s0002")]
    assert conferir([capitulo], ["c001-s0003"], juntados) == ()


def test_id_de_origem_que_sumiu_e_problema() -> None:
    capitulo = _capitulo(("c001-s0001", "c001-s0002"))
    assert conferir([capitulo], ["c001-s0003"], []) == (
        Problema("c001-s0004", "sumiu: não está em limpos, nas remoções nem nas junções"),
    )


def test_id_mantido_e_removido_ao_mesmo_tempo_e_problema() -> None:
    capitulo = _capitulo(("c001-s0001", "c001-s0002", "c001-s0003", "c001-s0004"))
    assert conferir([capitulo], ["c001-s0003"], []) == (
        Problema("c001-s0003", "aparece 2 vezes entre mantidos, remoções e junções"),
    )


def test_id_que_nao_existe_na_origem_e_problema() -> None:
    mantidos = (*ORIGEM, "c001-s0099")
    assert conferir([_capitulo(mantidos)], [], []) == (
        Problema("c001-s0099", "não existe na origem"),
    )


def test_juncao_em_segmento_que_nao_foi_mantido_e_problema() -> None:
    capitulo = _capitulo(("c001-s0001", "c001-s0002"))
    juntados = [("c001-s0004", "c001-s0003")]
    assert conferir([capitulo], ["c001-s0003"], juntados) == (
        Problema("c001-s0004", "juntado em c001-s0003, que não foi mantido"),
    )


def test_marca_do_xhtml_tem_de_bater_com_a_origem() -> None:
    marcados = ("c001-s0001", "c001-s0002", "c001-s0003", "c001-s0003")
    assert conferir([_capitulo(ORIGEM, marcados)], [], []) == (
        Problema("c001-s0003", "marcado 2 vezes no XHTML"),
        Problema("c001-s0004", "sem marca no XHTML"),
    )


def test_marca_fora_da_origem_e_problema() -> None:
    marcados = (*ORIGEM, "c001-s0099")
    assert conferir([_capitulo(ORIGEM, marcados)], [], []) == (
        Problema("c001-s0099", "marcado no XHTML fora da origem"),
    )


def test_texto_com_caractere_que_o_xml_nao_aceita_e_problema() -> None:
    # Revisão: o lxml recusava o texto sem dizer o arquivo nem o segmento. A tradução vai
    # escrever esses textos; o conferir aponta o ID antes do montar.
    segmentos = [
        Segmento("c001-s0001", Papel.TITULO, "Um"),
        Segmento("c001-s0002", Papel.PARAGRAFO, "a\x0cb\x00"),
    ]
    assert conferir_textos(segmentos) == (
        Problema("c001-s0002", "texto com caractere que o XML não aceita: U+000C, U+0000"),
    )


def test_mantido_no_capitulo_errado_e_problema() -> None:
    # A2 da auditoria: o montar lê os textos do `limpos/` de cada capítulo; o segmento
    # posto no capítulo errado passava no conferir e sumia do livro montado.
    um = CapituloParaConferir(
        "c001", ("c001-s0001", "c001-s0002"), ("c001-s0001",), ("c001-s0001", "c001-s0002")
    )
    dois = CapituloParaConferir(
        "c002", ("c002-s0001",), ("c002-s0001", "c001-s0002"), ("c002-s0001",)
    )
    assert conferir([um, dois], [], []) == (
        Problema("c001-s0002", "mantido no capítulo c002, mas é do c001"),
    )


def test_remocao_repetida_no_registro_da_limpeza_e_problema() -> None:
    # A7 da auditoria: a leitura juntava as repetições antes de contar.
    capitulo = _capitulo(("c001-s0001", "c001-s0002"))
    remocoes = ["c001-s0003", "c001-s0003"]
    assert conferir([capitulo], remocoes, [("c001-s0004", "c001-s0002")]) == (
        Problema("c001-s0003", "aparece 2 vezes entre mantidos, remoções e junções"),
    )


def test_juncao_repetida_no_registro_da_limpeza_e_problema() -> None:
    capitulo = _capitulo(("c001-s0001", "c001-s0002"))
    juntados = [("c001-s0004", "c001-s0002"), ("c001-s0004", "c001-s0002")]
    assert conferir([capitulo], ["c001-s0003"], juntados) == (
        Problema("c001-s0004", "aparece 2 vezes entre mantidos, remoções e junções"),
    )
