# SPDX-License-Identifier: GPL-3.0-or-later
"""A fidelidade de um grupo adaptado às fontes: número, termo raro e papel (ADR-0009)."""

from __future__ import annotations

import pytest

from earbook.dominio.fidelidade import (
    Raridade,
    eh_rotulo,
    faltas_de_fidelidade,
    so_funciona_no_papel,
)
from earbook.dominio.segmento import Papel, Segmento

_COMUM = "Os pacientes apresentam sintomas variados."


def _raridade(*textos: str) -> Raridade:
    """O livro: os textos dados, mais 25 parágrafos que tornam comuns as palavras de `_COMUM`."""
    segmentos = [Segmento(f"c001-s{n:04d}", Papel.PARAGRAFO, t) for n, t in enumerate(textos)]
    segmentos += [Segmento(f"c002-s{n:04d}", Papel.PARAGRAFO, _COMUM) for n in range(25)]
    return Raridade.do_livro(segmentos)


def _faltas(fontes: list[str], texto: str, omitidos: tuple[str, ...] = ()) -> list[str]:
    return faltas_de_fidelidade(fontes, [texto], omitidos, _raridade(*fontes))


def test_numero_das_fontes_que_some_e_acusado() -> None:
    assert _faltas(["Por 2 semanas, em 51,1% dos casos."], "Por semanas, em 51,1% dos casos.") == [
        "o número 2 das fontes não está no texto"
    ]


def test_numero_que_as_fontes_nao_tem_e_acusado() -> None:
    assert _faltas(["Por 2 semanas."], "Por 2 ou 3 semanas.") == ["o número 3 não está nas fontes"]


def test_numero_repetido_nas_fontes_e_cobrado_tantas_vezes_quantas_aparece() -> None:
    assert _faltas(["De 5 a 10 dias.", "Em 5 casos."], "De 5 a 10 dias, em casos.") == [
        "o número 5 das fontes não está no texto"
    ]


@pytest.mark.parametrize(
    ("fonte", "texto"),
    [
        ("O humor triste (Del Pino, 2003).", "O humor triste."),
        ("As áreas (Kandel; Schwartz; Jessel, 1995; Miotto et al., 1996).", "As áreas."),
        ("Bleuler (1985, p. 16) adverte.", "Bleuler adverte."),
        ("Harry Stack Sullivan (1983) afirmava.", "Harry Stack Sullivan afirmava."),
        ("Dalgalarrondo et al. (2003) mediram.", "Dalgalarrondo e colaboradores mediram."),
        ("Nas palavras de Aristóteles (348-322 a.C.).", "Nas palavras de Aristóteles."),
        ("Kraepelin (1856-1926) definiu.", "Kraepelin definiu."),
        ("Quadro 27.1", ""),
        ("Episódio depressivo (Quadro 27.1).", "Episódio depressivo."),
        ("1. Distimia", "Distimia."),
        ("EUA1 317 pacientes", "Nos Estados Unidos, 317 pacientes."),
    ],
)
def test_citacao_rotulo_ordinal_e_chamada_de_nota_nao_sao_cobrados(fonte: str, texto: str) -> None:
    assert _faltas([fonte], texto) == []


def test_ano_entre_colchetes_e_dado_e_e_cobrado() -> None:
    fonte = "Freud [1911] (1976) postulou."
    assert _faltas([fonte], "Freud postulou.") == ["o número 1911 das fontes não está no texto"]
    assert _faltas([fonte], "Freud, em 1911, postulou.") == []


def test_ano_de_citacao_pode_ficar_como_data_do_fato() -> None:
    assert _faltas(["Desenvolvido por Moruzzi e Magoun (1949)."], "Desenvolvido em 1949.") == []


def test_parentese_com_dado_alem_do_ano_nao_e_citacao() -> None:
    assert _faltas(["Um terço (Datafolha, 1998: 30%) relata."], "Um terço relata.") == [
        "o número 1998 das fontes não está no texto",
        "o número 30 das fontes não está no texto",
        "o termo 'Datafolha' das fontes não está no texto nem em omitidos",
    ]


