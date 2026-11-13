# SPDX-License-Identifier: GPL-3.0-or-later
"""A referência com a citação "volume:página, ano" sai do texto lido, registrada (ADR-0008,
"Tratado em português e em espanhol", decisão 1).

O Miller traz a bibliografia assim: "1. Bedford PD: Lancet 269:259, 1955.", "39. Van Gessel E, et
al: Eur J Anaesthesiol 27(8):673, 2010.". A regra Vancouver só contava "1980;62:358". A região, a
lacuna, as 10 citações e o motivo são os mesmos.
"""

from __future__ import annotations

import pytest

from earbook.dominio.fora_do_audio import MOTIVO_DO_VANCOUVER
from earbook.dominio.limpeza import limpar_para_o_ouvido
from earbook.dominio.livro_limpo import LivroLimpo
from earbook.dominio.segmento import Papel, Segmento

TITULO = (Papel.TITULO, "BiBliografía")
PROSA = (Papel.PARAGRAFO, "La anestesia general modifica la ventilación de manera previsible.")
PROXIMO = (Papel.TITULO, "Capítulo 16 Fisiología respiratoria")


def _referencia(n: int, citacao: str = "{n}:{p}, {ano}") -> str:
    onde = citacao.format(n=n, p=250 + n, ano=1950 + n)
    return f"{n}. Autor AB, et al: Rev Sint Anest {onde}."


def _notas(de: int, ate: int, citacao: str = "{n}:{p}, {ano}") -> list[tuple[Papel, str]]:
    return [(Papel.NOTA, _referencia(n, citacao)) for n in range(de, ate + 1)]


def _limpar(segmentos: list[tuple[Papel, str]]) -> LivroLimpo:
    capitulo = [
        Segmento(f"c001-s{n:04d}", papel, texto) for n, (papel, texto) in enumerate(segmentos, 1)
    ]
    return limpar_para_o_ouvido([("c001", capitulo)], "Livro", "Autor")


def _sobrou(livro: LivroLimpo) -> list[str]:
    return [s.texto for capitulo in livro.capitulos for s in capitulo.segmentos]


def test_dez_referencias_com_volume_pagina_e_ano_saem_com_o_titulo_registradas() -> None:
    livro = _limpar([PROSA, TITULO, *_notas(1, 10), PROXIMO])
    assert _sobrou(livro) == [PROSA[1], PROXIMO[1]]
    assert [(r.id, r.motivo) for r in livro.remocoes] == [
        (f"c001-s{n:04d}", MOTIVO_DO_VANCOUVER) for n in range(2, 13)
    ]


def test_nove_citacoes_ficam() -> None:
    assert len(_sobrou(_limpar([PROSA, TITULO, *_notas(1, 9), PROXIMO]))) == 12


@pytest.mark.parametrize(
    "citacao",
    ["{n}({n}):{p}, {ano}", "{n}:{p}-{p}, {ano}", "{n}:e{p}, {ano}", "{n}:S{p}-S{p}, {ano}"],
)
def test_o_fasciculo_a_faixa_de_paginas_e_a_pagina_com_letra_contam(citacao: str) -> None:
    assert _sobrou(_limpar([PROSA, TITULO, *_notas(1, 10, citacao), PROXIMO])) == [
        PROSA[1],
        PROXIMO[1],
    ]


@pytest.mark.parametrize(
    "frase",
    [
        "La relación fue de {n}:2 en 2010 y de {n}:3 en 2011.",
        "El registro de las {n}:30 del año 2012 muestra hipotermia.",
        "Se diluye a 1:{n}00.000 antes de la incisión.",
        "La escala va de {n}:10 a {n}:20; 2014 fue el año de la revisión.",
    ],
)
def test_a_proporcao_a_hora_e_a_diluicao_da_prosa_nao_sao_citacao(frase: str) -> None:
    prosa = [(Papel.PARAGRAFO, frase.format(n=n)) for n in range(1, 13)]
    assert len(_sobrou(_limpar(prosa))) == 12


def test_a_prosa_que_cita_um_artigo_no_meio_da_frase_fica() -> None:
    cita = (
        Papel.PARAGRAFO,
        "Como mostró Bedford (Lancet 269:259, 1955), el deterioro cognitivo no es raro.",
    )
    livro = _limpar([cita, PROSA, PROSA, PROSA, TITULO, *_notas(1, 10)])
    assert _sobrou(livro) == [cita[1], PROSA[1], PROSA[1], PROSA[1]]
