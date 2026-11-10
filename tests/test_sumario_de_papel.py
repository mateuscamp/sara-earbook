# SPDX-License-Identifier: GPL-3.0-or-later
"""O sumário de papel e a propaganda do livro saem do texto lido, registrados (ADR-0009).

O Dalgalarrondo lia em voz alta o sumário com pontilhado e número de página ("1. Introdução
geral ......... 23") e a propaganda "Conheça também", no primeiro capítulo. O Mateus aprovou
("Sim aos quatro"). O `limpos/` muda aqui, antes do livro inteiro, para o adaptador não pagar
por esse texto.
"""

from __future__ import annotations

from earbook.dominio.fora_do_audio import MOTIVO_DA_PROPAGANDA, MOTIVO_DO_SUMARIO_DE_PAPEL
from earbook.dominio.limpeza import limpar_para_o_ouvido
from earbook.dominio.livro_limpo import LivroLimpo
from earbook.dominio.segmento import Papel, Segmento

PROSA = (Papel.PARAGRAFO, "Este livro nasceu de muitas aulas de psicopatologia geral.")
PONTILHADO = "." * 40


def _linhas(quantas: int) -> list[tuple[Papel, str]]:
    return [
        (Papel.PARAGRAFO, f"{n}. Capítulo {PONTILHADO} {n + 22}") for n in range(1, quantas + 1)
    ]


def _limpar(*capitulos: list[tuple[Papel, str]]) -> LivroLimpo:
    livro = [
        (
            f"c{c:03d}",
            [
                Segmento(f"c{c:03d}-s{n:04d}", papel, texto)
                for n, (papel, texto) in enumerate(segmentos, 1)
            ],
        )
        for c, segmentos in enumerate(capitulos, 1)
    ]
    return limpar_para_o_ouvido(livro, "Livro", "Autor")


def _sobrou(livro: LivroLimpo) -> list[str]:
    return [s.texto for capitulo in livro.capitulos for s in capitulo.segmentos]


def test_cinco_linhas_com_pontilhado_e_numero_saem_registradas() -> None:
    livro = _limpar([PROSA, *_linhas(5), PROSA])
    assert _sobrou(livro) == [PROSA[1], PROSA[1]]
    assert [r.motivo for r in livro.remocoes] == [MOTIVO_DO_SUMARIO_DE_PAPEL] * 5


def test_linha_entre_as_pontilhadas_fica() -> None:
    linhas = _linhas(6)
    meio = (Papel.PARAGRAFO, "21. Funções psíquicas compostas e suas alterações:")
    assert _sobrou(_limpar([*linhas[:3], meio, *linhas[3:]])) == [meio[1]]


def test_quatro_linhas_pontilhadas_ficam() -> None:
    assert len(_sobrou(_limpar(_linhas(4)))) == 4


def test_a_conta_das_linhas_e_por_capitulo() -> None:
    assert len(_sobrou(_limpar(_linhas(3), _linhas(3)))) == 6


def test_pontilhado_sem_numero_no_fim_fica() -> None:
    teste = (Papel.PARAGRAFO, f"Teste de Wilson: 3 vezes 5 {PONTILHADO} (Continuação)")
    assert len(_sobrou(_limpar([teste] * 6))) == 6


def test_menos_de_cinco_pontos_nao_e_pontilhado() -> None:
    linhas = [(Papel.PARAGRAFO, f"Etapa {n} .... {n}") for n in range(6)]
    assert len(_sobrou(_limpar(linhas))) == 6


def test_propaganda_sai_ate_o_proximo_titulo() -> None:
    livro = _limpar(
        [
            (Papel.TITULO, "Psicopatologia"),
            (Papel.TITULO, "Conheça também"),
            (Papel.PARAGRAFO, "A religiosidade é um objeto de interesse."),
            (Papel.PARAGRAFO, "Em Religião e Saúde Mental, o doutor apresenta sua pesquisa."),
            (Papel.TITULO, "2a edição"),
            PROSA,
        ]
    )
    assert _sobrou(livro) == ["Psicopatologia", "2a edição", PROSA[1]]
    assert [r.motivo for r in livro.remocoes] == [MOTIVO_DA_PROPAGANDA] * 3


def test_propaganda_no_fim_do_capitulo_sai_ate_o_fim_dele() -> None:
    livro = _limpar([PROSA, (Papel.TITULO, "Conheça também"), PROSA], [PROSA])
    assert _sobrou(livro) == [PROSA[1], PROSA[1]]


def test_titulo_seguido_de_mais_de_cinco_paragrafos_nao_e_propaganda() -> None:
    titulo = (Papel.TITULO, "Conheça também")
    paragrafos = [(Papel.PARAGRAFO, f"Parágrafo {n} de um texto que continua.") for n in range(6)]
    assert len(_sobrou(_limpar([titulo, *paragrafos]))) == 7


def test_so_o_titulo_exato_e_propaganda() -> None:
    titulo = (Papel.TITULO, "Conheça também a história da psiquiatria")
    paragrafo = (Papel.PARAGRAFO, "Conheça também")
    assert len(_sobrou(_limpar([titulo, PROSA, paragrafo, PROSA]))) == 4


def test_titulo_com_exatos_cinco_paragrafos_ainda_e_propaganda() -> None:
    titulo = (Papel.TITULO, "Conheça também")
    paragrafos = [(Papel.PARAGRAFO, f"Parágrafo {n} sobre outro livro.") for n in range(5)]
    assert _sobrou(_limpar([PROSA, titulo, *paragrafos])) == [PROSA[1]]


def test_titulo_da_propaganda_em_maiusculas_sai() -> None:
    titulo = (Papel.TITULO, "CONHEÇA TAMBÉM")
    assert _sobrou(_limpar([PROSA, titulo, PROSA])) == [PROSA[1]]
