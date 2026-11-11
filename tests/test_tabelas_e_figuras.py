# SPDX-License-Identifier: GPL-3.0-or-later
"""A tabela e a figura saem do áudio pela letra (ADR-0004, "Tabela e figura pela letra").

No Practical, o corpo é AGaramondPro de 10 pt; o rótulo "TABLE" vem em Gotham-Bold, o número numa
linha à parte, o título em MyriadPro-Bold e as células em HelveticaNeueLTStd-Cn de 8,5 pt, lidas
coluna a coluna. A figura traz os rótulos do diagrama em Helvetica de 7 pt e a legenda
"• Figure 2.1 …" em HelveticaNeueLTStd-Lt de 8 pt. No Bonica, a tabela abre num título "TABLE 1.1
…" e segue em letra de nota, e a legenda é "FIGURE 1.1 …".
"""

from __future__ import annotations

from pathlib import Path

import pytest

from earbook.comandos.cli import principal
from earbook.comandos.importar_pdf import importar_pdf
from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.tabelas_e_figuras import (
    MOTIVO_DA_FIGURA,
    MOTIVO_DA_TABELA,
    tirar_tabelas_e_figuras,
)
from tests.pdf_de_teste import LinhaDeTeste, montar_pdf

CORPO = "AGaramondPro"


def _linha(texto: str, topo: float, *, fonte: str = CORPO, tamanho: float = 10.0) -> Linha:
    return Linha(texto, x=42.0, fim=296.0, topo=topo, tamanho=tamanho, fonte=fonte)


def _corpo(topo: float, n: int = 12) -> list[Linha]:
    return [_linha(f"Texto corrido da linha {k} do livro.", topo + 0.014 * k) for k in range(n)]


def _tabela(topo: float) -> list[Linha]:
    return [
        _linha("TABLE", topo, fonte="Gotham", tamanho=8.5),
        _linha("2.1", topo + 0.012, fonte="Gotham", tamanho=8.5),
        _linha("Pain Axes", topo + 0.005, fonte="MyriadPro"),
        _linha("Axis I", topo + 0.03, fonte="HelveticaNeueLTStd", tamanho=8.5),
        _linha("Regions", topo + 0.03, fonte="HelveticaNeueLTStd", tamanho=8.5),
    ]


def _textos(paginas: tuple[Pagina, ...]) -> list[str]:
    return [linha.texto for pagina in paginas for linha in pagina.linhas]


def test_tabela_sai_inteira_do_rotulo_ate_a_letra_do_corpo() -> None:
    antes, depois = _corpo(0.1), _corpo(0.9, 2)
    limpas = tirar_tabelas_e_figuras([Pagina(1, (*antes, *_tabela(0.8), *depois))])
    assert _textos(limpas.paginas) == [linha.texto for linha in (*antes, *depois)]
    assert [(r.pagina, r.motivo, r.texto) for r in limpas.remocoes] == [
        (1, MOTIVO_DA_TABELA, texto) for texto in ("TABLE", "2.1", "Pain Axes", "Axis I", "Regions")
    ]


def test_figura_sai_com_os_rotulos_do_diagrama_e_a_legenda() -> None:
    figura = [
        _linha("Chronic pain", 0.05, fonte="Helvetica", tamanho=7.0),
        _linha("Chronic primary", 0.08, fonte="Helvetica", tamanho=7.0),
        _linha(
            "• Figure 2.1 International Classification of", 0.1, fonte="HelveticaNeue", tamanho=8
        ),
        _linha("Diseases chronic pain terms.", 0.11, fonte="HelveticaNeue", tamanho=8),
    ]
    corpo = _corpo(0.2)
    limpas = tirar_tabelas_e_figuras([Pagina(1, (*figura, *corpo))])
    assert _textos(limpas.paginas) == [linha.texto for linha in corpo]
    assert {r.motivo for r in limpas.remocoes} == {MOTIVO_DA_FIGURA}


