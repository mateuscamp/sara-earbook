# SPDX-License-Identifier: GPL-3.0-or-later
"""O texto escondido debaixo de outro sai antes dos blocos (ADR-0004, "O que ficou da Fase 1").

No Dalgalarrondo p. 275, debaixo do Quadro 22.4, há o "24" em 60 pt e "A inteligência e" / "suas
alterações" em 22 pt: o resto de uma abertura de capítulo antiga. Juntos às linhas do quadro na
mesma altura, o "24" virava título do tamanho do capítulo e abria um capítulo falso (`c026`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from earbook.comandos.importar_pdf import importar_pdf
from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.paginacao import LinhaRemovida
from earbook.dominio.texto_escondido import (
    MOTIVO_DO_ESCONDIDO,
    MOTIVO_DO_REPETIDO,
    tirar_texto_escondido,
)
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf


def _linha(texto: str, x: float, fim: float, tamanho: float = 8.0, topo: float = 0.686) -> Linha:
    return Linha(texto, x=x, fim=fim, topo=topo, tamanho=tamanho)


def _corpo(topo: float) -> Linha:
    """Uma linha comprida que firma o corpo do livro em 10 pt."""
    return _linha(
        "Texto corrido do livro, longo como uma linha inteira de corpo.", 66, 247, 10, topo
    )


def _tirar(*linhas: Linha) -> tuple[list[str], tuple[LinhaRemovida, ...]]:
    corpo = [_corpo(0.1 + n * 0.017) for n in range(5)]
    limpas = tirar_texto_escondido([Pagina(275, (*corpo, *linhas))])
    return [linha.texto for linha in limpas.paginas[0].linhas[5:]], limpas.remocoes


def test_titulo_debaixo_de_uma_linha_de_outro_tamanho_sai_registrado() -> None:
    quadro = _linha("transgressão ou violência. Apesar de manipulador,", 60.3, 403.7)
    escondido = _linha("24", 57.4, 109.3, tamanho=60)
    assert _tirar(quadro, escondido) == (
        ["transgressão ou violência. Apesar de manipulador,"],
        (LinhaRemovida(275, MOTIVO_DO_ESCONDIDO, "24"),),
    )


def test_texto_repetido_por_cima_do_mesmo_tamanho_nao_e_escondido() -> None:
    # Dalgalarrondo p. 2: "Conheça também", em 24 pt sobre 24 pt, é negrito feito com o texto
    # repetido por cima; Hard Parts p. 5, "Beijing" duas vezes. Não é texto escondido: uma cópia
    # fica, e a outra sai como repetida (ADR-0004, "Negrito feito à mão"). Até 2026-11-03, este
    # teste dizia que as duas ficavam; o Mateus aprovou tirar a cópia ("Aprovar").
    um = _linha("Conheça também", 66, 236, tamanho=24)
    outro = _linha("Conheça também", 66.5, 236.5, tamanho=24)
    assert _tirar(um, outro) == (
        ["Conheça também"],
        (LinhaRemovida(275, MOTIVO_DO_REPETIDO, "Conheça também"),),
    )


def test_titulo_ao_lado_de_outra_linha_sem_sobrepor_fica() -> None:
    texto = _linha("e a coluna da direita, na mesma altura.", 287, 446)
    titulo = _linha("Questões de revisão", 66, 247, tamanho=24)
    assert _tirar(texto, titulo) == (
        ["e a coluna da direita, na mesma altura.", "Questões de revisão"],
        (),
    )


def test_letra_miuda_sobreposta_abaixo_do_titulo_fica() -> None:
    # Hard Parts p. 462: lixo de 0,7 a 3,6 pt, uma letra por cima da outra, abaixo da letra de
    # título. Fica para as outras regras.
    um = _linha("5", 470, 474, tamanho=2.2)
    outro = _linha("7", 470, 474, tamanho=3.6)
    assert _tirar(um, outro) == (["5", "7"], ())


def test_importar_pdf_tira_o_numero_escondido_e_nao_abre_capitulo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # O pdfminer junta numa linha só o "24" e a linha do quadro do PDF montado em código; no
    # Dalgalarrondo, eles vêm em linhas separadas. As páginas entram já lidas, e o comando roda
    # inteiro sobre elas.
    corpo = [_corpo(0.3 + n * 0.017) for n in range(8)]
    paginas = [
        *(Pagina(n, (_linha(t, 66, 120, 60, 0.15), *corpo)) for n, t in enumerate("UDT", 1)),
        Pagina(
            4,
            (
                *corpo,
                _linha("transgressão ou violência.", 60.3, 403.7),
                _linha("24", 57.4, 109.3, 60),
            ),
        ),
    ]

    def ler_paginas(_: Path) -> tuple[Pagina, ...]:
        return tuple(paginas)

    monkeypatch.setattr("earbook.comandos.importar_pdf.ler_paginas", ler_paginas)
    pdf = montar_pdf(tmp_path / "livro.pdf", [[LinhaDeTeste("Livro.", 72, 700)]])
    importacao = importar_pdf(pdf, tmp_path / "livro.epub")
    assert (importacao.capitulos, [r.motivo for r in importacao.remocoes]) == (
        3,
        [MOTIVO_DO_ESCONDIDO],
    )
