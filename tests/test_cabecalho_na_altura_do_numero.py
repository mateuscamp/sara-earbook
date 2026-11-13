# SPDX-License-Identifier: GPL-3.0-or-later
"""O cabeçalho maior que o corpo sai pela altura do número de página, e o carimbo da gráfica,
pela forma (ADR-0004, "Tratado em português e em espanhol").

No Manica o cabeçalho vem em negrito de 10 pt, com o corpo de 9,3: o título do livro nas páginas
pares e o do capítulo nas ímpares, na linha do número de página. A regra da linha repetida só
olha a letra não maior que a do corpo.
"""

from __future__ import annotations

from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.paginacao import PaginasLimpas, tirar_cabecalhos_e_rodapes

ALTO = 0.064
PE = 0.96
CORPO = 9.3
CABECALHO = 10.0
MOTIVO = "cabeçalho de página na altura do número"


def _linha(texto: str, topo: float, tamanho: float = CORPO, x: float = 86.0) -> Linha:
    return Linha(texto, x=x, fim=320.0, topo=topo, tamanho=tamanho)


def _corpo(numero: int) -> list[Linha]:
    return [
        _linha(f"Texto corrido da linha {k} da página {numero} do livro.", 0.12 + 0.013 * k)
        for k in range(6)
    ]


def _limpar(*paginas: list[Linha]) -> PaginasLimpas:
    return tirar_cabecalhos_e_rodapes(
        [Pagina(n, tuple(linhas)) for n, linhas in enumerate(paginas, 1)]
    )


def _pagina(numero: int, cabecalho: str, topo_do_numero: float = ALTO) -> list[Linha]:
    """O número impresso é a página mais 20, no tamanho do cabeçalho."""
    return [
        _linha(str(numero + 20), topo_do_numero, CABECALHO, x=52.0),
        _linha(cabecalho, ALTO, CABECALHO),
        *_corpo(numero),
    ]


def _cabecalhos(limpas: PaginasLimpas) -> list[tuple[int, str, str]]:
    return [(r.pagina, r.motivo, r.texto) for r in limpas.remocoes if r.motivo == MOTIVO]


def test_cabecalho_maior_que_o_corpo_na_altura_do_numero_sai_sem_se_repetir() -> None:
    titulos = ["Anestesiologia", "A história da anestesia", "Anestesiologia", "O ensino"]
    limpas = _limpar(*[_pagina(n, titulo) for n, titulo in enumerate(titulos, 1)])
    assert _cabecalhos(limpas) == [(n, MOTIVO, titulo) for n, titulo in enumerate(titulos, 1)]
    assert [len(pagina.linhas) for pagina in limpas.paginas] == [6, 6, 6, 6]


def test_titulo_grande_no_alto_com_o_numero_no_pe_fica() -> None:
    titulos = ["Anestesiologia", "A história da anestesia", "Farmacologia"]
    limpas = _limpar(*[_pagina(n, titulo, PE) for n, titulo in enumerate(titulos, 1)])
    assert _cabecalhos(limpas) == []
    assert [pagina.linhas[0].texto for pagina in limpas.paginas] == titulos


def test_titulo_de_outro_tamanho_na_altura_do_numero_fica() -> None:
    paginas = [
        [
            _linha(str(n + 20), ALTO, CABECALHO, x=52.0),
            _linha(f"Capítulo de número {n}", ALTO, 14.0),
            *_corpo(n),
        ]
        for n in (1, 2, 3)
    ]
    assert _cabecalhos(_limpar(*paginas)) == []


def test_cabecalho_na_altura_do_numero_em_duas_paginas_fica() -> None:
    paginas = [
        _pagina(1, "Anestesiologia"),
        _pagina(2, "A história da anestesia"),
        [_linha("23", ALTO, CABECALHO, x=52.0), *_corpo(3)],
    ]
    assert _cabecalhos(_limpar(*paginas)) == []


def test_linha_do_corpo_na_altura_do_numero_do_pe_fica() -> None:
    ultimas = [
        "A última linha acaba aqui.",
        "Outra frase fecha a página.",
        "E mais uma, diferente.",
    ]
    paginas = [
        [*_corpo(n), _linha(ultima, PE), _linha(str(n + 20), PE, x=560.0)]
        for n, ultima in enumerate(ultimas, 1)
    ]
    limpas = _limpar(*paginas)
    assert [r.motivo for r in limpas.remocoes] == ["número de página"] * 3


def test_linha_sem_letra_na_altura_do_numero_fica() -> None:
    limpas = _limpar(*[_pagina(n, "* * *") for n in (1, 2, 3)])
    assert _cabecalhos(limpas) == []


def test_carimbo_de_data_e_hora_no_pe_sai_mesmo_mudando_a_cada_pagina() -> None:
    # Manica: "27/09/2017 20:12:36" no pé de cada página, em Helvetica de 6 pt.
    carimbos = ["27/09/2017 20:12:36", "27/09/2017 20:12:41", "04/11/2017 17:16:14"]
    limpas = _limpar(
        *[[*_corpo(n), _linha(carimbo, 0.987, 6.0)] for n, carimbo in enumerate(carimbos, 1)]
    )
    assert [(r.motivo, r.texto) for r in limpas.remocoes] == [
        ("rodapé de página repetido", carimbo) for carimbo in carimbos
    ]


def test_data_sem_hora_que_muda_a_cada_pagina_fica() -> None:
    datas = ["27/09/2017", "28/09/2017", "04/11/2017"]
    limpas = _limpar(*[[*_corpo(n), _linha(data, 0.987, 6.0)] for n, data in enumerate(datas, 1)])
    assert limpas.remocoes == ()