def test_legenda_do_bonica_em_letra_do_corpo_menor_sai() -> None:
    legenda = _linha("FIGURE 1.1 Thomas Sydenham. (Courtesy of the", 0.5, tamanho=8.0)
    corpo = _corpo(0.1)
    limpas = tirar_tabelas_e_figuras([Pagina(1, (*corpo, legenda))])
    assert _textos(limpas.paginas) == [linha.texto for linha in corpo]


def test_tabela_que_abre_em_titulo_sai_com_as_celulas() -> None:
    # Bonica: "TABLE 1.1 Relationships in Antiquity…" em letra de título, células em nota.
    rotulo = _linha("TABLE 1.1 Relationships in Antiquity", 0.5, fonte="Frutiger", tamanho=12)
    celulas = [_linha("Black bile Blood Phlegm", 0.52, tamanho=8.0)]
    corpo, depois = _corpo(0.1), _corpo(0.6, 2)
    limpas = tirar_tabelas_e_figuras([Pagina(1, (*corpo, rotulo, *celulas, *depois))])
    assert _textos(limpas.paginas) == [linha.texto for linha in (*corpo, *depois)]


def test_tabela_continua_na_pagina_seguinte_ate_a_letra_do_corpo() -> None:
    continuacao = [_linha("Axis V", 0.08, fonte="HelveticaNeueLTStd", tamanho=8.5)]
    pagina_1 = Pagina(1, (*_corpo(0.1), *_tabela(0.8)))
    pagina_2 = Pagina(2, (*continuacao, *_corpo(0.2)))
    limpas = tirar_tabelas_e_figuras([pagina_1, pagina_2])
    assert "Axis V" not in _textos(limpas.paginas)
    assert len(_textos(limpas.paginas)) == 24


def test_titulo_de_secao_fecha_a_tabela() -> None:
    titulo = _linha("Acute Pain", 0.9, fonte="MyriadPro", tamanho=13.0)
    limpas = tirar_tabelas_e_figuras([Pagina(1, (*_corpo(0.1), *_tabela(0.8), titulo))])
    assert "Acute Pain" in _textos(limpas.paginas)


def test_caixa_em_outra_letra_sem_rotulo_fica() -> None:
    caixa = [
        _linha("Key Points", 0.8, fonte="MyriadPro"),
        _linha("• Chronic pain is common.", 0.82, fonte="MyriadPro", tamanho=9.0),
    ]
    paginas = [Pagina(1, (*_corpo(0.1), *caixa, *_corpo(0.9, 2)))]
    assert tirar_tabelas_e_figuras(paginas).remocoes == ()


def test_mencao_a_tabela_na_letra_do_corpo_fica() -> None:
    mencao = _linha("Table 2.1 shows the axes, and the first", 0.5)
    paginas = [Pagina(1, (*_corpo(0.1), mencao, *_corpo(0.6, 2)))]
    assert tirar_tabelas_e_figuras(paginas).remocoes == ()


def test_rotulo_em_portugues_fica() -> None:
    # O quadro do Dalgalarrondo fica no lugar (ADR-0004, "Quadro no lugar"), e o Competente, com
    # as legendas "Figura N.N", não está neste Mac para medir.
    rotulo = _linha("Tabela 19.1 Sintomas", 0.5, fonte="Frutiger", tamanho=12)
    celulas = [_linha("Delírio Alucinação", 0.52, tamanho=8.0)]
    paginas = [Pagina(1, (*_corpo(0.1), rotulo, *celulas, *_corpo(0.6, 2)))]
    assert tirar_tabelas_e_figuras(paginas).remocoes == ()


def test_livro_sem_familia_de_letra_nao_muda() -> None:
    # O EPUB de teste e o PDF cujo nome de fonte não é texto não trazem a família.
    linhas = [
        Linha(linha.texto, x=42.0, fim=296.0, topo=linha.topo, tamanho=8.5)
        for linha in _tabela(0.8)
    ]
    paginas = [
        Pagina(
            1,
            (
                *[Linha(f"Corpo {k}.", 42.0, 296.0, 0.1 + 0.01 * k, 10.0) for k in range(12)],
                *linhas,
            ),
        )
    ]
    assert tirar_tabelas_e_figuras(paginas).remocoes == ()


