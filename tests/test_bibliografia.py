# SPDX-License-Identifier: GPL-3.0-or-later
"""A bibliografia sai do texto lido, registrada (ADR-0008, "Bibliografia").

No Dalgalarrondo, as p. 417 a 431 trazem as referências no padrão ABNT ("ABDO, C. H. N.
Diagnóstico em psiquiatria… 1996."), depois do título "Referências bibliográficas e leituras
recomendadas". O Mateus decidiu: "Sim, sai". A regra olha o conteúdo de cada parágrafo, nunca o
título, que o ADR-0008 proíbe como critério.
"""

from __future__ import annotations

from earbook.dominio.fora_do_audio import MOTIVO_DA_BIBLIOGRAFIA
from earbook.dominio.limpeza import limpar_para_o_ouvido
from earbook.dominio.livro_limpo import LivroLimpo
from earbook.dominio.segmento import Papel, Segmento

TITULO = (Papel.TITULO, "Referências bibliográficas e leituras recomendadas")
DEPOIS = (Papel.TITULO, "Índice")


def _referencias(quantas: int) -> list[tuple[Papel, str]]:
    return [
        (
            Papel.PARAGRAFO,
            f"AUTOR{chr(65 + n)}, C. H. N. Diagnóstico. Porto Alegre: Artmed, {1990 + n}.",
        )
        for n in range(quantas)
    ]


def _limpar(segmentos: list[tuple[Papel, str]]) -> LivroLimpo:
    capitulo = [
        Segmento(f"c001-s{n:04d}", papel, texto) for n, (papel, texto) in enumerate(segmentos, 1)
    ]
    return limpar_para_o_ouvido([("c001", capitulo)], "Livro", "Autor")


def _sobrou(livro: LivroLimpo) -> list[str]:
    return [s.texto for capitulo in livro.capitulos for s in capitulo.segmentos]


def test_dez_referencias_seguidas_e_o_titulo_logo_antes_saem_registrados() -> None:
    prosa = (
        Papel.PARAGRAFO,
        "Este glossário é baseado nos trabalhos de Fernando São Paulo (1936).",
    )
    livro = _limpar([prosa, TITULO, *_referencias(10), DEPOIS])
    assert _sobrou(livro) == [prosa[1], DEPOIS[1]]
    assert [(r.id, r.motivo) for r in livro.remocoes] == [
        (f"c001-s{n:04d}", MOTIVO_DA_BIBLIOGRAFIA) for n in range(2, 13)
    ]


def test_nove_referencias_seguidas_ficam() -> None:
    # A lista curta no fim de um capítulo, e as referências do Competente, partidas entre nota e
    # parágrafo (no máximo 3 seguidas).
    assert len(_sobrou(_limpar([TITULO, *_referencias(9)]))) == 10


def test_referencia_sem_ano_parte_a_sequencia() -> None:
    sem_ano = (
        Papel.PARAGRAFO,
        "SÃO PAULO, F. Linguagem médica popular no Brasil. Rio de Janeiro: s.d.",
    )
    segmentos = [TITULO, *_referencias(5), sem_ano, *_referencias(5)]
    assert len(_sobrou(_limpar(segmentos))) == 12


def test_referencia_que_nao_e_abnt_fica() -> None:
    # Learning DDD, c317: "Evans, E. (2003). Domain-Driven Design…", no padrão APA. Está traduzido,
    # e a regra não o toca.
    apa = [
        (Papel.PARAGRAFO, f"Evans{n}, E. (2003). Domain-Driven Design. Boston: Addison-Wesley.")
        for n in range(12)
    ]
    assert len(_sobrou(_limpar([(Papel.TITULO, "References"), *apa]))) == 13


def test_o_titulo_sozinho_nao_tira_nada() -> None:
    prosa = [(Papel.PARAGRAFO, f"Texto corrido do capítulo, parágrafo {n}.") for n in range(10)]
    assert len(_sobrou(_limpar([TITULO, *prosa]))) == 11


def test_titulo_longe_das_referencias_fica() -> None:
    aviso = (Papel.PARAGRAFO, "As obras abaixo foram consultadas para esta edição.")
    livro = _limpar([TITULO, aviso, *_referencias(10)])
    assert _sobrou(livro) == [TITULO[1], aviso[1]]
