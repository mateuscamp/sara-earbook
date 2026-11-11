# SPDX-License-Identifier: GPL-3.0-or-later
"""Divisão em capítulos e nível dos títulos (ADR-0004)."""

from __future__ import annotations

from earbook.dominio.blocos import Bloco
from earbook.dominio.capitulos import dividir_em_capitulos
from earbook.dominio.tipo_da_linha import TipoDeBloco


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


def test_rotulo_de_capitulo_no_tamanho_da_secao_abre_capitulo() -> None:
    # Bonica: a parte vem em 30 pt, em 6 das 6.053 páginas, e o "CHAPTER 1" com o título, em
    # 21 pt, o tamanho da seção. O livro saía com 7 capítulos, um por parte.
    blocos = [
        _titulo("Basic Considerations", 10, 30),
        _titulo("CHAPTER 1 Intellectual Milestones", 10, 21),
        _paragrafo("Texto.", 10),
        _titulo("Mechanistic Views of Pain", 11, 21),
        _paragrafo("Texto.", 11),
        _titulo("CHAPTER 2 Pain Terms", 20, 21),
        _paragrafo("Texto.", 20),
        _titulo("Pain Conditions", 30, 30),
        _titulo("NEUROPATHIC PAIN CONDITIONS CHAPTER 3 Painful Neuropathies", 30, 21),
        _paragrafo("Texto.", 30),
        _titulo("Methods for Symptomatic Control", 40, 30),
        _paragrafo("Texto.", 40),
    ]
    capitulos = dividir_em_capitulos(blocos)
    assert [[b.texto for b in capitulo] for capitulo in capitulos] == [
        [
            "Basic Considerations",
            "CHAPTER 1 Intellectual Milestones",
            "Texto.",
            "Mechanistic Views of Pain",
            "Texto.",
        ],
        ["CHAPTER 2 Pain Terms", "Texto."],
        ["Pain Conditions", "NEUROPATHIC PAIN CONDITIONS CHAPTER 3 Painful Neuropathies", "Texto."],
        ["Methods for Symptomatic Control", "Texto."],
    ]


def test_rotulo_menor_que_o_titulo_vai_com_o_capitulo_que_abre() -> None:
    # Hard Parts: o "CHAPTER 2" em letra pequena vem antes do título de 25,2 pt e ficava no fim
    # do capítulo anterior.
    blocos = [
        *[
            bloco
            for n in (1, 2, 3)
            for bloco in (
                _titulo(f"CHAPTER {n}", 10 * n, 12),
                _titulo(f"Título {n}", 10 * n, 25.2),
                _paragrafo("Texto.", 10 * n),
            )
        ],
    ]
    capitulos = dividir_em_capitulos(blocos)
    assert [[b.texto for b in capitulo] for capitulo in capitulos] == [
        ["CHAPTER 1", "Título 1", "Texto."],
        ["CHAPTER 2", "Título 2", "Texto."],
        ["CHAPTER 3", "Título 3", "Texto."],
    ]


def test_titulo_que_so_cita_capitulo_e_linha_do_sumario_nao_abrem_capitulo() -> None:
    # Practical: "Radiofrequency Denervation (see also Chapter 66…)"; Bonica, o sumário do fim:
    # "CHAPTER 6: Supraspinal Mechanisms of Pain and 377".
    blocos = [
        bloco
        for n in (1, 2, 3)
        for bloco in (
            _titulo(f"Parte {n}", 10 * n, 30),
            _paragrafo("Texto.", 10 * n),
            _titulo(f"Denervation (see also Chapter {n} Radiofrequency)", 10 * n + 1, 12),
            _paragrafo("Texto.", 10 * n + 1),
            _titulo(f"CHAPTER {n}: Supraspinal Mechanisms 377", 10 * n + 2, 12),
            _paragrafo("Texto.", 10 * n + 2),
        )
    ]
    capitulos = dividir_em_capitulos(blocos)
    assert [capitulo[0].texto for capitulo in capitulos] == ["Parte 1", "Parte 2", "Parte 3"]
