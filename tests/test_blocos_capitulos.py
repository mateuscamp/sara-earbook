# SPDX-License-Identifier: GPL-3.0-or-later
"""Divisão em capítulos e nível dos títulos (ADR-0004)."""

from __future__ import annotations

from earbook.dominio.blocos import Bloco, TipoDeBloco
from earbook.dominio.capitulos import dividir_em_capitulos


def _titulo(texto: str, pagina: int, tamanho: float) -> Bloco:
    return Bloco(TipoDeBloco.TITULO, texto, pagina, tamanho)


def _paragrafo(texto: str, pagina: int) -> Bloco:
    return Bloco(TipoDeBloco.PARAGRAFO, texto, pagina, 10.5)


def test_capitulo_comeca_no_maior_titulo_que_aparece_em_tres_paginas() -> None:
    # Competente: o número do capítulo vem em 30 pt; a capa em 27 pt aparece uma vez só.
    blocos = [
        _titulo("Competente o Suficiente", 1, 27),
        _paragrafo("Prefácio.", 2),
        *[
            bloco
            for n in (1, 2, 3)
            for bloco in (
                _titulo(str(n), 10 * n, 30),
                _titulo(f"Capítulo {n}", 10 * n, 19),
                _paragrafo("Texto.", 10 * n),
            )
        ],
    ]
    capitulos = dividir_em_capitulos(blocos)
    assert [[b.texto for b in capitulo] for capitulo in capitulos] == [
        ["Competente o Suficiente", "Prefácio."],
        ["1", "Capítulo 1", "Texto."],
        ["2", "Capítulo 2", "Texto."],
        ["3", "Capítulo 3", "Texto."],
    ]


def test_nivel_do_titulo_vem_do_tamanho() -> None:
    blocos = [
        *[
            bloco
            for n in (1, 2, 3)
            for bloco in (
                _titulo(str(n), 10 * n, 30),
                _titulo("Seção", 10 * n, 19),
                _titulo("Sub", 10 * n, 15),
            )
        ],
        _titulo("Capa", 1, 40),
    ]
    niveis = {b.texto: b.nivel for capitulo in dividir_em_capitulos(blocos) for b in capitulo}
    assert niveis == {"1": 1, "2": 1, "3": 1, "Seção": 2, "Sub": 3, "Capa": 1}


def test_livro_sem_titulo_vira_um_capitulo_so() -> None:
    blocos = [_paragrafo("Um.", 1), _paragrafo("Dois.", 2)]
    assert [[b.texto for b in c] for c in dividir_em_capitulos(blocos)] == [["Um.", "Dois."]]