def test_mencao_quebrada_na_linha_de_um_quadro_em_outra_letra_fica() -> None:
    # Hard Parts p. 125 e 144: a "Sysops Squad Saga" vem em MyriadPro de 9 pt, e a menção à
    # tabela e à figura cai no começo da linha, continuando a frase da linha de cima.
    saga = [
        _linha("Addison highlighted these components in", 0.5, fonte="MyriadPro", tamanho=9.0),
        _linha("Figure 5-11.", 0.51, fonte="MyriadPro", tamanho=9.0),
        _linha(
            "create a single story and listed the changes in", 0.52, fonte="MyriadPro", tamanho=9
        ),
        _linha("Table 5-18. Addison also decided to rename", 0.53, fonte="MyriadPro", tamanho=9),
    ]
    paginas = [Pagina(1, (*_corpo(0.1), *saga, *_corpo(0.6, 2)))]
    assert tirar_tabelas_e_figuras(paginas).remocoes == ()


def test_importar_pdf_tira_a_tabela_e_o_resumo_a_conta(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpo = [
        LinhaDeTeste(f"Linha {n} do texto corrido do livro.", 72, 700 - 14 * n, serifa=True)
        for n in range(12)
    ]
    tabela = [
        LinhaDeTeste("TABLE", 72, 500, tamanho=8.5, negrito=True),
        LinhaDeTeste("2.1", 72, 490, tamanho=8.5, negrito=True),
        LinhaDeTeste("Axis I Regions", 72, 478, tamanho=8.5),
    ]
    pdf = montar_pdf(tmp_path / "livro.pdf", [[*corpo, *tabela]])
    importacao = importar_pdf(pdf, tmp_path / "livro.epub")
    assert [(r.motivo, r.texto) for r in importacao.remocoes] == [
        (MOTIVO_DA_TABELA, texto) for texto in ("TABLE", "2.1", "Axis I Regions")
    ]
    assert principal(["importar-pdf", str(pdf), "--epub", str(tmp_path / "outro.epub")]) == 0
    saida = capsys.readouterr().out
    assert "0 linhas tiradas da página: a borda, o texto escondido e o texto repetido." in saida
    assert "3 linhas de tabela, figura e página de lista tiradas." in saida


def test_credito_do_autor_na_pagina_seguinte_nao_continua_a_tabela() -> None:
    # R2 da code-review: a tabela que vira a página só continua na letra das células dela.
    credito = _linha("NATALIE MORYL, CHARLES INTURRISI", 0.05, fonte="Gotham", tamanho=10.0)
    pagina_1 = Pagina(1, (*_corpo(0.1), *_tabela(0.8)))
    pagina_2 = Pagina(2, (credito, *_corpo(0.2)))
    limpas = tirar_tabelas_e_figuras([pagina_1, pagina_2])
    assert "NATALIE MORYL, CHARLES INTURRISI" in _textos(limpas.paginas)


def test_caixa_antes_do_diagrama_na_mesma_pagina_fica() -> None:
    # R3 da code-review: antes da legenda, só sai a letra do diagrama, não maior que a dela.
    caixa = _linha("• Chronic pain is common.", 0.03, fonte="MyriadPro", tamanho=9.0)
    figura = [
        _linha("Chronic pain", 0.05, fonte="Helvetica", tamanho=7.0),
        _linha("• Figure 2.1 International Classification", 0.1, fonte="HelveticaNeue", tamanho=8),
    ]
    limpas = tirar_tabelas_e_figuras([Pagina(1, (caixa, *figura, *_corpo(0.2)))])
    assert "• Chronic pain is common." in _textos(limpas.paginas)
