# SPDX-License-Identifier: GPL-3.0-or-later
"""O sumário interno do PDF diz onde os capítulos abrem (ADR-0004, "Capítulos pelo sumário
interno do PDF").

No Manica, o nível 1 é a parte e o nível 2, o capítulo ("Capítulo 1. …"). No Miller, o capítulo
está nos níveis 1 e 2, na mesma página, e as seções vêm abaixo. No Practical os itens não trazem
o rótulo, e no Bonica o capítulo e a seção estão no mesmo nível.
"""

from __future__ import annotations

from earbook.dominio.sumario_interno import Abertura, ItemDoSumario, aberturas_de_capitulo


def _item(nivel: int, titulo: str, pagina: int) -> ItemDoSumario:
    return ItemDoSumario(nivel, titulo, pagina)


def test_parte_no_nivel_de_cima_e_capitulo_com_rotulo_abrem_capitulo() -> None:
    itens = [
        _item(1, "Capa", 1),
        _item(2, "Prefácio", 5),
        _item(1, "Parte I - História", 9),
        _item(2, "Capítulo 1. A história", 10),
        _item(2, "Capítulo 2. O ensino", 20),
        _item(2, "Caapítulo 3. A pesquisa", 30),
        _item(1, "Parte II - Gestão", 39),
        _item(2, "Capítulo 4. A gestão", 40),
        _item(1, "Anexo 1. Respostas", 50),
    ]
    assert aberturas_de_capitulo(itens) == tuple(
        Abertura(item.pagina, item.titulo) for item in itens
    )


def test_secao_abaixo_do_nivel_do_capitulo_nao_abre_capitulo() -> None:
    itens = [
        _item(1, "Prologo", 3),
        *[
            item
            for n in (1, 2, 3)
            for item in (
                _item(1, f"Capitulo {n}_ Ambito", 10 * n),
                _item(2, f"Capítulo {n} - Ámbito", 10 * n),
                _item(3, "Puntos clave", 10 * n),
                _item(3, "Bibliografía", 10 * n + 8),
            )
        ],
    ]
    assert aberturas_de_capitulo(itens) == (
        Abertura(3, "Prologo"),
        Abertura(10, "Capítulo 1 - Ámbito"),
        Abertura(20, "Capítulo 2 - Ámbito"),
        Abertura(30, "Capítulo 3 - Ámbito"),
    )


def test_sumario_sem_rotulo_de_capitulo_nao_serve() -> None:
    # Practical: "Part 1 General Considerations" e "1 History Is a Distillation of Rumor".
    itens = [
        _item(1, "Part 1 General Considerations", 23),
        *[_item(2, f"{n} Um capítulo sem rótulo", 20 + 10 * n) for n in range(1, 8)],
    ]
    assert aberturas_de_capitulo(itens) == ()


def test_sumario_plano_com_capitulo_e_secao_no_mesmo_nivel_nao_serve() -> None:
    # Bonica: 991 itens no nível 1, e só os 115 "CHAPTER N:" têm o rótulo.
    itens = [
        item
        for n in (1, 2, 3)
        for item in (
            _item(1, f"CHAPTER {n}: Pain", 10 * n),
            _item(1, "Definition of Terms", 10 * n + 1),
            _item(1, "Taxonomies", 10 * n + 2),
        )
    ]
    assert aberturas_de_capitulo(itens) == ()


def test_dois_rotulos_nao_bastam() -> None:
    itens = [_item(1, "Chapter 1 One", 5), _item(1, "Chapter 2 Two", 15)]
    assert aberturas_de_capitulo(itens) == ()


def test_tres_rotulos_na_mesma_pagina_nao_bastam() -> None:
    itens = [_item(1, f"Chapter {n} Same page", 5) for n in (1, 2, 3)]
    assert aberturas_de_capitulo(itens) == ()


def test_aberturas_saem_em_ordem_de_pagina_e_uma_por_pagina() -> None:
    itens = [
        _item(1, "Chapter 2: Two", 20),
        _item(1, "Chapter 1: One", 10),
        _item(1, "Chapter 3: Three", 30),
        _item(1, "Preface", 10),
    ]
    assert aberturas_de_capitulo(itens) == (
        Abertura(10, "Preface"),
        Abertura(20, "Chapter 2: Two"),
        Abertura(30, "Chapter 3: Three"),
    )


def test_palavra_que_so_comeca_como_o_rotulo_nao_e_rotulo() -> None:
    itens = [_item(1, f"Capitulos {n} a {n + 1} em resumo", 10 * n) for n in (1, 2, 3)]
    assert aberturas_de_capitulo(itens) == ()
