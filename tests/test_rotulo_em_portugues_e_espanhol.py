# SPDX-License-Identifier: GPL-3.0-or-later
"""A tabela, o quadro e a figura saem também pelo rótulo em português e em espanhol (ADR-0004,
"Tratado em português e em espanhol").

No Manica, o corpo é Times New Roman de 9,3 pt; a legenda ("FigurA 1.2 …", com a caixa trocada
pelo versalete) vem em MyriadPro de 9 pt, e o rótulo do quadro e da tabela, em MyriadPro de 10
pt, com as células em 9,7. No Miller, o corpo é StoneSerif de 9 pt; a figura e a tabela vêm em
StoneSans, e o título do quadro ("CUADRO 4-1 …"), em StoneSerif negrito de 9,5 pt.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from earbook.dominio.pagina import Linha, Pagina
from earbook.dominio.tabelas_e_figuras import (
    MOTIVO_DA_FIGURA,
    MOTIVO_DA_TABELA,
    tirar_tabelas_e_figuras,
)

CORPO = "TimesNewRomanPSMT"
SERIFA = "StoneSerif"


def _linha(
    texto: str,
    topo: float,
    *,
    fonte: str = CORPO,
    tamanho: float = 9.3,
    negrito: bool = False,
) -> Linha:
    return Linha(texto, x=86.0, fim=320.0, topo=topo, tamanho=tamanho, fonte=fonte, negrito=negrito)


def _corpo(topo: float, n: int = 12, fonte: str = CORPO, tamanho: float = 9.3) -> list[Linha]:
    return [
        _linha(
            f"Texto corrido da linha {k} do livro.", topo + 0.013 * k, fonte=fonte, tamanho=tamanho
        )
        for k in range(n)
    ]


def _motivos(linhas: list[Linha]) -> list[tuple[str, str]]:
    limpas = tirar_tabelas_e_figuras([Pagina(1, tuple(linhas))])
    return [(r.motivo, r.texto) for r in limpas.remocoes]


def test_legenda_com_rotulo_em_portugues_e_caixa_trocada_sai() -> None:
    legenda = [
        _linha("FigurA 1.2 Papoula.", 0.5, fonte="MyriadPro", tamanho=9.0),
        _linha("Fonte: Banco de imagens.", 0.513, fonte="MyriadPro", tamanho=9.0),
    ]
    assert _motivos([*_corpo(0.1), *legenda, *_corpo(0.6, 2)]) == [
        (MOTIVO_DA_FIGURA, "FigurA 1.2 Papoula."),
        (MOTIVO_DA_FIGURA, "Fonte: Banco de imagens."),
    ]


@pytest.mark.parametrize(
    "rotulo", ["QuAdro 1.1 nomes e fatos", "tAbelA 8.1 Parâmetros vitais", "Quadro 2.7.1 Sinopse"]
)
def test_quadro_e_tabela_com_rotulo_em_portugues_saem_com_as_celulas(rotulo: str) -> None:
    quadro = [
        _linha(rotulo, 0.5, fonte="MyriadPro", tamanho=10.0),
        _linha("Espécie", 0.515, fonte="MyriadPro", tamanho=9.7),
        _linha("Coelho", 0.53, fonte="MyriadPro", tamanho=9.7),
    ]
    assert _motivos([*_corpo(0.1), *quadro, *_corpo(0.6, 2)]) == [
        (MOTIVO_DA_TABELA, rotulo),
        (MOTIVO_DA_TABELA, "Espécie"),
        (MOTIVO_DA_TABELA, "Coelho"),
    ]


def test_tabla_e_figura_com_rotulo_em_espanhol_saem() -> None:
    tabla = [
        _linha("TABLA 2-1 PERSONAL Y ÁMBITO", 0.4, fonte="StoneSans", tamanho=9.0),
        _linha("Indonesia", 0.415, fonte="StoneSans", tamanho=8.0),
    ]
    figura = [_linha("Figura 1-1. Ámbito cambiante.", 0.7, fonte="StoneSans", tamanho=8.0)]
    corpo = _corpo(0.1, fonte=SERIFA, tamanho=9.0)
    meio = _corpo(0.5, 2, fonte=SERIFA, tamanho=9.0)
    assert _motivos([*corpo, *tabla, *meio, *figura]) == [
        (MOTIVO_DA_TABELA, "TABLA 2-1 PERSONAL Y ÁMBITO"),
        (MOTIVO_DA_TABELA, "Indonesia"),
        (MOTIVO_DA_FIGURA, "Figura 1-1. Ámbito cambiante."),
    ]


def test_cuadro_com_titulo_em_negrito_na_letra_do_corpo_sai_com_o_conteudo() -> None:
    cuadro = [
        _linha(
            "CUADRO 4-1 Características del director", 0.5, fonte=SERIFA, tamanho=9.5, negrito=True
        ),
        _linha("médico de quirófano", 0.514, fonte=SERIFA, tamanho=9.5, negrito=True),
        _linha("• Persona con experiencia", 0.53, fonte="StoneSans", tamanho=8.0),
        _linha("• Respetado por su equipo", 0.543, fonte="StoneSans", tamanho=8.0),
    ]
    antes = [
        *_corpo(0.1, 11, fonte=SERIFA, tamanho=9.0),
        _linha("la frase del cuerpo sigue en la", 0.3, fonte=SERIFA, tamanho=9.0),
    ]
    depois = _corpo(0.6, 2, fonte=SERIFA, tamanho=9.0)
    assert _motivos([*antes, *cuadro, *depois]) == [
        (MOTIVO_DA_TABELA, linha.texto) for linha in cuadro
    ]


def test_subtitulo_em_negrito_na_letra_do_corpo_depois_do_quadro_fica() -> None:
    quadro = [
        _linha("Quadro 4.1 Critérios", 0.5, fonte="MyriadPro", tamanho=10.0),
        _linha("Idade", 0.515, fonte="MyriadPro", tamanho=9.7),
    ]
    subtitulo = _linha("Farmacologia clínica", 0.55, negrito=True)
    linhas = [*_corpo(0.1), *quadro, subtitulo, *_corpo(0.6, 2)]
    assert [texto for _, texto in _motivos(linhas)] == ["Quadro 4.1 Critérios", "Idade"]


def test_rotulo_em_letra_de_titulo_e_o_quadro_que_fica_no_lugar() -> None:
    # Dalgalarrondo: "Quadro 5.1" em 12 pt, com o corpo de 10, e o conteúdo em 8 e 9 pt
    # (ADR-0004, "Quadro no lugar").
    quadro = [
        _linha("Quadro 5.1 Funções psíquicas", 0.5, fonte="Frutiger", tamanho=12.0),
        _linha("Consciência e atenção", 0.52, fonte="Frutiger", tamanho=9.0),
    ]
    assert _motivos([*_corpo(0.1, tamanho=10.0), *quadro, *_corpo(0.6, 2, tamanho=10.0)]) == []


@pytest.mark.parametrize(
    "mencao",
    ["Quadro 2.7.1, relacionam-se os principais", "tabla 7-4, junto con los medicamentos"],
)
def test_mencao_na_letra_do_corpo_fica(mencao: str) -> None:
    assert _motivos([*_corpo(0.1), _linha(mencao, 0.5), *_corpo(0.6, 2)]) == []


def test_mencao_que_continua_a_frase_em_outra_letra_fica() -> None:
    caixa = [
        _linha("Os valores de referência estão na", 0.5, fonte="MyriadPro", tamanho=9.0),
        _linha("Tabela 5.2 e mudam com a idade.", 0.513, fonte="MyriadPro", tamanho=9.0),
    ]
    assert _motivos([*_corpo(0.1), *caixa, *_corpo(0.6, 2)]) == []


def test_rotulo_com_numero_simples_fica() -> None:
    caixa = [_linha("Figura 3 Esquema do aparelho.", 0.5, fonte="MyriadPro", tamanho=9.0)]
    assert _motivos([*_corpo(0.1), *caixa, *_corpo(0.6, 2)]) == []


def test_rotulo_em_ingles_em_negrito_na_letra_do_corpo_fica() -> None:
    tabela = [
        _linha("Table 2.1 Pain Axes", 0.5, negrito=True),
        _linha("Axis I", 0.515, fonte="HelveticaNeueLTStd", tamanho=8.5),
    ]
    assert _motivos([*_corpo(0.1), *tabela, *_corpo(0.6, 2)]) == []


def test_rotulo_em_negrito_depois_de_linha_sem_ponto_na_mesma_letra_e_rotulo() -> None:
    # Manica: "FigurA 1.9", em negrito, embaixo do rótulo solto do diagrama, na mesma letra.
    figura = [
        _linha("Glicogênio", 0.5, fonte="MyriadPro", tamanho=9.0),
        _linha("FigurA 1.9", 0.513, fonte="MyriadPro", tamanho=9.0, negrito=True),
    ]
    assert [motivo for motivo, _ in _motivos([*_corpo(0.1), *figura, *_corpo(0.6, 2)])] == [
        MOTIVO_DA_FIGURA,
        MOTIVO_DA_FIGURA,
    ]


def test_livro_de_corpo_em_negrito_nao_perde_a_prosa_depois_da_mencao() -> None:
    # Achado da code-review: no livro de corpo em negrito, a menção no começo da linha abria um
    # "título" que não acabava mais, e a prosa saía com a caixa seguinte.
    corpo = [replace(linha, negrito=True) for linha in _corpo(0.1)]
    mencao = _linha("Tabela 3.2 resume os achados do estudo.", 0.3, negrito=True)
    depois = [replace(linha, negrito=True) for linha in _corpo(0.32, 8)]
    caixa = _linha("Pontos de atenção", 0.6, fonte="MyriadPro", tamanho=9.0)
    assert _motivos([*corpo, mencao, *depois, caixa]) == []


def test_titulo_do_rotulo_em_negrito_tem_no_maximo_seis_linhas() -> None:
    # Miller: o título do "CUADRO" tem de 1 a 5 linhas. O parágrafo de destaque em negrito que
    # começa por uma menção não sai inteiro.
    negrito = [
        _linha(texto, 0.4 + 0.013 * n, fonte=SERIFA, tamanho=9.5, negrito=True)
        for n, texto in enumerate(
            ["CUADRO 4-1 Lista", *[f"linha {k} do destaque" for k in range(7)]]
        )
    ]
    corpo = _corpo(0.1, fonte=SERIFA, tamanho=9.0)
    depois = _corpo(0.6, 2, fonte=SERIFA, tamanho=9.0)
    assert _motivos([*corpo, *negrito, *depois]) == [
        (MOTIVO_DA_TABELA, linha.texto) for linha in negrito[:6]
    ]


def test_titulo_do_rotulo_em_negrito_nao_passa_para_a_pagina_seguinte() -> None:
    rotulo = _linha("CUADRO 4-1 Lista", 0.9, fonte=SERIFA, tamanho=9.5, negrito=True)
    subtitulo = _linha("Farmacología clínica", 0.1, fonte=SERIFA, tamanho=9.5, negrito=True)
    paginas = [
        Pagina(1, (*_corpo(0.1, fonte=SERIFA, tamanho=9.0), rotulo)),
        Pagina(2, (subtitulo, *_corpo(0.2, 4, fonte=SERIFA, tamanho=9.0))),
    ]
    limpas = tirar_tabelas_e_figuras(paginas)
    assert [(r.pagina, r.texto) for r in limpas.remocoes] == [(1, "CUADRO 4-1 Lista")]