def test_termo_raro_que_some_e_acusado_e_o_comum_nao() -> None:
    assert _faltas(
        ["Os pacientes apresentam anedonia e hipersonia."], "Apresentam hipersonia."
    ) == ["o termo 'anedonia' das fontes não está no texto nem em omitidos"]


def test_termo_compara_sem_acento_hifen_e_flexao() -> None:
    fonte = "Humor freqüente, auto-estima baixa, deprimido."
    assert _faltas([fonte], "Humor frequente, autoestima baixa, deprimida.") == []


def test_termo_em_omitidos_nao_e_cobrado() -> None:
    fonte = "O miniexame do estado mental (Minimental)."
    assert _faltas([fonte], "O miniexame do estado mental.", ("Minimental",)) == []


def test_nome_de_autor_dentro_da_citacao_nao_e_cobrado() -> None:
    assert _faltas(["A memória (Schwartzberger, 2003)."], "A memória.") == []


@pytest.mark.parametrize(
    ("paragrafo", "motivo"),
    [
        ("• Humor deprimido", "marcador de lista '•'"),
        ("\u2013 Tristeza", "item de lista com travessão"),
        ("2. Distimia", "item de lista numerado"),
        ("Ver o Quadro 27.1 acima.", "rótulo ou remissão 'Quadro 27.1'"),
        ("O humor triste (Del Pino, 2003).", "citação '(Del Pino, 2003)'"),
        ("Segundo Nelson et al., é raro.", "'et al.'"),
        ("Há, p. ex., a mania.", "'p. ex.'"),
        ("Introdução ........ 23", "pontilhado de sumário"),
        ("Nome: " + "\u2013" * 9, "linha de formulário"),
        ("Sei lá! [...]", "'[...]'"),
    ],
)
def test_o_que_so_funciona_no_papel_e_acusado(paragrafo: str, motivo: str) -> None:
    assert so_funciona_no_papel(paragrafo) == [motivo]


def test_texto_corrido_nao_tem_nada_de_papel() -> None:
    assert so_funciona_no_papel("Distimia é uma depressão crônica, por exemplo, de 2 anos.") == []


@pytest.mark.parametrize(
    ("texto", "rotulo"),
    [("Quadro 27.1", True), ("Tabela 19.1", True), ("27", True), ("Quadro de sintomas", False)],
)
def test_rotulo_e_so_o_rotulo(texto: str, *, rotulo: bool) -> None:
    assert eh_rotulo(texto) is rotulo


def test_algarismo_colado_a_letra_de_dado_e_cobrado() -> None:
    """A3 da auditoria: só a chamada de nota colada a uma palavra ("EUA1") fica fora."""
    fonte = "Déficit de vitamina B12 e B1, no F40."
    assert _faltas([fonte], "Déficit de vitamina B6 e B1, no F40.") == [
        "o número 12 das fontes não está no texto",
        "o número 6 não está nas fontes",
    ]


def test_parentese_de_dado_com_intervalo_nao_e_citacao() -> None:
    """A4 da auditoria: só o ano de verdade faz a citação; o intervalo e a página, não."""
    fonte = "Po Chu Yi (poeta chinês da Dinastia Tang, 618-960) escreveu."
    assert _faltas([fonte], "Po Chu Yi escreveu.") == [
        "o número 618 das fontes não está no texto",
        "o número 960 das fontes não está no texto",
        "o termo 'Dinastia' das fontes não está no texto nem em omitidos",
    ]
    assert so_funciona_no_papel(fonte) == []


def test_dois_algarismos_colados_a_palavra_nao_sao_chamada_de_nota() -> None:
    """A chamada de nota da tabela é um algarismo só ("Brasil3"); "COVID19" é dado."""
    assert _faltas(["Casos de COVID19 no Brasil3."], "Casos de COVID no Brasil.") == [
        "o número 19 das fontes não está no texto"
    ]
