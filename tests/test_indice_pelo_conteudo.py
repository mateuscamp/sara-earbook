# SPDX-License-Identifier: GPL-3.0-or-later
"""O índice remissivo sem marcação sai do texto lido, pelo conteúdo (ADR-0008, "Índice pelo
conteúdo").

O PDF importado não tem `epub:type="index"`. O índice do Dalgalarrondo (18 parágrafos, um por
letra, depois do título "Índice") e o do Hard Parts (26, entre títulos "A", "B"…) eram lidos. O
Mateus aprovou ("Aprovar"). A regra olha o conteúdo de cada parágrafo, nunca o título.
"""

from __future__ import annotations

from earbook.dominio.fora_do_audio import MOTIVO_DO_INDICE_PELO_CONTEUDO
from earbook.dominio.limpeza import limpar_para_o_ouvido
from earbook.dominio.livro_limpo import LivroLimpo
from earbook.dominio.segmento import Papel, Segmento

TITULO = (Papel.TITULO, "Índice")
DEPOIS = (Papel.TITULO, "Sobre o autor")


def _entradas(quantas: int) -> list[tuple[Papel, str]]:
    return [
        (Papel.PARAGRAFO, f"Termo{chr(65 + n)} composto, {100 + n}-{110 + n} subtermo, {20 + n}")
        for n in range(quantas)
    ]


def _limpar(segmentos: list[tuple[Papel, str]]) -> LivroLimpo:
    capitulo = [
        Segmento(f"c001-s{n:04d}", papel, texto) for n, (papel, texto) in enumerate(segmentos, 1)
    ]
    return limpar_para_o_ouvido([("c001", capitulo)], "Livro", "Autor")


def _sobrou(livro: LivroLimpo) -> list[str]:
    return [s.texto for capitulo in livro.capitulos for s in capitulo.segmentos]


def test_dez_entradas_seguidas_e_o_titulo_logo_antes_saem_registrados() -> None:
    prosa = (Papel.PARAGRAFO, "Este glossário é baseado nos trabalhos de Fernando São Paulo.")
    livro = _limpar([prosa, TITULO, *_entradas(10), DEPOIS])
    assert _sobrou(livro) == [prosa[1], DEPOIS[1]]
    assert [(r.id, r.motivo) for r in livro.remocoes] == [
        (f"c001-s{n:04d}", MOTIVO_DO_INDICE_PELO_CONTEUDO) for n in range(2, 13)
    ]


def test_nove_entradas_seguidas_ficam() -> None:
    assert len(_sobrou(_limpar([TITULO, *_entradas(9)]))) == 10


def test_letra_no_meio_sai_com_o_indice() -> None:
    # Hard Parts: "Index", "A", parágrafo, "B", parágrafo… O "B" não parte a sequência.
    segmentos = [(Papel.TITULO, "Index"), (Papel.TITULO, "A"), *_entradas(5)]
    segmentos += [(Papel.TITULO, "B"), *_entradas(5), DEPOIS]
    assert _sobrou(_limpar(segmentos)) == [DEPOIS[1]]


def test_entrada_que_termina_em_remissao_conta() -> None:
    # Hard Parts, o "W": "… service granularity, 200-203 (see also distributed workflows)".
    remissao = (
        Papel.PARAGRAFO,
        "Workflow management, 300 service granularity, 200-203 (see also distributed workflows)",
    )
    assert _sobrou(_limpar([TITULO, *_entradas(9), remissao])) == []


def test_mais_de_oito_palavras_por_pagina_nao_e_entrada() -> None:
    longa = (
        Papel.PARAGRAFO,
        "On September 7, 2017, the agency announced a breach that exposed many records, 12",
    )
    assert len(_sobrou(_limpar([TITULO, *_entradas(5), longa, *_entradas(5)]))) == 12


def _no_meio_de_dez_entradas(texto: str) -> int:
    """Quantos segmentos sobram com `texto` entre 5 entradas e outras 5: se ele contasse como
    entrada, a sequência chegaria a 11 e sairia inteira, com o título."""
    meio = (Papel.PARAGRAFO, texto)
    return len(_sobrou(_limpar([TITULO, *_entradas(5), meio, *_entradas(5)])))


def test_virgula_sem_espaco_nao_e_pagina() -> None:
    # A vírgula decimal das tabelas do Dalgalarrondo ("2,0 1,3") e o separador de milhar da
    # tabela do Hard Parts (c008: "Billing Payment ss.billing.payment 5 4,312 23"), que sairia
    # como índice falso (M15 da auditoria).
    assert _no_meio_de_dez_entradas("Billing Payment ss.billing.payment 5 4,312 23") == 12


def test_ano_nao_e_pagina() -> None:
    assert _no_meio_de_dez_entradas("Publicado em Porto Alegre, 2004") == 12


def test_numero_antes_do_parentese_nao_e_pagina() -> None:
    # A citação ("Doença de Alzheimer (Cummings, 2004)", Dalgalarrondo), com um número que não
    # parece ano.
    assert _no_meio_de_dez_entradas("Doença de Alzheimer (Cummings, 20)") == 12


def test_o_titulo_sozinho_nao_tira_nada() -> None:
    prosa = [(Papel.PARAGRAFO, f"Texto corrido do capítulo, parágrafo {n}.") for n in range(10)]
    assert len(_sobrou(_limpar([TITULO, *prosa]))) == 11
