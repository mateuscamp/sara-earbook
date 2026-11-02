# SPDX-License-Identifier: GPL-3.0-or-later
"""A marca d'água: o mesmo parágrafo em metade ou mais dos arquivos do spine (ADR-0008)."""

from __future__ import annotations

import pytest

from earbook.dominio.limpeza import LivroLimpo, limpar_para_o_ouvido
from earbook.dominio.segmento import Papel, Segmento

# Medido no Learning DDD: o último parágrafo de cada um dos 321 arquivos.
MARCA = "OceanofPDF.com"


def _limpar(capitulos: list[list[tuple[Papel, str]]]) -> LivroLimpo:
    entrada = [
        (
            f"c{c:03d}",
            [
                Segmento(f"c{c:03d}-s{s:04d}", papel, texto)
                for s, (papel, texto) in enumerate(segs, 1)
            ],
        )
        for c, segs in enumerate(capitulos, 1)
    ]
    return limpar_para_o_ouvido(entrada, "Livro", "Autor")


def _com_marca(
    arquivos: int, com_marca: int, papel: Papel = Papel.PARAGRAFO, marca: str = MARCA
) -> list[list[tuple[Papel, str]]]:
    """`arquivos` capítulos com um parágrafo próprio cada; os `com_marca` primeiros, com a marca."""
    return [
        [
            (Papel.PARAGRAFO, f"The story of chapter {i} begins."),
            *([(papel, marca)] * (i < com_marca)),
        ]
        for i in range(arquivos)
    ]


def _sobrou(livro: LivroLimpo, texto: str) -> int:
    return sum(s.texto == texto for capitulo in livro.capitulos for s in capitulo.segmentos)


def test_paragrafo_em_todos_os_arquivos_sai_registrado() -> None:
    livro = _limpar(_com_marca(10, 10))
    assert _sobrou(livro, MARCA) == 0
    motivo = "marca d'água: o mesmo parágrafo em 10 de 10 arquivos"
    assert [(r.id, r.motivo, r.texto) for r in livro.remocoes] == [
        (f"c{c:03d}-s0002", motivo, MARCA) for c in range(1, 11)
    ]


@pytest.mark.parametrize(("arquivos", "com_marca", "sobra"), [(22, 11, 0), (24, 11, 11)])
def test_metade_dos_arquivos_basta_e_menos_que_a_metade_fica(
    arquivos: int, com_marca: int, sobra: int
) -> None:
    assert _sobrou(_limpar(_com_marca(arquivos, com_marca)), MARCA) == sobra


def test_menos_de_dez_arquivos_nao_bastam() -> None:
    # Num livro de poucos arquivos (o Huxley tem 4 com texto), 2 ou 3 iguais ainda são texto.
    assert _sobrou(_limpar(_com_marca(9, 9)), MARCA) == 9


@pytest.mark.parametrize("papel", [Papel.TITULO, Papel.CITACAO, Papel.ITEM, Papel.NOTA])
def test_titulo_citacao_item_e_nota_repetidos_ficam(papel: Papel) -> None:
    # "Conclusion", "Exercises", "Questões de revisão" (65% dos arquivos do Dalgalarrondo).
    assert _sobrou(_limpar(_com_marca(10, 10, papel=papel)), MARCA) == 10


def test_paragrafo_sem_letra_fica() -> None:
    # A pausa de cena ("* * *") não se lê como palavra e marca a pausa.
    assert _sobrou(_limpar(_com_marca(10, 10, marca="* * *")), "* * *") == 10


def test_arquivo_sem_segmento_nao_conta() -> None:
    livro = _limpar([*_com_marca(10, 10), *([[]] * 15)])
    assert _sobrou(livro, MARCA) == 0
    assert livro.remocoes[0].motivo == "marca d'água: o mesmo parágrafo em 10 de 10 arquivos"


def test_marca_no_meio_do_paragrafo_partido_deixa_as_metades_se_juntarem() -> None:
    # Como o cabeçalho de página, a marca sai antes da junção (ADR-0003). Cada capítulo tem o seu
    # texto: as metades iguais em todos seriam, elas também, marca d'água.
    partidos = [
        [
            (Papel.PARAGRAFO, f"Chapter {i} goes on until the"),
            (Papel.PARAGRAFO, MARCA),
            (Papel.PARAGRAFO, f"page {i} turns."),
        ]
        for i in range(10)
    ]
    livro = _limpar(partidos)
    assert [[s.texto for s in c.segmentos] for c in livro.capitulos] == [
        [f"Chapter {i} goes on until the page {i} turns."] for i in range(10)
    ]
