# SPDX-License-Identifier: GPL-3.0-or-later
"""O texto repetido por cima, do mesmo tamanho, é lido uma vez só (ADR-0004, "Negrito feito à
mão").

Na p. 2 do Dalgalarrondo, "Conheça também" (24 pt) está desenhado cinco vezes, deslocado de 0,5 a
1 pt, para engrossar a letra. O pdfminer devolve 9 linhas na mesma altura ("Conheça", "também" e
"Conheça também"), e a voz lia "Conheça Conheça Conheça também…". Na p. 5 do Hard Parts, "Beijing
Beijing Boston Boston…" é o mesmo defeito.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from earbook.comandos.cli import principal
from earbook.comandos.importar_pdf import importar_pdf
from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.paginacao import LinhaRemovida
from earbook.dominio.texto_escondido import (
    MOTIVO_DO_ESCONDIDO,
    MOTIVO_DO_REPETIDO,
    tirar_texto_escondido,
)
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf


def _linha(texto: str, x: float, fim: float, tamanho: float = 24.0, topo: float = 0.2244) -> Linha:
    return Linha(texto, x=x, fim=fim, topo=topo, tamanho=tamanho)


def _tirar(*linhas: Linha) -> tuple[list[str], tuple[LinhaRemovida, ...]]:
    limpas = tirar_texto_escondido([Pagina(2, linhas)])
    return [linha.texto for linha in limpas.paginas[0].linhas], limpas.remocoes


def test_copia_do_mesmo_tamanho_por_cima_sai_e_fica_a_primeira() -> None:
    um = _linha("Conheça também", 66.5, 235.7)
    outro = _linha("Conheça também", 66.0, 235.2, topo=0.2249)
    assert _tirar(um, outro) == (
        ["Conheça também"],
        (LinhaRemovida(2, MOTIVO_DO_REPETIDO, "Conheça também"),),
    )


def test_palavras_contidas_na_linha_que_as_cobre_saem() -> None:
    # As 9 linhas da p. 2 do Dalgalarrondo, como o pdfminer as devolve.
    linhas = [
        _linha("também", 156.4, 234.9),
        _linha("também", 157.1, 235.7),
        _linha("Conheça", 66.1, 155.6),
        _linha("Conheça", 66.9, 156.3),
        _linha("também", 156.8, 235.3, topo=0.2249),
        _linha("Conheça também", 66.5, 235.7, topo=0.2249),
        _linha("também", 156.4, 234.9, topo=0.2254),
        _linha("Conheça", 66.9, 156.4, topo=0.2254),
        _linha("Conheça", 66.2, 155.6, topo=0.2254),
    ]
    sobrou, remocoes = _tirar(*linhas)
    assert (sobrou, len(remocoes)) == (["Conheça também"], 8)


def test_copia_de_uma_letra_so_fica() -> None:
    # Hard Parts p. 462: o texto vertical vem uma letra por linha, e o "ll" de "Reilly" são duas
    # linhas iguais, a 0,0014 de altura uma da outra.
    um = _linha("l", 470.0, 474.5, tamanho=0.8, topo=0.7562)
    outro = _linha("l", 470.0, 474.5, tamanho=0.8, topo=0.7576)
    assert _tirar(um, outro) == (["l", "l"], ())


def test_copia_deslocada_mais_que_um_decimo_da_largura_fica() -> None:
    um = _linha("Conheça", 66.0, 156.0)
    outro = _linha("Conheça", 76.0, 166.0)
    assert _tirar(um, outro) == (["Conheça", "Conheça"], ())


def test_mesmo_texto_em_outro_tamanho_fica() -> None:
    um = _linha("Conheça também", 66.0, 235.0, tamanho=10.0)
    outro = _linha("Conheça também", 66.0, 235.0, tamanho=9.0)
    assert _tirar(um, outro) == (["Conheça também", "Conheça também"], ())


def test_mesmo_texto_em_outra_altura_fica() -> None:
    um = _linha("Conheça também", 66.0, 235.0)
    outro = _linha("Conheça também", 66.0, 235.0, topo=0.26)
    assert _tirar(um, outro) == (["Conheça também", "Conheça também"], ())


def test_texto_diferente_por_cima_fica() -> None:
    um = _linha("Conheça", 66.0, 156.0)
    outro = _linha("Contato", 66.0, 156.0)
    assert _tirar(um, outro) == (["Conheça", "Contato"], ())


def test_importar_pdf_le_o_negrito_feito_a_mao_uma_vez(tmp_path: Path) -> None:
    corpo = [
        LinhaDeTeste("Texto corrido do livro, longo como uma linha.", 72, 500 - n * 14)
        for n in range(6)
    ]
    pagina = [
        LinhaDeTeste("Conheça também", 66.0, 600.0, 24),
        LinhaDeTeste("Conheça também", 66.5, 600.3, 24),
        *corpo,
    ]
    pdf = montar_pdf(tmp_path / "livro.pdf", [pagina])
    importacao = importar_pdf(pdf, tmp_path / "livro.epub")
    textos = [bloco.texto for bloco in importacao.livro.blocos]
    assert (textos[0], [r.motivo for r in importacao.remocoes]) == (
        "Conheça também",
        [MOTIVO_DO_REPETIDO],
    )


def test_copia_do_texto_escondido_tem_um_registro_so() -> None:
    # R1 da code-review: o título escondido debaixo do quadro (22 pt sobre 8 pt, Dalgalarrondo
    # p. 275), desenhado duas vezes, saía duas vezes no registro, como escondido e como repetido.
    corpo = [
        _linha(f"Texto corrido do livro, linha {n}.", 66, 247, 10, 0.1 + n * 0.02) for n in range(8)
    ]
    quadro = _linha("transgressão ou violência. Apesar de manipulador,", 60.3, 403.7, 8, 0.686)
    um = _linha("A inteligência e", 57.4, 230.0, 22, 0.686)
    outro = _linha("A inteligência e", 57.9, 230.5, 22, 0.6865)
    remocoes = tirar_texto_escondido([Pagina(275, (*corpo, quadro, um, outro))]).remocoes
    assert [(r.motivo, r.texto) for r in remocoes] == [
        (MOTIVO_DO_ESCONDIDO, "A inteligência e"),
        (MOTIVO_DO_ESCONDIDO, "A inteligência e"),
    ]


def test_resumo_do_importar_pdf_diz_o_texto_repetido(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # R2 da code-review: o resumo conta as cópias junto com a borda e o texto escondido.
    corpo = [
        LinhaDeTeste("Texto corrido do livro, longo como uma linha.", 72, 500 - n * 14)
        for n in range(6)
    ]
    pagina = [
        LinhaDeTeste("Conheça também", 66.0, 600.0, 24),
        LinhaDeTeste("Conheça também", 66.5, 600.3, 24),
        *corpo,
    ]
    pdf = montar_pdf(tmp_path / "livro.pdf", [pagina])
    assert principal(["importar-pdf", str(pdf)]) == 0
    saida = capsys.readouterr().out
    assert "1 linhas tiradas da página: a borda, o texto escondido e o texto repetido." in saida
