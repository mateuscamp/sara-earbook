# SPDX-License-Identifier: GPL-3.0-or-later
"""A borda do tratado em duas colunas: o rótulo da tabela fica, e o cabeçalho do capítulo sai
(ADR-0004, "Rótulo e cabeçalho do capítulo na borda").

No Practical, o rótulo "TABLE" abre a tabela no alto da página, a 7,5% da altura, dentro da faixa
da borda, e se repete em 137 páginas: saía como cabeçalho, e a tabela sem rótulo ficava no texto.
O cabeçalho "CHAPTER 2 Classification of…" vem só nas páginas ímpares, e o capítulo curto o tem
em duas páginas alternadas: ficava, colado ao parágrafo.
"""

from __future__ import annotations

import pytest

from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.paginacao import PaginasLimpas, tirar_cabecalhos_e_rodapes

ALTO = 0.023
PE = 0.959
ROTULO = 0.075
MEIO = 0.5


def _linha(texto: str, topo: float = MEIO, tamanho: float = 10.0) -> Linha:
    return Linha(texto, x=54, fim=540, topo=topo, tamanho=tamanho)


def _corpo(numero: int) -> Linha:
    return _linha(f"Texto corrido da página {numero}, longo como uma linha do livro.")


def _limpar(*paginas: list[Linha]) -> PaginasLimpas:
    return tirar_cabecalhos_e_rodapes(
        [Pagina(n, tuple(linhas)) for n, linhas in enumerate(paginas, 1)]
    )


def _textos(limpas: PaginasLimpas) -> list[list[str]]:
    return [[linha.texto for linha in pagina.linhas] for pagina in limpas.paginas]


@pytest.mark.parametrize("rotulo", ["TABLE", "• BOX 9.1", "• Box 20.2"])
def test_rotulo_de_tabela_ou_de_quadro_no_alto_de_tres_paginas_fica(rotulo: str) -> None:
    paginas = [[_linha(rotulo, ROTULO, 8.5), _corpo(n)] for n in (1, 2, 3)]
    assert [linha[0] for linha in _textos(_limpar(*paginas))] == [rotulo] * 3


def test_cabecalho_com_o_rotulo_do_capitulo_sai_mesmo_em_duas_paginas_alternadas() -> None:
    # Cada capítulo curto tem o seu cabeçalho em duas páginas ímpares; juntos, pelo rótulo
    # "CHAPTER N", eles se repetem no mesmo topo do livro inteiro.
    dois = _linha("CHAPTER 2 Classification of Acute Pain", ALTO, 9)
    tres = _linha("CHAPTER 3 Organizing an Inpatient Acute Pain Service", ALTO, 9)
    paginas = [[dois, _corpo(1)], [_corpo(2)], [dois, _corpo(3)], [tres, _corpo(4)], [_corpo(5)]]
    paginas.append([tres, _corpo(6)])
    assert all(len(textos) == 1 for textos in _textos(_limpar(*paginas)))


def test_titulo_do_capitulo_em_letra_grande_no_alto_fica() -> None:
    # A abertura do capítulo, maior que o corpo, não é cabeçalho, mesmo com o rótulo.
    titulos = [_linha(f"CHAPTER {n} Um título", ALTO, 18) for n in (1, 2, 3)]
    paginas = [[titulo, _corpo(n)] for n, titulo in enumerate(titulos)]
    assert [textos[0] for textos in _textos(_limpar(*paginas))] == [
        titulo.texto for titulo in titulos
    ]


def test_numero_entre_os_das_paginas_vizinhas_sai_quando_a_paginacao_pula_uma_pagina() -> None:
    # Practical, p. 17 a 19 do PDF: "xvii", "xix", "xxi". O "xix" não tem a sequência dele (a
    # página xviii não está no PDF), mas fica entre os números das vizinhas.
    romanos = ["xv", "xvi", "xvii", "xix", "xxi", "xxii", "xxiii"]
    paginas = [[_corpo(n), _linha(romano, PE, 9)] for n, romano in enumerate(romanos)]
    assert all(len(textos) == 1 for textos in _textos(_limpar(*paginas)))


def test_numero_fora_da_ordem_das_paginas_vizinhas_fica() -> None:
    romanos = ["xv", "xvi", "xvii", "xl", "xxi", "xxii", "xxiii"]
    paginas = [[_corpo(n), _linha(romano, PE, 9)] for n, romano in enumerate(romanos)]
    assert _textos(_limpar(*paginas))[3] == [_corpo(3).texto, "xl"]


def test_primeira_linha_da_coluna_que_abre_com_o_rotulo_do_capitulo_fica() -> None:
    # A prosa do Practical começa a 7% da altura, dentro da faixa da borda. A linha do corpo que
    # abre com "Chapter 20" em três páginas não é cabeçalho: ela está na mancha do corpo, e o
    # cabeçalho fica acima dela (code-review).
    frases = {
        1: "Chapter 21 describes the treatment of this pain at length.",
        2: "Chapter 22 covers the opioids and their side effects.",
        3: "Chapter 23 reviews the evidence for interventional care.",
    }

    def pagina(n: int) -> list[Linha]:
        primeira = _linha(frases[n], 0.07)
        resto = [
            _linha(f"Texto corrido da página {n}, longo como uma linha.", 0.084 + 0.014 * k)
            for k in range(20)
        ]
        return [primeira, *resto]

    textos = _textos(_limpar(*[pagina(n) for n in (1, 2, 3)]))
    assert [pagina[0] for pagina in textos] == list(frases.values())
