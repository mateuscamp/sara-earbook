# SPDX-License-Identifier: GPL-3.0-or-later
"""A figura sai com o diagrama inteiro, e o quadro depois da tabela e da figura fica (ADR-0004,
"Figura pelo diagrama e quadro depois da tabela").

No Practical, o quadro ("• Box 49.4", MyriadPro negrito, conteúdo em HelveticaNeueLTStd de 8,5
pt) vem na página logo depois de uma tabela, na mesma letra das células, e saía com ela; logo
depois de uma legenda, saía com a figura. A letra do painel ("A", "B"), em Helvetica de 10 pt, e o
valor do eixo, de 8,3 pt, são maiores que a legenda de 8 pt, e ficavam no meio da frase.
"""

from __future__ import annotations

import pytest

from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.tabelas_e_figuras import tirar_tabelas_e_figuras

CORPO = "AGaramondPro"
CELULA = "HelveticaNeueLTStd"
DIAGRAMA = "Helvetica"


def _linha(texto: str, topo: float, *, fonte: str = CORPO, tamanho: float = 10.0) -> Linha:
    return Linha(texto, x=42.0, fim=296.0, topo=topo, tamanho=tamanho, fonte=fonte)


def _corpo(topo: float, n: int = 12) -> list[Linha]:
    return [_linha(f"Texto corrido da linha {k} do livro.", topo + 0.014 * k) for k in range(n)]


def _quadro(topo: float) -> list[Linha]:
    return [
        _linha("• Box 49.4 Common Glucocorticoid Dosing Schedules", topo, fonte="MyriadPro"),
        _linha(
            "• Prednisone taper—prednisone, 10 mg tablets", topo + 0.02, fonte=CELULA, tamanho=8.5
        ),
        _linha("• Day one: two tablets before breakfast", topo + 0.04, fonte=CELULA, tamanho=8.5),
    ]


def _textos(paginas: tuple[Pagina, ...]) -> list[str]:
    return [linha.texto for pagina in paginas for linha in pagina.linhas]


def test_quadro_logo_depois_da_tabela_na_mesma_letra_fica() -> None:
    tabela = [
        _linha("TABLE", 0.075, fonte="Gotham", tamanho=8.5),
        _linha("49.11", 0.088, fonte="Gotham", tamanho=8.5),
        _linha("Commonly Prescribed Oral Glucocorticoids", 0.08, fonte="MyriadPro"),
        _linha("Methylprednisolone", 0.14, fonte=CELULA, tamanho=8.5),
        _linha("Medrol", 0.14, fonte=CELULA, tamanho=8.5),
    ]
    quadro = _quadro(0.35)
    limpas = tirar_tabelas_e_figuras([Pagina(1, (*tabela, *quadro, *_corpo(0.5)))])
    assert [linha.texto for linha in quadro] == _textos(limpas.paginas)[: len(quadro)]


def _legenda(topo: float, texto: str = "• Figure 20.5 The effect of upright radiographs") -> Linha:
    return _linha(texto, topo, fonte=CELULA, tamanho=8.0)


def test_quadro_logo_depois_da_legenda_fica() -> None:
    quadro = _quadro(0.42)
    figura = [_linha("Pain", 0.3, fonte=DIAGRAMA, tamanho=7.0), _legenda(0.36)]
    limpas = tirar_tabelas_e_figuras([Pagina(1, (*figura, *quadro, *_corpo(0.5)))])
    assert _textos(limpas.paginas)[: len(quadro)] == [linha.texto for linha in quadro]


@pytest.mark.parametrize("painel", ["A B", "c d c d", "I I II II III III"])
def test_letra_do_painel_maior_que_a_legenda_sai_com_a_figura(painel: str) -> None:
    corpo = _corpo(0.1)
    figura = [_linha(painel, 0.716, fonte=DIAGRAMA), _legenda(0.735, "• Figure 3.1 Organization")]
    limpas = tirar_tabelas_e_figuras([Pagina(1, (*corpo, *figura))])
    assert _textos(limpas.paginas) == [linha.texto for linha in corpo]


def test_valor_do_eixo_e_titulo_na_familia_do_diagrama_saem_com_a_figura() -> None:
    # Practical p. 126 e 132: o título do gráfico em Helvetica de 10 pt e o eixo de 8,3 pt, acima
    # dos anos de 7,6 pt e da legenda de 8 pt.
    corpo = _corpo(0.6)
    figura = [
        _linha("Pain Systems", 0.08, fonte=DIAGRAMA),
        _linha("120", 0.11, fonte=DIAGRAMA, tamanho=8.3),
        _linha("1993 1994 1995", 0.46, fonte=DIAGRAMA, tamanho=7.6),
        _legenda(0.51, "• Figure 7.3 Trends in the number of fellowships"),
    ]
    limpas = tirar_tabelas_e_figuras([Pagina(1, (*figura, *corpo))])
    assert _textos(limpas.paginas) == [linha.texto for linha in corpo]


def test_quadro_antes_do_diagrama_fica() -> None:
    # O diagrama em Helvetica não leva o quadro de HelveticaNeueLTStd de 8,5 pt logo acima.
    quadro = [
        _linha("• Box 43.7 Landmarks", 0.1, fonte="MyriadPro"),
        _linha("Locate the cricoid cartilage", 0.12, fonte=CELULA, tamanho=8.5),
    ]
    figura = [_linha("Th", 0.3, fonte=DIAGRAMA, tamanho=7.0), _legenda(0.36)]
    limpas = tirar_tabelas_e_figuras([Pagina(1, (*quadro, *figura, *_corpo(0.5)))])
    assert _textos(limpas.paginas)[:2] == [linha.texto for linha in quadro]


@pytest.mark.parametrize(
    "legenda",
    ["• Figure 3.1, cont\u2019d.", "• Figure 20.4, cont\u2019d Note (G) the typical appearance"],
)
def test_legenda_da_figura_continuada_sai_com_o_painel(legenda: str) -> None:
    corpo = _corpo(0.1)
    figura = [_linha("B", 0.716, fonte=DIAGRAMA), _legenda(0.735, legenda)]
    limpas = tirar_tabelas_e_figuras([Pagina(1, (*corpo, *figura))])
    assert _textos(limpas.paginas) == [linha.texto for linha in corpo]


def test_caixa_sem_rotulo_na_familia_do_diagrama_logo_acima_fica() -> None:
    # A família do diagrama leva o título e o eixo, que não fecham frase; o texto de 9 pt que
    # fecha a frase é de uma caixa, e fica (R3 da code-review de 2026-11-10, e a de 2026-11-17).
    caixa = [
        _linha("Locate the cricoid cartilage and", 0.1, fonte=DIAGRAMA, tamanho=9.0),
        _linha("insert the needle at the C6 level.", 0.12, fonte=DIAGRAMA, tamanho=9.0),
    ]
    figura = [_linha("Th", 0.3, fonte=DIAGRAMA, tamanho=7.0), _legenda(0.36)]
    limpas = tirar_tabelas_e_figuras([Pagina(1, (*caixa, *figura, *_corpo(0.5)))])
    assert _textos(limpas.paginas)[:2] == [linha.texto for linha in caixa]
